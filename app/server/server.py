from __future__ import annotations

import email
import html
import imaplib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.message import Message
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory


APP_DIR = Path(__file__).resolve().parent
CONFIG_DIR = Path(os.environ.get("APP_CONFIG_DIR", "./var/config")).resolve()
DATA_DIR = Path(os.environ.get("APP_DATA_DIR", "./var/data")).resolve()
LOG_DIR = Path(os.environ.get("APP_LOG_DIR", "./var/logs")).resolve()
HOST = os.environ.get("APP_HOST", "0.0.0.0")
PORT = int(os.environ.get("APP_PORT", "8080"))
SYNC_ROOT_HOST_PATH = os.environ.get("SYNC_ROOT_HOST_PATH", "/var/apps/icloud-sync/shares/icloud")

CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_FILE = CONFIG_DIR / "state.json"
STORAGE_ROOT_FILE = CONFIG_DIR / "storage_root.json"
COOKIE_ROOT = CONFIG_DIR / "cookies"
MAX_LOG_LINES = 500
STATS_CACHE_TTL_SECONDS = 30

for path in (CONFIG_DIR, DATA_DIR, LOG_DIR, COOKIE_ROOT):
    path.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=str(APP_DIR / "static"), static_url_path="/static")


@app.after_request
def add_response_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Cache-Control"] = "no-store"
    return response


DEFAULT_NOTES: dict[str, Any] = {
    "host": "imap.mail.me.com",
    "port": 993,
    "username": "",
    "password": "",
    "folder": "Notes",
    "format": "markdown",
    "limit": 0,
}

DEFAULT_PROFILE: dict[str, Any] = {
    "id": "default",
    "name": "默认方案",
    "data_subdir": "",
    "apple_id": "",
    "store_password": False,
    "password": "",
    "photos_enabled": True,
    "videos_enabled": True,
    "notes_enabled": False,
    "schedule_enabled": False,
    "sync_interval_minutes": 360,
    "domain": "cn",
    "folder_structure": "{:%Y/%m/%d}",
    "media_mode": "copy",
    "recent": "",
    "until_found": "",
    "album": "",
    "library": "",
    "size": "original",
    "live_photo_size": "",
    "force_size": False,
    "align_raw": "",
    "file_match_policy": "",
    "retry_attempts": 3,
    "retry_delay_seconds": 60,
    "include_live_photos": True,
    "keep_unicode": True,
    "set_exif_datetime": True,
    "notes": DEFAULT_NOTES,
}

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 2,
    "active_profile_id": "default",
    "profiles": [DEFAULT_PROFILE],
}

DEFAULT_PROFILE_STATE: dict[str, Any] = {
    "last_media_sync": "",
    "last_notes_sync": "",
    "last_scheduler_check": "",
    "last_media_schedule_attempt": "",
    "last_notes_schedule_attempt": "",
    "last_scheduler_trigger": "",
    "scheduler_check_count": 0,
    "scheduler_trigger_count": 0,
    "last_scheduler_status": "",
    "last_scheduler_message": "",
}

DEFAULT_STATE: dict[str, Any] = {
    "schema_version": 2,
    "profiles": {
        "default": DEFAULT_PROFILE_STATE,
    },
}

DEFAULT_STORAGE_ROOT: dict[str, Any] = {
    "selected_root_path": SYNC_ROOT_HOST_PATH,
    "using_default_root": True,
    "authorized_paths": [],
    "updated_at": "",
}


config_lock = threading.RLock()
job_lock = threading.RLock()
stats_lock = threading.RLock()
jobs_by_profile: dict[str, "Job"] = {}
stats_cache: dict[str, tuple[float, dict[str, Any]]] = {}


@dataclass
class Job:
    kind: str
    profile_id: str
    profile_name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "running"
    started_at: str = field(default_factory=lambda: utc_now())
    ended_at: str = ""
    return_code: int | None = None
    waiting_input: bool = False
    process: subprocess.Popen[str] | None = None
    log_lines: list[str] = field(default_factory=list)
    log_path: Path | None = None
    error: str = ""
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    def append(self, text: str) -> None:
        line = text.rstrip("\n")
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {line}" if line else ""
        with self.lock:
            self.log_lines.append(formatted)
            if len(self.log_lines) > MAX_LOG_LINES:
                self.log_lines = self.log_lines[-MAX_LOG_LINES:]
            log_path = self.log_path
        if log_path:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(formatted + "\n")

    def to_dict(self, include_log: bool = True) -> dict[str, Any]:
        with self.lock:
            payload = {
                "id": self.id,
                "kind": self.kind,
                "profile_id": self.profile_id,
                "profile_name": self.profile_name,
                "status": self.status,
                "started_at": self.started_at,
                "ended_at": self.ended_at,
                "return_code": self.return_code,
                "waiting_input": self.waiting_input,
                "error": self.error,
            }
            if include_log:
                payload["log"] = self.log_lines[-250:]
        return payload


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "p", "div", "li"}:
            self.parts.append("\n")

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self.parts)).strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def timestamp_to_iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).replace(microsecond=0).isoformat()


