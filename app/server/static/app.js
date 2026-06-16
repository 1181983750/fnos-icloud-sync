const fields = {
  profileName: document.querySelector("#profileName"),
  appleId: document.querySelector("#appleId"),
  profileSubdir: document.querySelector("#profileSubdir"),
  profilePathPreview: document.querySelector("#profilePathPreview"),
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
  recent: document.querySelector("#recent"),
  untilFound: document.querySelector("#untilFound"),
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
  photoCount: document.querySelector("#photoCount"),
  videoCount: document.querySelector("#videoCount"),
  noteCount: document.querySelector("#noteCount"),
  dataPath: document.querySelector("#dataPath"),
  dataPathMeta: document.querySelector("#dataPathMeta"),
  syncRootDisplay: document.querySelector("#syncRootDisplay"),
  syncRootHint: document.querySelector("#syncRootHint"),
  cloudDeleteWarning: document.querySelector("#cloudDeleteWarning"),
  lastSync: document.querySelector("#lastSync"),
  logPanel: document.querySelector(".log-panel"),
  toast: document.querySelector("#toast"),
};

const CLOUD_DELETE_CONFIRM_TEXT = "删除云端";

let appState = {
  config: null,
  activeProfileId: "",
  status: null,
  selectedGuideStep: "",
};
let toastTimer = null;

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
    status?.storage?.applied_root_path ||
    status?.storage?.selected_root_path ||
    status?.storage?.container_root ||
    "";
  const preview = joinDisplayPath(root, currentProfileSubdir());
  fields.profilePathPreview.value = preview;
  return preview;
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

