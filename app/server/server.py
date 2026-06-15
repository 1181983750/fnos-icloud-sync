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
    "domain": "com",
    "folder_structure": "{:%Y/%m/%d}",
    "media_mode": "copy",
    "recent": "",
    "until_found": "",
    "album": "",
    "library": "",
    "size": "original",
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
current_job: "Job | None" = None
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

    def append(self, text: str) -> None:
        line = text.rstrip("\n")
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {line}" if line else ""
        self.log_lines.append(formatted)
        if len(self.log_lines) > MAX_LOG_LINES:
            self.log_lines = self.log_lines[-MAX_LOG_LINES:]
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(formatted + "\n")

    def to_dict(self) -> dict[str, Any]:
        return {
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
            "log": self.log_lines[-250:],
        }


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
    profile["data_subdir"] = profile_id
    return profile


def normalize_profile(profile: dict[str, Any]) -> None:
    profile["id"] = str(profile.get("id") or ("p_" + uuid.uuid4().hex[:10]))
    profile["name"] = str(profile.get("name") or profile.get("apple_id") or "未命名方案").strip()
    profile["data_subdir"] = str(profile.get("data_subdir", profile["id"]))
    profile["apple_id"] = str(profile.get("apple_id", "")).strip()
    profile["domain"] = "cn" if str(profile.get("domain", "com")).lower() == "cn" else "com"
    profile["media_mode"] = "mirror" if profile.get("media_mode") == "mirror" else "copy"
    profile["size"] = str(profile.get("size") or "original")
    profile["folder_structure"] = str(profile.get("folder_structure") or "{:%Y/%m/%d}")
    profile["sync_interval_minutes"] = max(15, int_or_default(profile.get("sync_interval_minutes"), 360))
    profile["recent"] = normalize_number_string(profile.get("recent"))
    profile["until_found"] = normalize_number_string(profile.get("until_found"))
    for key in [
        "photos_enabled",
        "videos_enabled",
        "notes_enabled",
        "schedule_enabled",
        "store_password",
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
    selected_root_path = str(raw.get("selected_root_path") or SYNC_ROOT_HOST_PATH).strip() or SYNC_ROOT_HOST_PATH
    authorized_paths = raw.get("authorized_paths", [])
    if not isinstance(authorized_paths, list):
        authorized_paths = []

    normalized_paths: list[str] = []
    for item in authorized_paths:
        text = str(item or "").strip()
        if text:
            normalized_paths.append(text)

    return {
        "selected_root_path": selected_root_path,
        "using_default_root": bool(raw.get("using_default_root", selected_root_path == SYNC_ROOT_HOST_PATH)),
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
    return DATA_DIR / "profiles" / subdir


def profile_cookie_dir(profile: dict[str, Any]) -> Path:
    return COOKIE_ROOT / profile["id"]


def can_start_job() -> tuple[bool, str]:
    with job_lock:
        if current_job and current_job.status == "running":
            return False, "已有任务正在运行"
    return True, ""


def start_job(kind: str, profile_id: str, target, *args) -> Job:
    global current_job
    allowed, message = can_start_job()
    if not allowed:
        raise RuntimeError(message)

    profile = get_profile(load_config(), profile_id)
    job = Job(kind=kind, profile_id=profile["id"], profile_name=profile["name"])
    log_dir = LOG_DIR / profile["id"]
    log_dir.mkdir(parents=True, exist_ok=True)
    job.log_path = log_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{kind}-{job.id}.log"
    with job_lock:
        current_job = job
    thread = threading.Thread(target=target, args=(job, profile["id"], *args), daemon=True)
    thread.start()
    return job


def finish_job(job: Job, status: str, return_code: int | None = None, error: str = "") -> None:
    job.status = status
    job.ended_at = utc_now()
    job.return_code = return_code
    job.error = error
    clear_profile_stats(job.profile_id)
    if error:
        job.append(f"错误: {error}")


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


def build_base_icloudpd_args(
    profile: dict[str, Any],
    directory: Path,
    cookie_dir: Path,
    password: str = "",
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
    if profile.get("album"):
        args.extend(["--album", str(profile["album"]).strip()])
    if profile.get("library"):
        args.extend(["--library", str(profile["library"]).strip()])
    if profile.get("recent"):
        args.extend(["--recent", profile["recent"]])
    if profile.get("until_found"):
        args.extend(["--until-found", profile["until_found"]])
    if profile.get("media_mode") == "mirror":
        args.append("--auto-delete")
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
    process = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    job.process = process
    assert process.stdout is not None
    for line in process.stdout:
        if looks_like_input_prompt(line):
            job.waiting_input = True
        job.append(line)
    code = process.wait()
    job.waiting_input = False
    job.process = None
    return code


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
    lowered = line.lower()
    markers = [
        "verification code",
        "two-factor",
        "two factor",
        "mfa",
        "2fa",
        "password",
        "enter code",
        "security code",
    ]
    return any(marker in lowered for marker in markers)


def run_auth_job(job: Job, profile_id: str, password: str) -> None:
    profile = get_profile(load_config(), profile_id)
    if not profile.get("apple_id"):
        finish_job(job, "failed", error="请先填写 Apple ID")
        return
    if not password and not profile.get("password"):
        finish_job(job, "failed", error="认证需要输入 Apple ID 密码或已保存的密码")
        return
    if not command_exists("icloudpd"):
        finish_job(job, "failed", error="icloudpd 未安装，容器首次启动依赖安装可能尚未完成")
        return

    root = profile_data_dir(profile)
    cookie_dir = profile_cookie_dir(profile)
    root.mkdir(parents=True, exist_ok=True)
    cookie_dir.mkdir(parents=True, exist_ok=True)
    args = build_base_icloudpd_args(profile, root / "auth-check", cookie_dir, password=password)
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
        finish_job(job, "failed", error="icloudpd 未安装，容器首次启动依赖安装可能尚未完成")
        return

    root = profile_data_dir(profile)
    cookie_dir = profile_cookie_dir(profile)
    root.mkdir(parents=True, exist_ok=True)
    cookie_dir.mkdir(parents=True, exist_ok=True)

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
    for title, args in commands:
        job.append(f"开始同步{title}: {profile['name']}")
        code = run_process(job, args)
        final_code = code
        if code != 0:
            break

    if final_code == 0:
        update_profile_state(profile_id, {"last_media_sync": utc_now()})
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


def profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    state = get_profile_state(profile["id"])
    return {
        "id": profile["id"],
        "name": profile["name"],
        "apple_id": profile.get("apple_id", ""),
        "photos_enabled": profile.get("photos_enabled", False),
        "videos_enabled": profile.get("videos_enabled", False),
        "notes_enabled": profile.get("notes_enabled", False),
        "schedule_enabled": profile.get("schedule_enabled", False),
        "last_media_sync": state.get("last_media_sync", ""),
        "last_notes_sync": state.get("last_notes_sync", ""),
    }


def status_payload(profile_id: str | None = None) -> dict[str, Any]:
    config = load_config()
    profile = get_profile(config, profile_id)
    state = get_profile_state(profile["id"])
    storage_root = load_storage_root()
    icloudpd_path = resolve_command("icloudpd")
    with job_lock:
        job = current_job.to_dict() if current_job else None
    storage = profile_storage_stats(profile)
    return {
        "active_profile_id": config["active_profile_id"],
        "profile_id": profile["id"],
        "profiles": [profile_summary(item) for item in config.get("profiles", [])],
        "state": state,
        "job": job,
        "paths": storage["paths"],
        "counts": storage["counts"],
        "bytes": storage["bytes"],
        "storage": {
            "selected_root_path": storage_root["selected_root_path"],
            "applied_root_path": SYNC_ROOT_HOST_PATH,
            "using_default_root": storage_root["using_default_root"],
            "authorized_paths": storage_root["authorized_paths"],
            "updated_at": storage_root["updated_at"],
            "container_root": str(DATA_DIR),
            "restart_required": storage_root["selected_root_path"] != SYNC_ROOT_HOST_PATH,
        },
        "icloudpd_available": icloudpd_path is not None,
        "icloudpd_path": icloudpd_path or "",
        "python_executable": sys.executable,
    }


def scheduler_loop() -> None:
    while True:
        time.sleep(60)
        try:
            config = load_config()
            for profile in config.get("profiles", []):
                if not profile.get("schedule_enabled"):
                    continue
                state = get_profile_state(profile["id"])
                interval = max(15, int_or_default(profile.get("sync_interval_minutes"), 360)) * 60
                last_value = state.get("last_media_sync") or ""
                if last_value:
                    try:
                        last_time = datetime.fromisoformat(last_value).timestamp()
                    except ValueError:
                        last_time = 0
                else:
                    last_time = 0
                if time.time() - last_time < interval:
                    continue
                allowed, _ = can_start_job()
                if allowed and (profile.get("photos_enabled") or profile.get("videos_enabled")):
                    start_job("scheduled-media-sync", profile["id"], run_media_job)
                    break
        except Exception:
            continue


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
    clear_profile_stats(profile_id)
    return jsonify(public_config(load_config()))


@app.get("/api/status")
def api_status():
    return jsonify(status_payload(request.args.get("profile_id")))


@app.get("/api/job")
def api_job():
    with job_lock:
        return jsonify(current_job.to_dict() if current_job else {"status": "idle", "log": []})


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
    try:
        job = start_job("media-sync", profile_id, run_media_job)
        return jsonify(job.to_dict())
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 409


@app.post("/api/sync/notes")
def api_sync_notes():
    payload = request.get_json(force=True, silent=True) or {}
    profile_id = str(payload.get("profile_id") or load_config().get("active_profile_id"))
    try:
        job = start_job("notes-export", profile_id, run_notes_job)
        return jsonify(job.to_dict())
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 409


@app.post("/api/job/input")
def api_job_input():
    payload = request.get_json(force=True, silent=True) or {}
    value = str(payload.get("value") or "")
    with job_lock:
        job = current_job
        process = job.process if job else None
    if not job or not process or not process.stdin or job.status != "running":
        return jsonify({"error": "当前没有可输入的运行中任务"}), 409
    process.stdin.write(value + "\n")
    process.stdin.flush()
    job.waiting_input = False
    job.append("已发送控制台输入")
    return jsonify(job.to_dict())


@app.post("/api/job/stop")
def api_job_stop():
    with job_lock:
        job = current_job
        process = job.process if job else None
    if not job or job.status != "running":
        return jsonify({"error": "当前没有运行中任务"}), 409
    if process and process.poll() is None:
        try:
            process.send_signal(signal.SIGTERM)
        except Exception:
            process.kill()
    finish_job(job, "stopped", return_code=-1)
    return jsonify(job.to_dict())


threading.Thread(target=scheduler_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