def iso_to_timestamp(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0


def deep_copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return deep_copy(default)
    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return deep_copy(default)
    return loaded if isinstance(loaded, dict) else deep_copy(default)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temp.replace(path)


def merge_dicts(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = merge_dicts(base[key], value)
        else:
            base[key] = value
    return base


def make_profile(name: str = "新方案") -> dict[str, Any]:
    profile = deep_copy(DEFAULT_PROFILE)
    profile_id = "p_" + uuid.uuid4().hex[:10]
    profile["id"] = profile_id
    profile["name"] = name.strip() or "新方案"
    profile["data_subdir"] = f"profiles/{profile_id}"
    return profile


def normalize_data_subdir(value: Any, fallback: str, profile_id: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    for root in [SYNC_ROOT_HOST_PATH, str(DATA_DIR)]:
        normalized_root = root.replace("\\", "/").rstrip("/")
        if text == normalized_root:
            text = ""
            break
        if normalized_root and text.startswith(f"{normalized_root}/"):
            text = text[len(normalized_root) + 1 :]
            break

    text = re.sub(r"/+", "/", text).strip("/")
    if profile_id != "default" and text == profile_id:
        text = f"profiles/{profile_id}"

    parts: list[str] = []
    for part in text.split("/"):
        cleaned = part.strip()
        if not cleaned or cleaned in {".", ".."}:
            continue
        cleaned = re.sub(r'[<>:"|?*\x00-\x1f]', "_", cleaned)
        cleaned = cleaned[:80].strip()
        if cleaned:
            parts.append(cleaned)
    return "/".join(parts[:6]) or fallback


def normalize_root_path(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while len(text) > 1 and text.endswith("/"):
        text = text[:-1]
    return text


def normalize_profile(profile: dict[str, Any]) -> None:
    profile["id"] = str(profile.get("id") or ("p_" + uuid.uuid4().hex[:10]))
    profile["name"] = str(profile.get("name") or profile.get("apple_id") or "未命名方案").strip()
    fallback_subdir = "" if profile["id"] == "default" else f"profiles/{profile['id']}"
    profile["data_subdir"] = normalize_data_subdir(profile.get("data_subdir", ""), fallback_subdir, profile["id"])
    profile["apple_id"] = str(profile.get("apple_id", "")).strip()
    profile["domain"] = "cn" if str(profile.get("domain", "com")).lower() == "cn" else "com"
    media_mode = str(profile.get("media_mode") or "copy")
    profile["media_mode"] = media_mode if media_mode in {"copy", "mirror", "move"} else "copy"
    profile["size"] = str(profile.get("size") or "original")
    live_photo_size = str(profile.get("live_photo_size") or "").strip().lower()
    profile["live_photo_size"] = live_photo_size if live_photo_size in {"", "original", "medium", "thumb"} else ""
    align_raw = str(profile.get("align_raw") or "").strip().lower()
    profile["align_raw"] = align_raw if align_raw in {"", "original", "alternative", "as-is"} else ""
    file_match_policy = str(profile.get("file_match_policy") or "").strip().lower()
    profile["file_match_policy"] = (
        file_match_policy if file_match_policy in {"", "name-size-dedup-with-suffix", "name-id7"} else ""
    )
    profile["folder_structure"] = str(profile.get("folder_structure") or "{:%Y/%m/%d}")
    profile["sync_interval_minutes"] = max(15, int_or_default(profile.get("sync_interval_minutes"), 360))
    profile["recent"] = normalize_number_string(profile.get("recent"))
    profile["until_found"] = normalize_number_string(profile.get("until_found"))
    profile["retry_attempts"] = clamp_int(profile.get("retry_attempts"), 3, 0, 10)
    profile["retry_delay_seconds"] = clamp_int(profile.get("retry_delay_seconds"), 60, 0, 3600)
    for key in [
        "photos_enabled",
        "videos_enabled",
        "notes_enabled",
        "schedule_enabled",
        "store_password",
        "force_size",
        "include_live_photos",
        "keep_unicode",
        "set_exif_datetime",
    ]:
        profile[key] = bool(profile.get(key, DEFAULT_PROFILE.get(key, False)))

    notes = merge_dicts(deep_copy(DEFAULT_NOTES), profile.get("notes", {}))
    notes["host"] = str(notes.get("host") or "imap.mail.me.com").strip()
    notes["port"] = max(1, int_or_default(notes.get("port"), 993))
    notes["username"] = str(notes.get("username") or "").strip()
    notes["folder"] = str(notes.get("folder") or "Notes").strip()
    notes["format"] = "html" if notes.get("format") == "html" else "markdown"
    notes["limit"] = max(0, int_or_default(notes.get("limit"), 0))
    profile["notes"] = notes


def migrate_flat_config(raw: dict[str, Any]) -> dict[str, Any]:
    profile = merge_dicts(deep_copy(DEFAULT_PROFILE), raw)
    profile["id"] = "default"
    profile["data_subdir"] = ""
    profile["name"] = raw.get("name") or raw.get("apple_id") or "默认方案"
    normalize_profile(profile)
    return {
        "schema_version": 2,
        "active_profile_id": profile["id"],
        "profiles": [profile],
    }


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    if "profiles" not in config or not isinstance(config.get("profiles"), list):
        return migrate_flat_config(config)

    normalized_profiles: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in config.get("profiles", []):
        if not isinstance(item, dict):
            continue
        profile = merge_dicts(deep_copy(DEFAULT_PROFILE), item)
        normalize_profile(profile)
        if profile["id"] in seen:
            profile["id"] = "p_" + uuid.uuid4().hex[:10]
            if profile.get("data_subdir"):
                profile["data_subdir"] = profile["id"]
        seen.add(profile["id"])
        normalized_profiles.append(profile)

    if not normalized_profiles:
        normalized_profiles.append(deep_copy(DEFAULT_PROFILE))

    active_id = str(config.get("active_profile_id") or "")
    if active_id not in {profile["id"] for profile in normalized_profiles}:
        active_id = normalized_profiles[0]["id"]

    return {
        "schema_version": 2,
        "active_profile_id": active_id,
        "profiles": normalized_profiles,
    }


def load_config() -> dict[str, Any]:
    with config_lock:
        return normalize_config(read_json(CONFIG_FILE, DEFAULT_CONFIG))


def get_profile(config: dict[str, Any], profile_id: str | None = None) -> dict[str, Any]:
    effective_id = profile_id or config.get("active_profile_id")
    for profile in config.get("profiles", []):
        if profile.get("id") == effective_id:
            return profile
    if config.get("profiles"):
        return config["profiles"][0]
    raise RuntimeError("没有可用方案")


def profile_index(config: dict[str, Any], profile_id: str) -> int:
    for idx, profile in enumerate(config.get("profiles", [])):
        if profile.get("id") == profile_id:
            return idx
    raise KeyError(profile_id)


def save_config(payload: dict[str, Any]) -> dict[str, Any]:
    with config_lock:
        current = load_config()
        if payload.get("active_profile_id"):
            profile_index(current, str(payload["active_profile_id"]))
            current["active_profile_id"] = str(payload["active_profile_id"])

        profile_id = str(payload.get("profile_id") or current["active_profile_id"])
        profile = current["profiles"][profile_index(current, profile_id)]
        notes_current = profile.get("notes", {})

        for key in [
            "name",
            "data_subdir",
            "apple_id",
            "photos_enabled",
            "videos_enabled",
            "notes_enabled",
            "schedule_enabled",
            "sync_interval_minutes",
            "domain",
            "folder_structure",
            "media_mode",
            "recent",
            "until_found",
            "album",
            "library",
            "size",
            "live_photo_size",
            "align_raw",
            "file_match_policy",
            "force_size",
            "include_live_photos",
            "keep_unicode",
            "set_exif_datetime",
        ]:
            if key in payload:
                profile[key] = payload[key]

        if "store_password" in payload:
            profile["store_password"] = bool(payload["store_password"])
        if payload.get("clear_password") or not profile.get("store_password"):
            profile["password"] = ""
        elif payload.get("password"):
            profile["password"] = str(payload["password"])

        incoming_notes = payload.get("notes", {})
        if isinstance(incoming_notes, dict):
            for key in ["host", "port", "username", "folder", "format", "limit"]:
                if key in incoming_notes:
                    notes_current[key] = incoming_notes[key]
            if incoming_notes.get("clear_password"):
                notes_current["password"] = ""
            elif incoming_notes.get("password"):
                notes_current["password"] = str(incoming_notes["password"])
            profile["notes"] = notes_current

        normalize_profile(profile)
        write_json(CONFIG_FILE, current)
        clear_profile_stats(profile["id"])
        return current


def public_profile(profile: dict[str, Any]) -> dict[str, Any]:
    cleaned = deep_copy(profile)
    cleaned["has_password"] = bool(cleaned.get("password"))
    cleaned["password"] = ""
    notes = cleaned.get("notes", {})
    notes["has_password"] = bool(notes.get("password"))
    notes["password"] = ""
    return cleaned


def public_config(config: dict[str, Any]) -> dict[str, Any]:
    cleaned = deep_copy(config)
    cleaned["profiles"] = [public_profile(profile) for profile in config.get("profiles", [])]
    cleaned["active_profile"] = public_profile(get_profile(config, config.get("active_profile_id")))
    return cleaned


def int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    return min(max(int_or_default(value, default), minimum), maximum)


def normalize_number_string(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if re.fullmatch(r"\d+", text) else ""


def normalize_state(raw: dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw.get("profiles"), dict):
        profiles: dict[str, Any] = {}
        for profile_id, state in raw["profiles"].items():
            if isinstance(state, dict):
                profiles[str(profile_id)] = merge_dicts(deep_copy(DEFAULT_PROFILE_STATE), state)
        return {"schema_version": 2, "profiles": profiles}
    return {
        "schema_version": 2,
        "profiles": {
            "default": merge_dicts(deep_copy(DEFAULT_PROFILE_STATE), raw),
        },
    }


def load_state() -> dict[str, Any]:
    with config_lock:
        return normalize_state(read_json(STATE_FILE, DEFAULT_STATE))


def save_state(state: dict[str, Any]) -> None:
    with config_lock:
        write_json(STATE_FILE, state)


def load_storage_root() -> dict[str, Any]:
    raw = read_json(STORAGE_ROOT_FILE, DEFAULT_STORAGE_ROOT)
    applied_root_path = normalize_root_path(SYNC_ROOT_HOST_PATH)
    selected_root_path = normalize_root_path(raw.get("selected_root_path") or applied_root_path) or applied_root_path
    default_root_path = normalize_root_path(DEFAULT_STORAGE_ROOT["selected_root_path"])
    if selected_root_path == default_root_path and applied_root_path != default_root_path:
        selected_root_path = applied_root_path
    authorized_paths = raw.get("authorized_paths", [])
    if not isinstance(authorized_paths, list):
        authorized_paths = []

    normalized_paths: list[str] = []
    for item in authorized_paths:
        text = normalize_root_path(item)
        if text:
            normalized_paths.append(text)

    return {
        "selected_root_path": selected_root_path,
        "using_default_root": bool(raw.get("using_default_root", selected_root_path == applied_root_path)),
        "authorized_paths": normalized_paths,
        "updated_at": str(raw.get("updated_at") or ""),
    }


def get_profile_state(profile_id: str) -> dict[str, Any]:
    state = load_state()
    return merge_dicts(deep_copy(DEFAULT_PROFILE_STATE), state.get("profiles", {}).get(profile_id, {}))


def update_profile_state(profile_id: str, updates: dict[str, Any]) -> None:
    state = load_state()
    profiles = state.setdefault("profiles", {})
    current = merge_dicts(deep_copy(DEFAULT_PROFILE_STATE), profiles.get(profile_id, {}))
    current.update(updates)
    profiles[profile_id] = current
    save_state(state)


def profile_data_dir(profile: dict[str, Any]) -> Path:
    subdir = str(profile.get("data_subdir", profile["id"]))
    if not subdir:
        return DATA_DIR
    return DATA_DIR / subdir


def profile_cookie_dir(profile: dict[str, Any]) -> Path:
    return COOKIE_ROOT / profile["id"]


def profile_job(profile_id: str) -> Job | None:
    with job_lock:
        return jobs_by_profile.get(profile_id)


def running_jobs_count() -> int:
    with job_lock:
        return sum(1 for job in jobs_by_profile.values() if job.status == "running")


def job_has_live_process(job: Job) -> bool:
    with job.lock:
        process = job.process
    return bool(process and process.poll() is None)


def can_start_job(profile_id: str) -> tuple[bool, str]:
    with job_lock:
        existing = jobs_by_profile.get(profile_id)
        if existing and (existing.status == "running" or job_has_live_process(existing)):
            return False, "当前方案已有任务正在运行"
    return True, ""


def run_job_target(target, job: Job, profile_id: str, args: tuple[Any, ...]) -> None:
    try:
        target(job, profile_id, *args)
    except Exception as exc:
        finish_job(job, "failed", return_code=1, error=str(exc))


def start_job(kind: str, profile_id: str, target, *args) -> Job:
    config = load_config()
    profile = get_profile(config, profile_id)
    job = Job(kind=kind, profile_id=profile["id"], profile_name=profile["name"])
    log_dir = LOG_DIR / profile["id"]
    log_dir.mkdir(parents=True, exist_ok=True)
    job.log_path = log_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{kind}-{job.id}.log"
    profiles_by_id = {
        item["id"]: item for item in config.get("profiles", []) if isinstance(item, dict) and item.get("id")
    }
    target_dir = profile_data_dir(profile).resolve()

    with job_lock:
        existing = jobs_by_profile.get(profile["id"])
        if existing and (existing.status == "running" or job_has_live_process(existing)):
            raise RuntimeError("当前方案已有任务正在运行")
        for other_profile_id, other_job in jobs_by_profile.items():
            if other_profile_id == profile["id"] or other_job.status != "running":
                continue
            other_profile = profiles_by_id.get(other_profile_id)
            if not other_profile:
                continue
            if profile_data_dir(other_profile).resolve() == target_dir:
                raise RuntimeError(
                    f"方案“{other_job.profile_name}”正在使用相同保存文件夹。并行运行前，请先为不同方案设置不同保存文件夹。"
                )
        jobs_by_profile[profile["id"]] = job
    thread = threading.Thread(target=run_job_target, args=(target, job, profile["id"], args), daemon=True)
    thread.start()
    return job


def finish_job(job: Job, status: str, return_code: int | None = None, error: str = "") -> None:
    with job.lock:
        job.status = status
        job.ended_at = utc_now()
        job.return_code = return_code
        job.error = error
    clear_profile_stats(job.profile_id)
    if error:
        job.append(f"错误: {error}")


def is_job_stopped(job: Job) -> bool:
    with job.lock:
        return job.status == "stopped"


def resolve_command(name: str) -> str | None:
    resolved = shutil.which(name)
    if resolved:
        return resolved

    executable_names = [name]
    if os.name == "nt" and not name.lower().endswith(".exe"):
        executable_names.append(f"{name}.exe")

    bin_dir = "Scripts" if os.name == "nt" else "bin"
    candidate_dirs = [
        Path(sys.executable).parent,
        Path(sys.prefix) / bin_dir,
    ]
    if os.environ.get("VIRTUAL_ENV"):
        candidate_dirs.append(Path(os.environ["VIRTUAL_ENV"]) / bin_dir)

    seen: set[Path] = set()
    for directory in candidate_dirs:
        if directory in seen:
            continue
        seen.add(directory)
        for executable_name in executable_names:
            candidate = directory / executable_name
            if candidate.exists():
                return str(candidate)

    return None


def command_exists(name: str) -> bool:
    return resolve_command(name) is not None


def wait_for_retry(job: Job, seconds: int) -> bool:
    deadline = time.time() + max(0, seconds)
    while time.time() < deadline:
        if is_job_stopped(job):
            return False
        time.sleep(min(1, deadline - time.time()))
    return not is_job_stopped(job)


def build_base_icloudpd_args(
    profile: dict[str, Any],
    directory: Path,
    cookie_dir: Path,
    password: str = "",
    include_media_mode: bool = True,
) -> list[str]:
    args = [
        resolve_command("icloudpd") or "icloudpd",
        "--directory",
        str(directory),
        "--username",
        profile["apple_id"],
        "--cookie-directory",
        str(cookie_dir),
        "--domain",
        profile.get("domain", "com"),
        "--mfa-provider",
        "console",
        "--no-progress-bar",
    ]

    effective_password = password or str(profile.get("password") or "")
    if effective_password:
        args.extend(["--password-provider", "parameter", "--password", effective_password])
    else:
        args.extend(["--password-provider", "keyring"])

    if profile.get("folder_structure"):
        args.extend(["--folder-structure", profile["folder_structure"]])
    if profile.get("size"):
        args.extend(["--size", profile["size"]])
    if profile.get("live_photo_size"):
        args.extend(["--live-photo-size", profile["live_photo_size"]])
    if profile.get("force_size"):
        args.append("--force-size")
    if profile.get("album"):
        args.extend(["--album", str(profile["album"]).strip()])
    if profile.get("library"):
        args.extend(["--library", str(profile["library"]).strip()])
    if profile.get("align_raw"):
        args.extend(["--align-raw", profile["align_raw"]])
    if profile.get("file_match_policy"):
        args.extend(["--file-match-policy", profile["file_match_policy"]])
    if profile.get("recent"):
        args.extend(["--recent", profile["recent"]])
    if profile.get("until_found"):
        args.extend(["--until-found", profile["until_found"]])
    if include_media_mode:
        if profile.get("media_mode") == "mirror":
            args.append("--auto-delete")
        if profile.get("media_mode") == "move":
            args.extend(["--keep-icloud-recent-days", "0"])
    if not profile.get("include_live_photos", True):
        args.append("--skip-live-photos")
    if profile.get("keep_unicode", True):
        args.append("--keep-unicode-in-filenames")
    if profile.get("set_exif_datetime", True):
        args.append("--set-exif-datetime")
    return args


def run_process(job: Job, args: list[str]) -> int:
    safe_args = mask_command(args)
    job.append("$ " + " ".join(safe_args))
    popen_kwargs: dict[str, Any] = {
        "args": args,
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
    }
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(**popen_kwargs)
    except OSError as exc:
        with job.lock:
            job.waiting_input = False
            job.process = None
        job.append(f"启动命令失败: {exc}")
        return 127
    with job.lock:
        job.process = process
    assert process.stdout is not None
    for line in process.stdout:
        prompt_detected = looks_like_input_prompt(line)
        with job.lock:
            if prompt_detected:
                job.waiting_input = True
            elif job.waiting_input and line.strip():
                job.waiting_input = False
        job.append(line)
    code = process.wait()
    with job.lock:
        job.waiting_input = False
        job.process = None
    return code


def terminate_process(process: subprocess.Popen[str], timeout_seconds: int = 10) -> int | None:
    if process.poll() is not None:
        return process.returncode

    def send_signal(sig: signal.Signals) -> None:
        try:
            if os.name != "nt":
                os.killpg(process.pid, sig)
            elif sig == signal.SIGTERM:
                process.terminate()
            else:
                process.kill()
        except ProcessLookupError:
            pass
        except OSError:
            try:
                process.terminate() if sig == signal.SIGTERM else process.kill()
            except OSError:
                pass

    send_signal(signal.SIGTERM)
    try:
        return process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        send_signal(getattr(signal, "SIGKILL", signal.SIGTERM))
        try:
            return process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            return None


def mask_command(args: list[str]) -> list[str]:
    masked: list[str] = []
    skip_next = False
    for idx, item in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if item == "--password" and idx + 1 < len(args):
            masked.extend(["--password", "******"])
            skip_next = True
        else:
            masked.append(item)
    return masked


def looks_like_input_prompt(line: str) -> bool:
    lowered = line.strip().lower()
    if not lowered:
        return False

    prompt_patterns = [
        r"(enter|input|provide|send).*(verification code|security code|2fa|two-factor|two factor|mfa)",
        r"(verification code|security code|2fa|two-factor|two factor|mfa).*(enter|input|required|needed|waiting)",
        r"press enter to continue",
        r"confirmation required",
        r"waiting for .*code",
        r"please confirm",
    ]
    return any(re.search(pattern, lowered) for pattern in prompt_patterns)


def run_auth_job(job: Job, profile_id: str, password: str) -> None:
    profile = get_profile(load_config(), profile_id)
    if not profile.get("apple_id"):
        finish_job(job, "failed", error="请先填写 Apple ID")
        return
    if not password and not profile.get("password"):
        finish_job(job, "failed", error="认证需要输入 Apple ID 密码或已保存的密码")
        return
    if not command_exists("icloudpd"):
        finish_job(job, "failed", error="icloudpd 未安装，首次启动依赖安装可能尚未完成")
        return

    root = profile_data_dir(profile)
    cookie_dir = profile_cookie_dir(profile)
    auth_dir = root / "auth-check"
    root.mkdir(parents=True, exist_ok=True)
    cookie_dir.mkdir(parents=True, exist_ok=True)
    auth_dir.mkdir(parents=True, exist_ok=True)
    args = build_base_icloudpd_args(profile, auth_dir, cookie_dir, password=password, include_media_mode=False)
    args.append("--auth-only")
    code = run_process(job, args)
    finish_job(job, "success" if code == 0 else "failed", return_code=code)


def run_media_job(job: Job, profile_id: str) -> None:
    profile = get_profile(load_config(), profile_id)
    if not profile.get("apple_id"):
        finish_job(job, "failed", error="请先保存 Apple ID")
        return
    if not profile.get("photos_enabled") and not profile.get("videos_enabled"):
        finish_job(job, "failed", error="请至少启用照片或视频同步")
        return
    if not command_exists("icloudpd"):
        finish_job(job, "failed", error="icloudpd 未安装，首次启动依赖安装可能尚未完成")
        return

    root = profile_data_dir(profile)
    cookie_dir = profile_cookie_dir(profile)
    root.mkdir(parents=True, exist_ok=True)
    cookie_dir.mkdir(parents=True, exist_ok=True)
    if profile.get("media_mode") == "move":
        job.append("危险模式: 本次同步成功后会请求删除 iCloud 云端对应媒体文件，请确认 NAS 已有备份。")

    commands: list[tuple[str, list[str]]] = []
    if profile.get("photos_enabled"):
        photo_dir = root / "photos"
        photo_dir.mkdir(parents=True, exist_ok=True)
        args = build_base_icloudpd_args(profile, photo_dir, cookie_dir)
        args.append("--skip-videos")
        commands.append(("照片", args))
    if profile.get("videos_enabled"):
        video_dir = root / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)
        args = build_base_icloudpd_args(profile, video_dir, cookie_dir)
        args.append("--skip-photos")
        commands.append(("视频", args))

    final_code = 0
    retry_attempts = max(0, int_or_default(profile.get("retry_attempts"), 3))
    retry_delay_seconds = max(0, int_or_default(profile.get("retry_delay_seconds"), 60))
    for title, args in commands:
        code = 1
        for attempt in range(retry_attempts + 1):
            if is_job_stopped(job):
                code = -1
                break
            if attempt == 0:
                job.append(f"开始同步{title}: {profile['name']}")
            else:
                job.append(f"第 {attempt + 1}/{retry_attempts + 1} 次重试同步{title}")
            code = run_process(job, args)
            if code == 0:
                break
            if is_job_stopped(job):
                break
            if attempt < retry_attempts:
                job.append(f"同步{title}失败，返回码 {code}。{retry_delay_seconds} 秒后自动重试。")
                if not wait_for_retry(job, retry_delay_seconds):
                    code = -1
                    break
        final_code = code
        if code != 0:
            break

    if final_code == 0:
        update_profile_state(profile_id, {"last_media_sync": utc_now()})
    if not is_job_stopped(job):
        finish_job(job, "success" if final_code == 0 else "failed", return_code=final_code)


def decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def sanitize_filename(value: str, fallback: str = "note") -> str:
    value = html.unescape(value).strip() or fallback
    value = re.sub(r"[\\/:*?\"<>|]+", "_", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:120] or fallback


def message_body(message: Message) -> tuple[str, str]:
    text_body = ""
    html_body = ""
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                continue
            payload = decode_payload(part)
            if content_type == "text/plain" and payload and not text_body:
                text_body = payload
            elif content_type == "text/html" and payload and not html_body:
                html_body = payload
    else:
        payload = decode_payload(message)
        if message.get_content_type() == "text/html":
            html_body = payload
        else:
            text_body = payload
    return text_body, html_body


def decode_payload(part: Message) -> str:
    raw = part.get_payload(decode=True)
    if raw is None:
        raw_text = part.get_payload()
        return raw_text if isinstance(raw_text, str) else ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def html_to_text(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value)
    return parser.text()


def choose_mailbox(client: imaplib.IMAP4_SSL, preferred: str, job: Job) -> str:
    status, boxes = client.list()
    if status != "OK":
        return preferred
    decoded: list[str] = []
    for item in boxes or []:
        text = item.decode("utf-8", errors="replace") if isinstance(item, bytes) else str(item)
        match = re.search(r' "([^"]+)"$', text)
        if match:
            decoded.append(match.group(1))
    if preferred in decoded:
        return preferred
    lowered = {box.lower(): box for box in decoded}
    for candidate in [preferred.lower(), "notes", "备忘录"]:
        if candidate in lowered:
            return lowered[candidate]
    for box in decoded:
        if "note" in box.lower() or "备忘" in box:
            return box
    job.append("未找到指定备忘录邮箱，尝试使用配置中的文件夹名称")
    return preferred


def run_notes_job(job: Job, profile_id: str) -> None:
    profile = get_profile(load_config(), profile_id)
    notes = profile.get("notes", {})
    username = str(notes.get("username") or profile.get("apple_id") or "").strip()
    password = str(notes.get("password") or "").strip()
    if not username or not password:
        finish_job(job, "failed", error="备忘录导出需要 IMAP 用户名和 Apple App 专用密码")
        return

    root = profile_data_dir(profile)
    output_dir = root / "notes"
    output_dir.mkdir(parents=True, exist_ok=True)
    host = str(notes.get("host") or "imap.mail.me.com")
    port = int_or_default(notes.get("port"), 993)
    limit = int_or_default(notes.get("limit"), 0)

    try:
        job.append(f"连接 IMAP: {host}:{port}")
        client = imaplib.IMAP4_SSL(host, port, timeout=45)
        client.login(username, password)
        mailbox = choose_mailbox(client, str(notes.get("folder") or "Notes"), job)
        job.append(f"选择邮箱: {mailbox}")
        status, _ = client.select(f'"{mailbox}"', readonly=True)
        if status != "OK":
            status, _ = client.select(mailbox, readonly=True)
        if status != "OK":
            raise RuntimeError(f"无法打开 IMAP 文件夹: {mailbox}")

        status, data = client.search(None, "ALL")
        if status != "OK":
            raise RuntimeError("无法读取备忘录列表")
        ids = data[0].split()
        if limit > 0:
            ids = ids[-limit:]
        job.append(f"准备导出 {len(ids)} 条备忘录")

        exported = 0
        for item in ids:
            status, fetched = client.fetch(item, "(RFC822)")
            if status != "OK" or not fetched:
                continue
            raw_message = fetched[0][1]
            if not isinstance(raw_message, bytes):
                continue
            message = email.message_from_bytes(raw_message)
            subject = decode_header_value(message.get("Subject")) or "Untitled"
            date_header = decode_header_value(message.get("Date"))
            text_body, html_body = message_body(message)
            uid = item.decode("ascii", errors="ignore")
            filename_base = sanitize_filename(f"{uid}-{subject}")
            if notes.get("format") == "html":
                body = html_body or f"<pre>{html.escape(text_body)}</pre>"
                target = output_dir / f"{filename_base}.html"
                target.write_text(body, encoding="utf-8")
            else:
                body_text = text_body or html_to_text(html_body)
                markdown = "\n".join(
                    [
                        "---",
                        f"title: {json.dumps(subject, ensure_ascii=False)}",
                        f"date: {json.dumps(date_header, ensure_ascii=False)}",
                        f"imap_uid: {json.dumps(uid, ensure_ascii=False)}",
                        "---",
                        "",
                        body_text.strip(),
                        "",
                    ]
                )
                target = output_dir / f"{filename_base}.md"
                target.write_text(markdown, encoding="utf-8")
            exported += 1

        client.close()
        client.logout()
        job.append(f"备忘录导出完成: {exported} 个文件")
        update_profile_state(profile_id, {"last_notes_sync": utc_now()})
        finish_job(job, "success", return_code=0)
    except Exception as exc:
        finish_job(job, "failed", return_code=1, error=str(exc))


def file_count(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for _, _, files in os.walk(path):
        total += len(files)
    return total


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def collect_profile_storage_stats(profile: dict[str, Any]) -> dict[str, Any]:
    root = profile_data_dir(profile)
    photos_dir = root / "photos"
    videos_dir = root / "videos"
    notes_dir = root / "notes"
    return {
        "paths": {
            "data": str(root),
            "photos": str(photos_dir),
            "videos": str(videos_dir),
            "notes": str(notes_dir),
        },
        "counts": {
            "photos": file_count(photos_dir),
            "videos": file_count(videos_dir),
            "notes": file_count(notes_dir),
        },
        "bytes": directory_size(root),
    }


def profile_storage_stats(profile: dict[str, Any]) -> dict[str, Any]:
    profile_id = profile["id"]
    now = time.time()
    with stats_lock:
        cached = stats_cache.get(profile_id)
        if cached and now - cached[0] < STATS_CACHE_TTL_SECONDS:
            return deep_copy(cached[1])

    stats = collect_profile_storage_stats(profile)
    with stats_lock:
        stats_cache[profile_id] = (now, deep_copy(stats))
    return stats


def clear_profile_stats(profile_id: str) -> None:
    with stats_lock:
        stats_cache.pop(profile_id, None)


def scheduler_payload(profile: dict[str, Any], state: dict[str, Any], now_ts: float | None = None) -> dict[str, Any]:
    now = time.time() if now_ts is None else now_ts
    schedule_enabled = bool(profile.get("schedule_enabled"))
    media_enabled = bool(profile.get("photos_enabled") or profile.get("videos_enabled"))
    notes_enabled = bool(profile.get("notes_enabled"))
    content_enabled = media_enabled or notes_enabled
    interval_minutes = max(15, int_or_default(profile.get("sync_interval_minutes"), 360))
    interval_seconds = interval_minutes * 60
    last_media_ts = max(
        iso_to_timestamp(state.get("last_media_sync")),
        iso_to_timestamp(state.get("last_media_schedule_attempt")),
    )
    last_notes_ts = max(
        iso_to_timestamp(state.get("last_notes_sync")),
        iso_to_timestamp(state.get("last_notes_schedule_attempt")),
    )
    media_next_ts = (last_media_ts + interval_seconds) if last_media_ts else now
    notes_next_ts = (last_notes_ts + interval_seconds) if last_notes_ts else now
    next_candidates = []
    if media_enabled:
        next_candidates.append(media_next_ts)
    if notes_enabled:
        next_candidates.append(notes_next_ts)
    next_ts = min(next_candidates) if next_candidates else now
    seconds_until_next = max(0, int(next_ts - now))
    active = schedule_enabled and content_enabled
    media_due = active and media_enabled and now >= media_next_ts
    notes_due = active and notes_enabled and now >= notes_next_ts

    return {
        "schedule_enabled": schedule_enabled,
        "media_enabled": media_enabled,
        "notes_enabled": notes_enabled,
        "content_enabled": content_enabled,
        "active": active,
        "interval_minutes": interval_minutes,
        "loop_interval_seconds": 60,
        "last_check": state.get("last_scheduler_check", ""),
        "last_trigger": state.get("last_scheduler_trigger", ""),
        "check_count": max(0, int_or_default(state.get("scheduler_check_count"), 0)),
        "trigger_count": max(0, int_or_default(state.get("scheduler_trigger_count"), 0)),
        "last_status": state.get("last_scheduler_status", ""),
        "last_message": state.get("last_scheduler_message", ""),
        "next_run": timestamp_to_iso(max(next_ts, now)) if active else "",
        "seconds_until_next": seconds_until_next if active else None,
        "media_due": media_due,
        "notes_due": notes_due,
        "due": media_due or notes_due,
    }


def profile_summary(profile: dict[str, Any], job: dict[str, Any] | None = None) -> dict[str, Any]:
    state = get_profile_state(profile["id"])
    scheduler = scheduler_payload(profile, state)
    return {
        "id": profile["id"],
        "name": profile["name"],
        "data_subdir": profile.get("data_subdir", ""),
        "apple_id": profile.get("apple_id", ""),
        "photos_enabled": profile.get("photos_enabled", False),
        "videos_enabled": profile.get("videos_enabled", False),
        "notes_enabled": profile.get("notes_enabled", False),
        "schedule_enabled": profile.get("schedule_enabled", False),
        "last_media_sync": state.get("last_media_sync", ""),
        "last_notes_sync": state.get("last_notes_sync", ""),
        "scheduler": scheduler,
        "job": job,
    }


def status_payload(profile_id: str | None = None) -> dict[str, Any]:
    config = load_config()
    profile = get_profile(config, profile_id)
    state = get_profile_state(profile["id"])
    storage_root = load_storage_root()
    applied_root_path = normalize_root_path(SYNC_ROOT_HOST_PATH)
    restart_required = storage_root["selected_root_path"] != applied_root_path
    icloudpd_path = resolve_command("icloudpd")
    with job_lock:
        profile_jobs = {job_profile_id: item.to_dict(include_log=False) for job_profile_id, item in jobs_by_profile.items()}
        job = jobs_by_profile.get(profile["id"]).to_dict() if jobs_by_profile.get(profile["id"]) else None
        active_jobs = sum(1 for item in jobs_by_profile.values() if item.status == "running")
    storage = profile_storage_stats(profile)
    return {
        "active_profile_id": config["active_profile_id"],
        "profile_id": profile["id"],
        "profiles": [profile_summary(item, profile_jobs.get(item["id"])) for item in config.get("profiles", [])],
        "state": state,
        "scheduler": scheduler_payload(profile, state),
        "job": job,
        "running_jobs_count": active_jobs,
        "paths": storage["paths"],
        "counts": storage["counts"],
        "bytes": storage["bytes"],
        "storage": {
            "selected_root_path": storage_root["selected_root_path"],
            "applied_root_path": applied_root_path,
            "using_default_root": storage_root["using_default_root"],
            "authorized_paths": storage_root["authorized_paths"],
            "updated_at": storage_root["updated_at"],
            "container_root": str(DATA_DIR),
            "restart_required": restart_required,
        },
        "icloudpd_available": icloudpd_path is not None,
        "icloudpd_path": icloudpd_path or "",
        "python_executable": sys.executable,
    }


def storage_mount_needs_recreate() -> bool:
    storage_root = load_storage_root()
    applied_root_path = normalize_root_path(SYNC_ROOT_HOST_PATH)
    return storage_root["selected_root_path"] != applied_root_path


def storage_mount_error_response():
    return jsonify({
        "error": "同步根目录还没有生效。请在飞牛应用中心停止后重新启动本应用，等服务读取新路径后再开始同步。"
    }), 409


def timestamp_or_zero(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0


def schedule_due(state: dict[str, Any], success_key: str, attempt_key: str, interval_seconds: int) -> bool:
    last_time = max(timestamp_or_zero(state.get(success_key)), timestamp_or_zero(state.get(attempt_key)))
    return time.time() - last_time >= interval_seconds


def mark_schedule_attempt(profile_id: str, attempt_key: str) -> None:
    now = utc_now()
    update_profile_state(profile_id, {
        attempt_key: now,
        "last_scheduler_check": now,
    })


def log_scheduler_exception(exc: Exception, profile_id: str = "") -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context = f" profile={profile_id}" if profile_id else ""
    message = f"[{timestamp}] scheduler error{context}: {exc}\n{traceback.format_exc()}"
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (LOG_DIR / "scheduler.log").open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except OSError:
        pass
    print(message, file=sys.stderr, flush=True)


def scheduler_loop() -> None:
    while True:
        time.sleep(60)
        try:
            config = load_config()
            mount_needs_recreate = storage_mount_needs_recreate()
        except Exception as exc:
            log_scheduler_exception(exc)
            continue

        for profile in config.get("profiles", []):
            try:
                if not profile.get("schedule_enabled"):
                    continue
                state = get_profile_state(profile["id"])
                now_ts = time.time()
                now_iso = timestamp_to_iso(now_ts)
                scheduler = scheduler_payload(profile, state, now_ts)
                updates = {
                    "last_scheduler_check": now_iso,
                    "scheduler_check_count": scheduler["check_count"] + 1,
                    "last_scheduler_status": "checked",
                    "last_scheduler_message": "尚未到下次同步时间",
                }
                if not scheduler["content_enabled"]:
                    updates.update({
                        "last_scheduler_status": "skipped",
                        "last_scheduler_message": "未选择照片、视频或备忘录，已跳过计划同步",
                    })
                    update_profile_state(profile["id"], updates)
                    continue
                if mount_needs_recreate:
                    updates.update({
                        "last_scheduler_status": "blocked",
                        "last_scheduler_message": "同步根目录尚未重启生效，已跳过本次检查",
                    })
                    update_profile_state(profile["id"], updates)
                    continue
                if not scheduler["due"]:
                    update_profile_state(profile["id"], updates)
                    continue

                allowed, reason = can_start_job(profile["id"])
                if not allowed:
                    updates.update({
                        "last_scheduler_status": "skipped",
                        "last_scheduler_message": reason or "当前方案已有任务正在运行，已等待下次检查",
                    })
                    update_profile_state(profile["id"], updates)
                    continue

                if scheduler["media_due"]:
                    attempt_key = "last_media_schedule_attempt"
                    job_kind = "scheduled-media-sync"
                    job_target = run_media_job
                    starting_message = "正在启动计划媒体同步任务"
                    started_message = "已启动计划媒体同步任务"
                elif scheduler["notes_due"]:
                    attempt_key = "last_notes_schedule_attempt"
                    job_kind = "scheduled-notes-export"
                    job_target = run_notes_job
                    starting_message = "正在启动计划备忘录导出"
                    started_message = "已启动计划备忘录导出"
                else:
                    updates.update({
                        "last_scheduler_status": "skipped",
                        "last_scheduler_message": "没有到期的计划任务",
                    })
                    update_profile_state(profile["id"], updates)
                    continue

                updates.update({
                    attempt_key: now_iso,
                    "last_scheduler_status": "starting",
                    "last_scheduler_message": starting_message,
                })
                update_profile_state(profile["id"], updates)
                try:
                    start_job(job_kind, profile["id"], job_target)
                except Exception as exc:
                    update_profile_state(profile["id"], {
                        "last_scheduler_status": "failed",
                        "last_scheduler_message": str(exc),
                    })
                    log_scheduler_exception(exc, str(profile.get("id") or ""))
                else:
                    update_profile_state(profile["id"], {
                        "last_scheduler_trigger": now_iso,
                        "scheduler_trigger_count": scheduler["trigger_count"] + 1,
                        "last_scheduler_status": "started",
                        "last_scheduler_message": started_message,
                    })
            except Exception as exc:
                log_scheduler_exception(exc, str(profile.get("id") or ""))


@app.get("/")
def index():
    return send_from_directory(APP_DIR / "static", "index.html")


@app.get("/api/config")
def api_get_config():
    return jsonify(public_config(load_config()))


@app.post("/api/config")
def api_save_config():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        saved = save_config(payload)
        return jsonify(public_config(saved))
    except KeyError:
        return jsonify({"error": "方案不存在"}), 404


@app.post("/api/profiles")
def api_create_profile():
    payload = request.get_json(force=True, silent=True) or {}
    with config_lock:
        config = load_config()
        default_name = f"iCloud 方案 {len(config.get('profiles', [])) + 1}"
        profile = make_profile(str(payload.get("name") or default_name))
        config["profiles"].append(profile)
        config["active_profile_id"] = profile["id"]
        write_json(CONFIG_FILE, config)
    return jsonify(public_config(config))


@app.post("/api/profiles/<profile_id>/select")
def api_select_profile(profile_id: str):
    try:
        config = save_config({"active_profile_id": profile_id, "profile_id": profile_id})
        return jsonify(public_config(config))
    except KeyError:
        return jsonify({"error": "方案不存在"}), 404


@app.delete("/api/profiles/<profile_id>")
def api_delete_profile(profile_id: str):
    payload = request.get_json(force=True, silent=True) or {}
    running_job = profile_job(profile_id)
    if running_job and running_job.status == "running":
        return jsonify({"error": "请先停止当前方案的运行中任务，再删除方案"}), 409
    with config_lock:
        config = load_config()
        if len(config.get("profiles", [])) <= 1:
            return jsonify({"error": "至少保留一个方案"}), 409
        try:
            idx = profile_index(config, profile_id)
        except KeyError:
            return jsonify({"error": "方案不存在"}), 404
        profile = config["profiles"].pop(idx)
        if config["active_profile_id"] == profile_id:
            config["active_profile_id"] = config["profiles"][0]["id"]
        write_json(CONFIG_FILE, config)
        state = load_state()
        state.setdefault("profiles", {}).pop(profile_id, None)
        save_state(state)

    if payload.get("delete_data"):
        for path in (profile_data_dir(profile), profile_cookie_dir(profile)):
            try:
                resolved = path.resolve()
                if (resolved == DATA_DIR or DATA_DIR in resolved.parents or COOKIE_ROOT in resolved.parents) and resolved.exists():
                    shutil.rmtree(resolved)
            except OSError:
                pass
    with job_lock:
        jobs_by_profile.pop(profile_id, None)
    clear_profile_stats(profile_id)
    return jsonify(public_config(load_config()))


@app.get("/api/status")
def api_status():
    return jsonify(status_payload(request.args.get("profile_id")))


@app.get("/api/job")
def api_job():
    profile_id = str(request.args.get("profile_id") or load_config().get("active_profile_id"))
    job = profile_job(profile_id)
    return jsonify(job.to_dict() if job else {"status": "idle", "log": []})


@app.post("/api/auth")
def api_auth():
    payload = request.get_json(force=True, silent=True) or {}
    profile_id = str(payload.get("profile_id") or load_config().get("active_profile_id"))
    updates: dict[str, Any] = {"profile_id": profile_id}
    if "apple_id" in payload:
        updates["apple_id"] = payload.get("apple_id", "")
    if "store_password" in payload:
        updates["store_password"] = bool(payload.get("store_password"))
    if payload.get("store_password"):
        updates["password"] = payload.get("password", "")
    if updates:
        save_config(updates)
    try:
        job = start_job("auth", profile_id, run_auth_job, str(payload.get("password") or ""))
        return jsonify(job.to_dict())
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 409


@app.post("/api/sync/media")
def api_sync_media():
    payload = request.get_json(force=True, silent=True) or {}
    profile_id = str(payload.get("profile_id") or load_config().get("active_profile_id"))
    if storage_mount_needs_recreate():
        return storage_mount_error_response()
    try:
        job = start_job("media-sync", profile_id, run_media_job)
        return jsonify(job.to_dict())
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 409


@app.post("/api/sync/notes")
def api_sync_notes():
    payload = request.get_json(force=True, silent=True) or {}
    profile_id = str(payload.get("profile_id") or load_config().get("active_profile_id"))
    if storage_mount_needs_recreate():
        return storage_mount_error_response()
    try:
        job = start_job("notes-export", profile_id, run_notes_job)
        return jsonify(job.to_dict())
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 409


@app.post("/api/job/input")
def api_job_input():
    payload = request.get_json(force=True, silent=True) or {}
    profile_id = str(payload.get("profile_id") or load_config().get("active_profile_id"))
    value = str(payload.get("value") or "")
    with job_lock:
        job = jobs_by_profile.get(profile_id)
        process = job.process if job else None
    if not job or not process or not process.stdin or job.status != "running":
        return jsonify({"error": "当前没有可输入的运行中任务"}), 409
    try:
        process.stdin.write(value + "\n")
        process.stdin.flush()
    except OSError:
        return jsonify({"error": "任务控制台已关闭，请查看最新日志确认任务状态"}), 409
    with job.lock:
        job.waiting_input = False
    job.append("已发送控制台输入")
    return jsonify(job.to_dict())


@app.post("/api/job/stop")
def api_job_stop():
    payload = request.get_json(force=True, silent=True) or {}
    profile_id = str(payload.get("profile_id") or load_config().get("active_profile_id"))
    with job_lock:
        job = jobs_by_profile.get(profile_id)
    if not job:
        return jsonify({"error": "当前没有运行中任务"}), 409
    with job.lock:
        process = job.process
        job_status = job.status
    if job_status != "running":
        return jsonify({"error": "当前没有运行中任务"}), 409
    if process and process.poll() is None:
        job.append("正在停止任务...")
        return_code = terminate_process(process)
        if return_code is None:
            finish_job(job, "failed", return_code=1, error="任务停止超时，请稍后检查进程是否仍在运行")
            return jsonify(job.to_dict()), 500
    finish_job(job, "stopped", return_code=-1)
    return jsonify(job.to_dict())


threading.Thread(target=scheduler_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
