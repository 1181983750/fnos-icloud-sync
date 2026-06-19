const fields = {
  profileName: document.querySelector("#profileName"),
  appleId: document.querySelector("#appleId"),
  profileSubdir: document.querySelector("#profileSubdir"),
  authPassword: document.querySelector("#authPassword"),
  storePassword: document.querySelector("#storePassword"),
  photosEnabled: document.querySelector("#photosEnabled"),
  videosEnabled: document.querySelector("#videosEnabled"),
  notesEnabled: document.querySelector("#notesEnabled"),
  scheduleEnabled: document.querySelector("#scheduleEnabled"),
  syncInterval: document.querySelector("#syncInterval"),
  domain: document.querySelector("#domain"),
  mediaMode: document.querySelector("#mediaMode"),
  folderStructure: document.querySelector("#folderStructure"),
  size: document.querySelector("#size"),
  livePhotoSize: document.querySelector("#livePhotoSize"),
  forceSize: document.querySelector("#forceSize"),
  alignRaw: document.querySelector("#alignRaw"),
  fileMatchPolicy: document.querySelector("#fileMatchPolicy"),
  recent: document.querySelector("#recent"),
  untilFound: document.querySelector("#untilFound"),
  retryAttempts: document.querySelector("#retryAttempts"),
  retryDelay: document.querySelector("#retryDelay"),
  album: document.querySelector("#album"),
  library: document.querySelector("#library"),
  includeLivePhotos: document.querySelector("#includeLivePhotos"),
  keepUnicode: document.querySelector("#keepUnicode"),
  setExifDatetime: document.querySelector("#setExifDatetime"),
  imapUser: document.querySelector("#imapUser"),
  imapPassword: document.querySelector("#imapPassword"),
  imapHost: document.querySelector("#imapHost"),
  imapPort: document.querySelector("#imapPort"),
  imapFolder: document.querySelector("#imapFolder"),
  noteFormat: document.querySelector("#noteFormat"),
};

const els = {
  form: document.querySelector("#configForm"),
  addProfileBtn: document.querySelector("#addProfileBtn"),
  deleteProfileBtn: document.querySelector("#deleteProfileBtn"),
  saveProfileBtn: document.querySelector("#configForm button[type='submit']"),
  profileList: document.querySelector("#profileList"),
  activeProfileTitle: document.querySelector("#activeProfileTitle"),
  guideHint: document.querySelector("#guideHint"),
  guideAccount: document.querySelector("#guideAccount"),
  guideAuth: document.querySelector("#guideAuth"),
  guideScope: document.querySelector("#guideScope"),
  guideRun: document.querySelector("#guideRun"),
  accountSection: document.querySelector("#accountSection"),
  scopeSection: document.querySelector("#scopeSection"),
  taskSection: document.querySelector("#taskSection"),
  notesSection: document.querySelector("#notesSection"),
  authBtn: document.querySelector("#authBtn"),
  mediaSyncBtn: document.querySelector("#mediaSyncBtn"),
  notesSyncBtn: document.querySelector("#notesSyncBtn"),
  stopJob: document.querySelector("#stopJob"),
  sendInputBtn: document.querySelector("#sendInputBtn"),
  consoleInput: document.querySelector("#consoleInput"),
  logSendInputBtn: document.querySelector("#logSendInputBtn"),
  logConsoleInput: document.querySelector("#logConsoleInput"),
  logOutput: document.querySelector("#logOutput"),
  jobStatus: document.querySelector("#jobStatus"),
  schedulerStatus: document.querySelector("#schedulerStatus"),
  scheduleCard: document.querySelector("#scheduleCard"),
  scheduleState: document.querySelector("#scheduleState"),
  scheduleCountdown: document.querySelector("#scheduleCountdown"),
  scheduleLastCheck: document.querySelector("#scheduleLastCheck"),
  scheduleNextRun: document.querySelector("#scheduleNextRun"),
  scheduleCheckCount: document.querySelector("#scheduleCheckCount"),
  scheduleTriggerCount: document.querySelector("#scheduleTriggerCount"),
  scheduleLastMessage: document.querySelector("#scheduleLastMessage"),
  photoCount: document.querySelector("#photoCount"),
  videoCount: document.querySelector("#videoCount"),
  noteCount: document.querySelector("#noteCount"),
  dataPath: document.querySelector("#dataPath"),
  dataPathMeta: document.querySelector("#dataPathMeta"),
  syncRootHint: document.querySelector("#syncRootHint"),
  finalPhotosPath: document.querySelector("#finalPhotosPath"),
  finalVideosPath: document.querySelector("#finalVideosPath"),
  finalNotesPath: document.querySelector("#finalNotesPath"),
  cloudDeleteWarning: document.querySelector("#cloudDeleteWarning"),
  lastSync: document.querySelector("#lastSync"),
  logPanel: document.querySelector(".log-panel"),
  toast: document.querySelector("#toast"),
  modalRoot: document.querySelector("#modalRoot"),
  modalBackdrop: document.querySelector("#modalBackdrop"),
  modalCard: document.querySelector("#modalCard"),
  modalEyebrow: document.querySelector("#modalEyebrow"),
  modalTitle: document.querySelector("#modalTitle"),
  modalBody: document.querySelector("#modalBody"),
  modalDetail: document.querySelector("#modalDetail"),
  modalFieldWrap: document.querySelector("#modalFieldWrap"),
  modalInputLabel: document.querySelector("#modalInputLabel"),
  modalInput: document.querySelector("#modalInput"),
  modalInputHint: document.querySelector("#modalInputHint"),
  modalError: document.querySelector("#modalError"),
  modalCancelBtn: document.querySelector("#modalCancelBtn"),
  modalConfirmBtn: document.querySelector("#modalConfirmBtn"),
};