function confirmCloudDelete(actionLabel) {
  const value = window.prompt(
    `${actionLabel}会在同步成功后删除 iCloud 云端对应照片/视频。\n\n` +
      `请先确认 NAS 已有完整备份。若继续，请输入：${CLOUD_DELETE_CONFIRM_TEXT}`
  );
  return value === CLOUD_DELETE_CONFIRM_TEXT;
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
  const profiles = appState.config?.profiles || [];
  els.profileList.innerHTML = "";
  profiles.forEach((profile) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `profile-item${profile.id === appState.activeProfileId ? " active" : ""}`;
    button.dataset.profileId = profile.id;

    const title = document.createElement("strong");
    title.textContent = profile.name || "未命名方案";
    const account = document.createElement("span");
    account.textContent = profile.apple_id || "未填写 Apple ID";
    const flags = document.createElement("small");
    const enabled = [];
    if (profile.photos_enabled) enabled.push("照片");
    if (profile.videos_enabled) enabled.push("视频");
    if (profile.notes_enabled) enabled.push("备忘录");
    const folder = cleanRelativePath(profile.data_subdir) || "根目录";
    flags.textContent = `${enabled.length ? enabled.join(" / ") : "未选择同步内容"} · ${folder}`;

    button.append(title, account, flags);
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
  updateProfilePathPreview();
  fields.authPassword.value = "";
  fields.storePassword.checked = Boolean(profile.store_password);
  fields.photosEnabled.checked = Boolean(profile.photos_enabled);
  fields.videosEnabled.checked = Boolean(profile.videos_enabled);
  fields.notesEnabled.checked = Boolean(profile.notes_enabled);
  fields.scheduleEnabled.checked = Boolean(profile.schedule_enabled);
  fields.syncInterval.value = profile.sync_interval_minutes || 360;
  fields.domain.value = profile.domain || "com";
  fields.mediaMode.value = profile.media_mode || "copy";
  fields.folderStructure.value = profile.folder_structure || "{:%Y/%m/%d}";
  fields.size.value = profile.size || "original";
  fields.recent.value = profile.recent || "";
  fields.untilFound.value = profile.until_found || "";
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
  els.deleteProfileBtn.disabled = (appState.config?.profiles || []).length <= 1;
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
    recent: fields.recent.value.trim(),
    until_found: fields.untilFound.value.trim(),
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

function setRunning(isRunning) {
  els.authBtn.disabled = isRunning;
  els.mediaSyncBtn.disabled = isRunning;
  els.notesSyncBtn.disabled = isRunning;
  els.stopJob.disabled = !isRunning;
}

function renderJob(job) {
  const status = job?.status || "idle";
  const labels = {
    idle: "空闲",
    running: "运行中",
    success: "完成",
    failed: "失败",
    stopped: "已停止",
  };
  const profileName = job?.profile_name ? ` · ${job.profile_name}` : "";
  els.jobStatus.textContent = `${labels[status] || status}${profileName}`;
  els.jobStatus.className = "pill";
  if (status === "failed" || status === "stopped") {
    els.jobStatus.classList.add("error");
  } else if (status === "running") {
    els.jobStatus.classList.add("warn");
  }
  setRunning(status === "running");

  if (Array.isArray(job?.log) && job.log.length) {
    els.logOutput.textContent = job.log.join("\n");
    els.logOutput.scrollTop = els.logOutput.scrollHeight;
  }
}

function renderStatus(status) {
  appState.status = status;
  els.photoCount.textContent = status.counts?.photos ?? 0;
  els.videoCount.textContent = status.counts?.videos ?? 0;
  els.noteCount.textContent = status.counts?.notes ?? 0;

  const selectedRoot = status.storage?.selected_root_path || status.paths?.data || "-";
  const appliedRoot = status.storage?.applied_root_path || selectedRoot;
  const authorizedCount = status.storage?.authorized_paths?.length ?? 0;
  const restartRequired = Boolean(status.storage?.restart_required);
  const rootMode = status.storage?.using_default_root ? "当前目标为应用共享目录" : "当前目标为飞牛已授权目录";
  let rootHint = status.storage?.using_default_root
    ? "如需切到任意目录，请到飞牛的应用设置里为本应用授权目录并选择。"
    : `已检测到 ${authorizedCount} 个授权目录，可在飞牛应用设置里切换。`;

  if (restartRequired) {
    rootHint = `已选择新目录，但当前容器仍挂载在 ${appliedRoot}。请重启应用后生效。`;
  }

  const profilePath = updateProfilePathPreview(status);
  els.dataPath.textContent = profilePath;
  els.dataPathMeta.textContent = `${rootMode} · 应用根目录 ${appliedRoot} · 容器内当前目录 ${status.paths?.data || "-"}`;
  els.syncRootDisplay.value = selectedRoot;
  els.syncRootHint.textContent = rootHint;

  const lastMedia = status.state?.last_media_sync || "从未同步媒体";
  const lastNotes = status.state?.last_notes_sync || "从未导出备忘录";
  els.lastSync.textContent = `媒体: ${lastMedia} / 备忘录: ${lastNotes}`;
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
  }
}

async function saveCurrentProfile(includePasswords = true, options = {}) {
  const payload = collectConfig(includePasswords);
  const previousMode = activeProfile()?.media_mode || "copy";
  if (
    isCloudDeleteMode(payload.media_mode) &&
    previousMode !== "move" &&
    !options.skipCloudDeleteConfirm &&
    !confirmCloudDelete("保存云端删除模式")
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
  const profile = activeProfile();
  if (!profile) {
    return;
  }
  const confirmed = window.confirm(`删除方案“${profile.name}”？同步文件默认保留。`);
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
  fields.imapUser,
  fields.imapPassword,
].forEach((field) => {
  const eventName = field.type === "checkbox" || field.tagName === "SELECT" ? "change" : "input";
  field.addEventListener(eventName, () => {
    releaseGuideStep();
    if (field === fields.profileSubdir) {
      updateProfilePathPreview();
    }
    updateGuide();
  });
});

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
    releaseGuideStep();
    const nextConfig = collectConfig(true);
    if (isCloudDeleteMode(nextConfig.media_mode) && !confirmCloudDelete("开始媒体同步")) {
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
      body: JSON.stringify({ value }),
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
    const job = await api("/api/job/stop", { method: "POST", body: "{}" });
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