const CLOUD_DELETE_CONFIRM_TEXT = "删除云端";

let appState = {
  config: null,
  activeProfileId: "",
  status: null,
  selectedGuideStep: "",
  isRunning: false,
  runningJobsCount: 0,
  storageRestartRequired: false,
  logAutoFollow: true,
  logSelectionLocked: false,
  pendingLogText: "",
  lastRenderedLogText: "等待任务...",
  lastJobId: "",
};
let toastTimer = null;
let modalState = {
  isOpen: false,
  resolver: null,
  requiredText: "",
  lastFocused: null,
};

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => els.toast.classList.remove("show"), 2600);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "请求失败");
  }
  return payload;
}

function activeProfile() {
  const profiles = appState.config?.profiles || [];
  return profiles.find((item) => item.id === appState.activeProfileId) || profiles[0] || null;
}

function activeProfileSummary() {
  const profiles = appState.status?.profiles || [];
  return profiles.find((item) => item.id === appState.activeProfileId) || activeProfile();
}

function activeProfileJob() {
  return appState.status?.job || activeProfileSummary()?.job || null;
}

function parseTimestamp(value) {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatTimestamp(value, fallback = "-") {
  const date = parseTimestamp(value);
  if (!date) {
    return fallback;
  }
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatDuration(seconds) {
  const total = Math.max(0, Number(seconds || 0));
  if (total < 60) {
    return `${Math.floor(total)} 秒`;
  }
  const minutes = Math.floor(total / 60);
  const remainingSeconds = Math.floor(total % 60);
  if (minutes < 60) {
    return remainingSeconds ? `${minutes} 分 ${remainingSeconds} 秒` : `${minutes} 分`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes ? `${hours} 小时 ${remainingMinutes} 分` : `${hours} 小时`;
}

function isSchedulerHeartbeatStale(scheduler) {
  if (!scheduler?.schedule_enabled) {
    return false;
  }
  const lastCheck = parseTimestamp(scheduler.last_check);
  return Boolean(lastCheck && Date.now() - lastCheck.getTime() > 150000);
}

function schedulerSummaryText(scheduler, job) {
  if (!scheduler?.schedule_enabled) {
    return "计划同步未启用";
  }
  if (!scheduler.content_enabled) {
    return "计划同步已启用，未选择同步内容";
  }
  if ((job?.kind === "scheduled-media-sync" || job?.kind === "scheduled-notes-export") && job.status === "running") {
    return "计划同步正在运行";
  }
  if (isSchedulerHeartbeatStale(scheduler)) {
    return "调度器超过 2 分钟未检查";
  }
  if (!scheduler.last_check) {
    return "等待调度器首次检查";
  }
  if (scheduler.due) {
    return "已到计划时间，等待触发";
  }
  return "计划同步按周期检查中";
}

function cleanRelativePath(value) {
  return String(value || "")
    .trim()
    .replace(/\\/g, "/")
    .replace(/\/+/g, "/")
    .replace(/^\/+|\/+$/g, "")
    .split("/")
    .map((part) => part.trim())
    .filter((part) => part && part !== "." && part !== "..")
    .join("/");
}

function joinDisplayPath(root, subdir) {
  const base = String(root || "").replace(/[\\/]+$/g, "");
  const relative = cleanRelativePath(subdir);
  if (!base) {
    return relative || "-";
  }
  return relative ? `${base}/${relative}` : base;
}

function currentProfileSubdir() {
  const profile = activeProfile();
  return cleanRelativePath(fields.profileSubdir.value || profile?.data_subdir || "");
}

function updateProfilePathPreview(status = appState.status) {
  const root =
    status?.storage?.selected_root_path ||
    status?.storage?.applied_root_path ||
    status?.storage?.container_root ||
    "";
  return joinDisplayPath(root, currentProfileSubdir());
}

function updateFinalPaths(basePath) {
  els.finalPhotosPath.textContent = joinDisplayPath(basePath, "photos");
  els.finalVideosPath.textContent = joinDisplayPath(basePath, "videos");
  els.finalNotesPath.textContent = joinDisplayPath(basePath, "notes");
}

const guideButtons = {
  account: els.guideAccount,
  auth: els.guideAuth,
  scope: els.guideScope,
  run: els.guideRun,
};

function preferredRunAction() {
  if (fields.photosEnabled.checked || fields.videosEnabled.checked) {
    return els.mediaSyncBtn;
  }
  return els.notesSyncBtn;
}

function isCloudDeleteMode(mode = fields.mediaMode.value) {
  return mode === "move";
}

function updateMediaModeWarning() {
  els.cloudDeleteWarning?.classList.toggle("hidden", !isCloudDeleteMode());
}

function updateModalValidation(showError = false) {
  if (!modalState.requiredText) {
    els.modalConfirmBtn.disabled = false;
    els.modalError.classList.add("hidden");
    return true;
  }

  const matched = els.modalInput.value.trim() === modalState.requiredText;
  els.modalConfirmBtn.disabled = !matched;
  if (matched || !showError) {
    els.modalError.classList.add("hidden");
  } else {
    els.modalError.textContent = `请输入“${modalState.requiredText}”后再继续。`;
    els.modalError.classList.remove("hidden");
  }
  return matched;
}

function closeModal(result = false) {
  if (!modalState.isOpen) {
    return;
  }

  const resolver = modalState.resolver;
  const lastFocused = modalState.lastFocused;
  modalState.isOpen = false;
  modalState.resolver = null;
  modalState.requiredText = "";
  modalState.lastFocused = null;

  els.modalRoot.classList.add("hidden");
  els.modalRoot.classList.remove("danger");
  els.modalRoot.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  els.modalInput.value = "";
  els.modalError.classList.add("hidden");

  if (lastFocused && typeof lastFocused.focus === "function") {
    window.setTimeout(() => lastFocused.focus({ preventScroll: true }), 0);
  }
  if (resolver) {
    resolver(Boolean(result));
  }
}

function openModal(options = {}) {
  if (modalState.isOpen) {
    closeModal(false);
  }

  modalState.isOpen = true;
  modalState.requiredText = String(options.confirmText || "").trim();
  modalState.lastFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;

  els.modalRoot.classList.toggle("danger", options.tone === "danger");
  els.modalRoot.classList.remove("hidden");
  els.modalRoot.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");

  els.modalEyebrow.textContent = options.eyebrow || "";
  els.modalEyebrow.classList.toggle("hidden", !options.eyebrow);
  els.modalTitle.textContent = options.title || "确认操作";
  els.modalBody.textContent = options.body || "";
  els.modalDetail.textContent = options.detail || "";
  els.modalDetail.classList.toggle("hidden", !options.detail);

  els.modalCancelBtn.textContent = options.cancelLabel || "取消";
  els.modalConfirmBtn.textContent = options.confirmLabel || "确认";
  els.modalConfirmBtn.className = options.tone === "danger" ? "primary danger-solid" : "primary";

  const needsInput = Boolean(modalState.requiredText);
  els.modalFieldWrap.classList.toggle("hidden", !needsInput);
  els.modalInputLabel.textContent = options.inputLabel || "确认文字";
  els.modalInputHint.textContent = options.inputHint || "";
  els.modalInputHint.classList.toggle("hidden", !options.inputHint);
  els.modalInput.placeholder = options.inputPlaceholder || (needsInput ? `请输入“${modalState.requiredText}”` : "");
  els.modalInput.value = "";
  els.modalError.classList.add("hidden");

  updateModalValidation(false);

  const focusTarget = needsInput ? els.modalInput : els.modalConfirmBtn;
  window.setTimeout(() => focusTarget.focus({ preventScroll: true }), 20);

  return new Promise((resolve) => {
    modalState.resolver = resolve;
  });
}

async function confirmCloudDelete(actionLabel) {
  return openModal({
    eyebrow: "高风险操作",
    title: `${actionLabel}前请再次确认`,
    body: "本次操作会在同步成功后删除 iCloud 云端对应照片/视频。",
    detail: `请先确认 NAS 已有完整备份。若继续，请输入：${CLOUD_DELETE_CONFIRM_TEXT}`,
    confirmLabel: "继续执行",
    cancelLabel: "暂不继续",
    confirmText: CLOUD_DELETE_CONFIRM_TEXT,
    inputLabel: "确认文字",
    inputHint: "只有输入指定文字后，才会继续执行危险操作。",
    tone: "danger",
  });
}

async function confirmProfileDeletion(profile) {
  return openModal({
    eyebrow: "删除方案",
    title: `删除“${profile.name}”`,
    body: "删除后将移除此方案配置、任务状态和 Cookie。",
    detail: "当前同步文件默认保留，后续可在 NAS 里手动清理。",
    confirmLabel: "删除方案",
    cancelLabel: "保留方案",
    tone: "danger",
  });
}

function handleModalKeydown(event) {
  if (!modalState.isOpen) {
    return;
  }

  if (event.key === "Escape") {
    event.preventDefault();
    closeModal(false);
    return;
  }

  if (event.key !== "Enter") {
    return;
  }

  if (event.target === els.modalCancelBtn) {
    return;
  }

  if (!updateModalValidation(true)) {
    event.preventDefault();
    els.modalInput.focus({ preventScroll: true });
    return;
  }

  event.preventDefault();
  closeModal(true);
}

function guideTargets(step) {
  const targets = {
    account: {
      sections: [els.accountSection],
      focusEl: fields.appleId,
      scrollEl: els.accountSection,
    },
    auth: {
      sections: [els.accountSection, els.taskSection],
      focusEl: fields.authPassword,
      scrollEl: fields.authPassword,
    },
    scope: {
      sections: [els.scopeSection, fields.notesEnabled.checked ? els.notesSection : null],
      focusEl: fields.photosEnabled,
      scrollEl: els.scopeSection,
    },
    run: {
      sections: [els.taskSection, els.logPanel],
      focusEl: preferredRunAction(),
      scrollEl: els.taskSection,
    },
  };
  return targets[step];
}

function clearGuideFocus() {
  document.querySelectorAll(".guide-focus-target").forEach((item) => item.classList.remove("guide-focus-target"));
}

function applyGuideFocus(step, options = {}) {
  const config = guideTargets(step);
  if (!config) {
    return;
  }

  clearGuideFocus();
  config.sections.filter(Boolean).forEach((item) => item.classList.add("guide-focus-target"));

  if (options.scroll && config.scrollEl) {
    config.scrollEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  if (options.focus && config.focusEl) {
    window.setTimeout(() => {
      config.focusEl.focus({ preventScroll: true });
      if ("select" in config.focusEl && typeof config.focusEl.select === "function" && config.focusEl.tagName === "INPUT") {
        config.focusEl.select();
      }
    }, options.scroll ? 240 : 60);
  }
}

function setGuideButtonState(button, state) {
  button.className = "guide-step";
  if (state.done) {
    button.classList.add("done");
  } else if (state.active) {
    button.classList.add("active");
  }
  if (state.current) {
    button.classList.add("current");
    button.setAttribute("aria-current", "step");
  } else {
    button.removeAttribute("aria-current");
  }
}

function guideState() {
  const hasAppleId = Boolean(fields.appleId.value.trim());
  const hasScope = fields.photosEnabled.checked || fields.videosEnabled.checked || fields.notesEnabled.checked;
  const job = appState.status?.job || null;
  const lastMediaSync = appState.status?.state?.last_media_sync || "";
  const lastNotesSync = appState.status?.state?.last_notes_sync || "";
  const hasSyncHistory = Boolean(lastMediaSync || lastNotesSync);
  const authDone = Boolean((job?.kind === "auth" && job?.status === "success") || hasSyncHistory);
  const runDone = Boolean(
    (job?.kind && job.kind !== "auth" && (job.status === "running" || job.status === "success")) || hasSyncHistory
  );

  let recommendedStep = "account";
  if (hasAppleId && !authDone) {
    recommendedStep = "auth";
  } else if (hasAppleId && authDone && !hasScope) {
    recommendedStep = "scope";
  } else if (hasAppleId && hasScope) {
    recommendedStep = "run";
  }

  return {
    hasAppleId,
    hasScope,
    authDone,
    runDone,
    recommendedStep,
  };
}

function guideHintText(step) {
  const hints = {
    account: "先填写 Apple ID 和认证密码，保存后就可以开始认证。",
    auth: "点“认证 iCloud”后，如果 Apple 要求验证码，在右侧输入框里直接发送。",
    scope: "勾选这次要同步的内容，再决定目录结构、照片尺寸和是否计划同步。",
    run: "认证完成后，点右侧按钮开始同步；下面日志会实时显示进度。",
  };
  return hints[step] || "按顺序完成 Apple ID、认证、同步内容和任务启动。";
}

function renderProfiles() {
  const profileStatus = new Map((appState.status?.profiles || []).map((item) => [item.id, item]));
  const profiles = appState.config?.profiles || [];
  els.profileList.innerHTML = "";
  profiles.forEach((profile) => {
    const summary = profileStatus.get(profile.id) || profile;
    const job = summary.job || null;
    const button = document.createElement("button");
    button.type = "button";
    button.className = `profile-item${profile.id === appState.activeProfileId ? " active" : ""}${job?.status === "running" ? " running" : ""}`;
    button.dataset.profileId = profile.id;

    const title = document.createElement("strong");
    title.textContent = summary.name || "未命名方案";
    const account = document.createElement("span");
    account.textContent = summary.apple_id || "未填写 Apple ID";
    const flags = document.createElement("small");
    const enabled = [];
    if (summary.photos_enabled) enabled.push("照片");
    if (summary.videos_enabled) enabled.push("视频");
    if (summary.notes_enabled) enabled.push("备忘录");
    const folder = cleanRelativePath(summary.data_subdir) || "根目录";
    flags.textContent = `${enabled.length ? enabled.join(" / ") : "未选择同步内容"} · ${folder}`;

    button.append(title, account, flags);
    if (job?.status === "running" || job?.waiting_input) {
      const kindLabels = {
        auth: "认证",
        "media-sync": "媒体同步",
        "scheduled-media-sync": "计划同步",
        "notes-export": "备忘录导出",
        "scheduled-notes-export": "计划备忘录",
      };
      const jobLine = document.createElement("small");
      jobLine.textContent = job.waiting_input
        ? `等待输入 · ${kindLabels[job.kind] || job.kind}`
        : `运行中 · ${kindLabels[job.kind] || job.kind}`;
      button.append(jobLine);
    }
    button.addEventListener("click", () => selectProfile(profile.id));
    els.profileList.append(button);
  });
}

function applyProfile(profile) {
  if (!profile) {
    return;
  }
  fields.profileName.value = profile.name || "";
  fields.appleId.value = profile.apple_id || "";
  fields.profileSubdir.value = profile.data_subdir || "";
  updateFinalPaths(updateProfilePathPreview());
  fields.authPassword.value = "";
  fields.storePassword.checked = Boolean(profile.store_password);
  fields.photosEnabled.checked = Boolean(profile.photos_enabled);
  fields.videosEnabled.checked = Boolean(profile.videos_enabled);
  fields.notesEnabled.checked = Boolean(profile.notes_enabled);
  fields.scheduleEnabled.checked = Boolean(profile.schedule_enabled);
  fields.syncInterval.value = profile.sync_interval_minutes || 360;
  fields.domain.value = profile.domain || "cn";
  fields.mediaMode.value = profile.media_mode || "copy";
  fields.folderStructure.value = profile.folder_structure || "{:%Y/%m/%d}";
  fields.size.value = profile.size || "original";
  fields.livePhotoSize.value = profile.live_photo_size || "";
  fields.forceSize.checked = Boolean(profile.force_size);
  fields.alignRaw.value = profile.align_raw || "";
  fields.fileMatchPolicy.value = profile.file_match_policy || "";
  fields.recent.value = profile.recent || "";
  fields.untilFound.value = profile.until_found || "";
  fields.retryAttempts.value = profile.retry_attempts ?? 3;
  fields.retryDelay.value = profile.retry_delay_seconds ?? 60;
  fields.album.value = profile.album || "";
  fields.library.value = profile.library || "";
  fields.includeLivePhotos.checked = Boolean(profile.include_live_photos);
  fields.keepUnicode.checked = Boolean(profile.keep_unicode);
  fields.setExifDatetime.checked = Boolean(profile.set_exif_datetime);

  const notes = profile.notes || {};
  fields.imapUser.value = notes.username || "";
  fields.imapPassword.value = "";
  fields.imapHost.value = notes.host || "imap.mail.me.com";
  fields.imapPort.value = notes.port || 993;
  fields.imapFolder.value = notes.folder || "Notes";
  fields.noteFormat.value = notes.format || "markdown";

  els.activeProfileTitle.textContent = profile.name || "当前方案";
  els.deleteProfileBtn.disabled = isJobRunning() || (appState.config?.profiles || []).length <= 1;
  updateMediaModeWarning();
  updateGuide();
}

function collectConfig(includePasswords = false) {
  const payload = {
    profile_id: appState.activeProfileId,
    name: fields.profileName.value.trim() || "未命名方案",
    data_subdir: cleanRelativePath(fields.profileSubdir.value),
    apple_id: fields.appleId.value.trim(),
    store_password: fields.storePassword.checked,
    photos_enabled: fields.photosEnabled.checked,
    videos_enabled: fields.videosEnabled.checked,
    notes_enabled: fields.notesEnabled.checked,
    schedule_enabled: fields.scheduleEnabled.checked,
    sync_interval_minutes: fields.syncInterval.value,
    domain: fields.domain.value,
    media_mode: fields.mediaMode.value,
    folder_structure: fields.folderStructure.value.trim(),
    size: fields.size.value,
    live_photo_size: fields.livePhotoSize.value,
    force_size: fields.forceSize.checked,
    align_raw: fields.alignRaw.value,
    file_match_policy: fields.fileMatchPolicy.value,
    recent: fields.recent.value.trim(),
    until_found: fields.untilFound.value.trim(),
    retry_attempts: fields.retryAttempts.value.trim(),
    retry_delay_seconds: fields.retryDelay.value.trim(),
    album: fields.album.value.trim(),
    library: fields.library.value.trim(),
    include_live_photos: fields.includeLivePhotos.checked,
    keep_unicode: fields.keepUnicode.checked,
    set_exif_datetime: fields.setExifDatetime.checked,
    notes: {
      username: fields.imapUser.value.trim(),
      host: fields.imapHost.value.trim(),
      port: fields.imapPort.value.trim(),
      folder: fields.imapFolder.value.trim(),
      format: fields.noteFormat.value,
    },
  };

  if (includePasswords) {
    if (fields.authPassword.value) {
      payload.password = fields.authPassword.value;
    }
    if (fields.imapPassword.value) {
      payload.notes.password = fields.imapPassword.value;
    }
  }
  return payload;
}

function isJobRunning() {
  return activeProfileJob()?.status === "running";
}

function isStorageRestartRequired() {
  return Boolean(appState.storageRestartRequired);
}

function showStorageRestartToast() {
  showToast("同步根目录还没有生效，请在应用中心停止后重新启动本应用");
}

function isSelectionInsideLog() {
  const selection = window.getSelection?.();
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
    return false;
  }
  return els.logOutput.contains(selection.anchorNode) || els.logOutput.contains(selection.focusNode);
}

function isLogNearBottom() {
  const distance = els.logOutput.scrollHeight - els.logOutput.scrollTop - els.logOutput.clientHeight;
  return distance < 24;
}

function shouldFreezeLogUpdates() {
  return appState.logSelectionLocked;
}

function applyLogText(text, shouldFollow = false) {
  if (text === appState.lastRenderedLogText) {
    return;
  }
  els.logOutput.textContent = text;
  appState.lastRenderedLogText = text;
  if (shouldFollow) {
    els.logOutput.scrollTop = els.logOutput.scrollHeight;
  }
}

function flushPendingLogText() {
  if (shouldFreezeLogUpdates() || !appState.pendingLogText) {
    return;
  }
  const text = appState.pendingLogText;
  appState.pendingLogText = "";
  applyLogText(text, false);
}

function setRunning(isRunning) {
  appState.isRunning = isRunning;
  const storageRestartRequired = isStorageRestartRequired();
  Object.values(fields)
    .filter(Boolean)
    .forEach((field) => {
      field.disabled = isRunning;
    });
  els.form.classList.toggle("config-locked", isRunning);
  els.addProfileBtn.disabled = false;
  els.saveProfileBtn.disabled = isRunning;
  els.deleteProfileBtn.disabled = isRunning || (appState.config?.profiles || []).length <= 1;
  els.authBtn.disabled = isRunning;
  els.mediaSyncBtn.disabled = isRunning || storageRestartRequired;
  els.notesSyncBtn.disabled = isRunning || storageRestartRequired;
  els.stopJob.disabled = !isRunning;
}

function renderJob(job) {
  const status = job?.status || "idle";
  const jobId = job?.id || "";
  if (jobId && jobId !== appState.lastJobId) {
    appState.logAutoFollow = true;
    appState.lastJobId = jobId;
  }
  const labels = {
    idle: "空闲",
    running: "运行中",
    success: "完成",
    failed: "失败",
    stopped: "已停止",
  };
  const profileName = job?.profile_name ? ` · ${job.profile_name}` : "";
  const otherRunningCount = Math.max(0, (appState.runningJobsCount || 0) - (status === "running" ? 1 : 0));
  const waitingInputText = job?.waiting_input ? " · 等待控制台输入" : "";
  const otherJobsText = otherRunningCount > 0 ? ` · 另有 ${otherRunningCount} 个方案运行中` : "";
  els.jobStatus.textContent = `${labels[status] || status}${profileName}${waitingInputText}${otherJobsText}`;
  els.jobStatus.className = "pill";
  if (status === "failed" || status === "stopped") {
    els.jobStatus.classList.add("error");
  } else if (status === "running") {
    els.jobStatus.classList.add("warn");
  }
  setRunning(status === "running");

  let nextLogText = "等待任务...";
  let shouldFollow = false;
  if (Array.isArray(job?.log) && job.log.length) {
    nextLogText = job.log.join("\n");
    shouldFollow = appState.logAutoFollow || isLogNearBottom();
  } else if (otherRunningCount > 0) {
    nextLogText = "当前方案暂无任务日志；可切换左侧运行中的方案查看对应进度。";
  }

  if (shouldFreezeLogUpdates()) {
    appState.pendingLogText = nextLogText;
  } else {
    appState.pendingLogText = "";
    applyLogText(nextLogText, shouldFollow);
  }
}

function renderSchedule(status) {
  const scheduler = status.scheduler || {};
  const job = status.job || activeProfileSummary()?.job || null;
  const isConfigured = Boolean(scheduler.schedule_enabled);
  const isRunning = (job?.kind === "scheduled-media-sync" || job?.kind === "scheduled-notes-export") && job.status === "running";
  const isStale = isSchedulerHeartbeatStale(scheduler);
  const summary = schedulerSummaryText(scheduler, job);

  els.schedulerStatus.textContent = isConfigured
    ? `${summary}${scheduler.last_check ? ` · ${formatTimestamp(scheduler.last_check)}` : ""}`
    : summary;
  els.schedulerStatus.className = "pill neutral";
  if (isRunning || (isConfigured && !isStale)) {
    els.schedulerStatus.classList.remove("neutral");
  }
  if (isStale || scheduler.last_status === "blocked" || scheduler.last_status === "failed") {
    els.schedulerStatus.classList.add("warn");
  }

  els.scheduleCard.className = "schedule-card";
  if (isConfigured) {
    els.scheduleCard.classList.add("active");
  }
  if (isRunning) {
    els.scheduleCard.classList.add("running");
  }
  if (isStale || scheduler.last_status === "blocked" || scheduler.last_status === "failed") {
    els.scheduleCard.classList.add("warn");
  }

  els.scheduleState.textContent = summary;
  if (!scheduler.active) {
    els.scheduleCountdown.textContent = "-";
  } else if (isRunning) {
    els.scheduleCountdown.textContent = "正在运行";
  } else if (scheduler.due) {
    els.scheduleCountdown.textContent = "已到时间";
  } else {
    els.scheduleCountdown.textContent = `${formatDuration(scheduler.seconds_until_next)} 后`;
  }
  els.scheduleLastCheck.textContent = formatTimestamp(scheduler.last_check, "等待检查");
  els.scheduleNextRun.textContent = scheduler.active ? formatTimestamp(scheduler.next_run, "-") : "-";
  els.scheduleCheckCount.textContent = `${scheduler.check_count || 0} 次`;
  els.scheduleTriggerCount.textContent = `${scheduler.trigger_count || 0} 次`;
  els.scheduleLastMessage.textContent = scheduler.last_message || "-";
}

function renderStatus(status) {
  appState.status = status;
  appState.runningJobsCount = status.running_jobs_count || 0;
  els.photoCount.textContent = status.counts?.photos ?? 0;
  els.videoCount.textContent = status.counts?.videos ?? 0;
  els.noteCount.textContent = status.counts?.notes ?? 0;

  const selectedRoot = status.storage?.selected_root_path || status.paths?.data || "-";
  const restartRequired = Boolean(status.storage?.restart_required);
  appState.storageRestartRequired = restartRequired;
  const profilePath = updateProfilePathPreview(status);
  const statusPrefix = restartRequired
    ? `已选择 ${selectedRoot}，但本次启动仍在使用旧位置；请在应用中心停止后重新启动本应用，资料才会保存到上方目录。`
    : `资料会保存到上方目录。`;

  updateFinalPaths(profilePath);
  els.dataPath.textContent = profilePath;
  els.dataPathMeta.textContent = restartRequired ? `重启应用后生效，当前仍使用旧位置` : "照片 / 视频 / 备忘录会分目录保存";
  els.syncRootHint.textContent = `${statusPrefix} 照片在 photos，视频在 videos，备忘录在 notes。`;

  const lastMedia = status.state?.last_media_sync || "从未同步媒体";
  const lastNotes = status.state?.last_notes_sync || "从未导出备忘录";
  els.lastSync.textContent = `媒体: ${lastMedia} / 备忘录: ${lastNotes}`;
  renderProfiles();
  renderSchedule(status);
  renderJob(status.job || { status: "idle", log: [] });
  updateGuide();
}

function updateGuide(options = {}) {
  const state = guideState();
  const currentStep = options.step || appState.selectedGuideStep || state.recommendedStep;

  setGuideButtonState(guideButtons.account, {
    done: state.hasAppleId,
    active: !state.hasAppleId,
    current: currentStep === "account",
  });
  setGuideButtonState(guideButtons.auth, {
    done: state.authDone,
    active: state.recommendedStep === "auth",
    current: currentStep === "auth",
  });
  setGuideButtonState(guideButtons.scope, {
    done: state.hasScope,
    active: state.recommendedStep === "scope",
    current: currentStep === "scope",
  });
  setGuideButtonState(guideButtons.run, {
    done: state.runDone,
    active: state.recommendedStep === "run",
    current: currentStep === "run",
  });

  els.guideHint.textContent = guideHintText(currentStep);
  applyGuideFocus(currentStep, {
    scroll: Boolean(options.scroll),
    focus: Boolean(options.focus),
  });
}

async function loadConfig() {
  const config = await api("/api/config");
  appState.config = config;
  appState.activeProfileId = config.active_profile_id;
  renderProfiles();
  applyProfile(activeProfile());
}

async function refreshStatus() {
  try {
    const profileId = appState.activeProfileId ? `?profile_id=${encodeURIComponent(appState.activeProfileId)}` : "";
    const status = await api(`/api/status${profileId}`);
    renderStatus(status);
  } catch (error) {
    els.jobStatus.textContent = "服务未连接";
    els.jobStatus.className = "pill error";
    els.schedulerStatus.textContent = "调度器未连接";
    els.schedulerStatus.className = "pill error";
    setRunning(false);
  }
}

async function saveCurrentProfile(includePasswords = true, options = {}) {
  const payload = collectConfig(includePasswords);
  const previousMode = activeProfile()?.media_mode || "copy";
  if (
    isCloudDeleteMode(payload.media_mode) &&
    previousMode !== "move" &&
    !options.skipCloudDeleteConfirm &&
    !(await confirmCloudDelete("保存云端删除模式"))
  ) {
    showToast("已取消保存");
    return null;
  }
  const config = await api("/api/config", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  appState.config = config;
  appState.activeProfileId = config.active_profile_id;
  renderProfiles();
  applyProfile(activeProfile());
  return config;
}

async function selectProfile(profileId) {
  try {
    releaseGuideStep();
    const config = await api(`/api/profiles/${encodeURIComponent(profileId)}/select`, {
      method: "POST",
      body: "{}",
    });
    appState.config = config;
    appState.activeProfileId = config.active_profile_id;
    els.logOutput.textContent = "等待任务...";
    renderProfiles();
    applyProfile(activeProfile());
    await refreshStatus();
    updateGuide({ focus: true });
  } catch (error) {
    showToast(error.message);
  }
}

function selectGuideStep(step, options = {}) {
  appState.selectedGuideStep = step;
  updateGuide(options);
}

function releaseGuideStep() {
  appState.selectedGuideStep = "";
}

els.addProfileBtn.addEventListener("click", async () => {
  try {
    releaseGuideStep();
    const config = await api("/api/profiles", {
      method: "POST",
      body: JSON.stringify({}),
    });
    appState.config = config;
    appState.activeProfileId = config.active_profile_id;
    els.logOutput.textContent = "新方案已创建，请填写 Apple ID 并保存。";
    renderProfiles();
    applyProfile(activeProfile());
    await refreshStatus();
    updateGuide({ focus: true });
    showToast("已新增方案");
  } catch (error) {
    showToast(error.message);
  }
});

els.deleteProfileBtn.addEventListener("click", async () => {
  if (isJobRunning()) {
    showToast("任务运行中，暂不能删除方案");
    return;
  }
  const profile = activeProfile();
  if (!profile) {
    return;
  }
  const confirmed = await confirmProfileDeletion(profile);
  if (!confirmed) {
    return;
  }
  try {
    releaseGuideStep();
    const config = await api(`/api/profiles/${encodeURIComponent(profile.id)}`, {
      method: "DELETE",
      body: JSON.stringify({ delete_data: false }),
    });
    appState.config = config;
    appState.activeProfileId = config.active_profile_id;
    els.logOutput.textContent = "等待任务...";
    renderProfiles();
    applyProfile(activeProfile());
    await refreshStatus();
    updateGuide({ focus: true });
    showToast("方案已删除");
  } catch (error) {
    showToast(error.message);
  }
});

els.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isJobRunning()) {
    showToast("任务运行中，配置已锁定");
    return;
  }
  try {
    releaseGuideStep();
    const config = await saveCurrentProfile(true);
    if (!config) {
      return;
    }
    fields.authPassword.value = "";
    fields.imapPassword.value = "";
    showToast("方案已保存");
    await refreshStatus();
  } catch (error) {
    showToast(error.message);
  }
});

[
  fields.profileName,
  fields.appleId,
  fields.profileSubdir,
  fields.photosEnabled,
  fields.videosEnabled,
  fields.notesEnabled,
  fields.authPassword,
  fields.storePassword,
  fields.domain,
  fields.mediaMode,
  fields.scheduleEnabled,
  fields.syncInterval,
  fields.retryAttempts,
  fields.retryDelay,
  fields.imapUser,
  fields.imapPassword,
].forEach((field) => {
  const eventName = field.type === "checkbox" || field.tagName === "SELECT" ? "change" : "input";
  field.addEventListener(eventName, () => {
    releaseGuideStep();
      if (field === fields.profileSubdir) {
        updateFinalPaths(updateProfilePathPreview());
      }
    updateGuide();
  });
});

els.logOutput.addEventListener("scroll", () => {
  appState.logAutoFollow = isLogNearBottom();
});

document.addEventListener("selectionchange", () => {
  const wasLocked = appState.logSelectionLocked;
  appState.logSelectionLocked = isSelectionInsideLog();
  if (wasLocked && !appState.logSelectionLocked) {
    flushPendingLogText();
  }
});

els.modalBackdrop.addEventListener("click", () => closeModal(false));
els.modalCancelBtn.addEventListener("click", () => closeModal(false));
els.modalConfirmBtn.addEventListener("click", () => {
  if (!updateModalValidation(true)) {
    els.modalInput.focus({ preventScroll: true });
    return;
  }
  closeModal(true);
});
els.modalInput.addEventListener("input", () => updateModalValidation(false));
document.addEventListener("keydown", handleModalKeydown);

Object.entries(guideButtons).forEach(([step, button]) => {
  button.addEventListener("click", () => selectGuideStep(step, { step, scroll: true, focus: true }));
});

els.authBtn.addEventListener("click", async () => {
  try {
    releaseGuideStep();
    const config = await saveCurrentProfile(true);
    if (!config) {
      return;
    }
    const job = await api("/api/auth", {
      method: "POST",
      body: JSON.stringify({
        profile_id: appState.activeProfileId,
        apple_id: fields.appleId.value.trim(),
        password: fields.authPassword.value,
        store_password: fields.storePassword.checked,
      }),
    });
    fields.authPassword.value = "";
    renderJob(job);
    showToast("认证任务已开始");
  } catch (error) {
    showToast(error.message);
  }
});

els.mediaSyncBtn.addEventListener("click", async () => {
  try {
    if (isStorageRestartRequired()) {
      showStorageRestartToast();
      return;
    }
    releaseGuideStep();
    const nextConfig = collectConfig(true);
    if (isCloudDeleteMode(nextConfig.media_mode) && !(await confirmCloudDelete("开始媒体同步"))) {
      showToast("已取消同步");
      return;
    }
    const config = await saveCurrentProfile(true, { skipCloudDeleteConfirm: true });
    if (!config) {
      return;
    }
    fields.authPassword.value = "";
    const job = await api("/api/sync/media", {
      method: "POST",
      body: JSON.stringify({ profile_id: appState.activeProfileId }),
    });
    renderJob(job);
    showToast("同步任务已开始");
  } catch (error) {
    showToast(error.message);
  }
});

fields.mediaMode.addEventListener("change", updateMediaModeWarning);

els.notesSyncBtn.addEventListener("click", async () => {
  try {
    if (isStorageRestartRequired()) {
      showStorageRestartToast();
      return;
    }
    releaseGuideStep();
    const config = await saveCurrentProfile(true);
    if (!config) {
      return;
    }
    fields.imapPassword.value = "";
    const job = await api("/api/sync/notes", {
      method: "POST",
      body: JSON.stringify({ profile_id: appState.activeProfileId }),
    });
    renderJob(job);
    showToast("备忘录导出已开始");
  } catch (error) {
    showToast(error.message);
  }
});

async function sendConsoleInput(inputEl) {
  const value = inputEl.value.trim();
  if (!value) {
    return;
  }
  try {
    const job = await api("/api/job/input", {
      method: "POST",
      body: JSON.stringify({ profile_id: appState.activeProfileId, value }),
    });
    if (els.consoleInput) {
      els.consoleInput.value = "";
    }
    if (els.logConsoleInput) {
      els.logConsoleInput.value = "";
    }
    renderJob(job);
  } catch (error) {
    showToast(error.message);
  }
}

els.sendInputBtn.addEventListener("click", async () => {
  await sendConsoleInput(els.consoleInput);
});

els.logSendInputBtn.addEventListener("click", async () => {
  await sendConsoleInput(els.logConsoleInput);
});

els.consoleInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    els.sendInputBtn.click();
  }
});

els.logConsoleInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    els.logSendInputBtn.click();
  }
});

els.stopJob.addEventListener("click", async () => {
  try {
    const job = await api("/api/job/stop", {
      method: "POST",
      body: JSON.stringify({ profile_id: appState.activeProfileId }),
    });
    renderJob(job);
    showToast("任务已停止");
  } catch (error) {
    showToast(error.message);
  }
});

loadConfig()
  .then(refreshStatus)
  .then(() => updateGuide({ focus: true }))
  .catch((error) => showToast(error.message));

setInterval(refreshStatus, 3000);
