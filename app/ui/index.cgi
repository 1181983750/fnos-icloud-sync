#!/bin/bash

APP_NAME="${TRIM_APPNAME:-icloud-sync}"
PKGVAR="${TRIM_PKGVAR:-/var/apps/${APP_NAME}/var}"
SERVICE_PORT="${TRIM_SERVICE_PORT:-8080}"
LOG_DIR="${PKGVAR}/logs"
RUN_DIR="${PKGVAR}/run"
SERVICE_LOG="${LOG_DIR}/service.log"
CONFIG_INIT_LOG="${LOG_DIR}/config_init.log"
CONFIG_CALLBACK_LOG="${LOG_DIR}/config_callback.log"
PID_FILE="${RUN_DIR}/icloud-sync.pid"

cat <<HTML
Content-Type: text/html; charset=utf-8

<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>iCloud 同步</title>
    <style>
      :root {
        color-scheme: light;
        --ink: #13211c;
        --muted: #668072;
        --glow: #58d7b0;
        --cyan: #7bd7ff;
        --gold: #ffe59a;
        --rose: #ffaec8;
        --panel: rgba(250, 255, 252, 0.72);
        --line: rgba(37, 80, 63, 0.14);
        --shadow: rgba(20, 55, 42, 0.18);
      }

      * {
        box-sizing: border-box;
      }

      body {
        min-height: 100vh;
        margin: 0;
        overflow: hidden;
        color: var(--ink);
        font-family: "HarmonyOS Sans SC", "MiSans", "Microsoft YaHei", "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at 20% 18%, rgba(123, 215, 255, 0.36), transparent 30vw),
          radial-gradient(circle at 82% 12%, rgba(255, 229, 154, 0.42), transparent 28vw),
          linear-gradient(145deg, #f7fbf8 0%, #dbeae4 46%, #b5d7d5 100%);
      }

      body::before,
      body::after {
        content: "";
        position: fixed;
        inset: -20%;
        pointer-events: none;
      }

      body::before {
        background:
          linear-gradient(110deg, transparent 30%, rgba(255, 255, 255, 0.56) 45%, transparent 62%),
          repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.12) 0 1px, transparent 1px 84px);
        mix-blend-mode: screen;
        transform: translateX(-24%);
        animation: lightSweep 7s ease-in-out infinite;
      }

      body::after {
        background:
          radial-gradient(circle at 50% 50%, transparent 0 46%, rgba(19, 33, 28, 0.08) 100%),
          linear-gradient(rgba(255, 255, 255, 0.2) 1px, transparent 1px);
        background-size: auto, auto 8px;
      }

      .stage {
        position: relative;
        z-index: 1;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 34px;
      }

      .orb {
        position: absolute;
        width: 36vw;
        height: 36vw;
        min-width: 320px;
        min-height: 320px;
        border-radius: 999px;
        filter: blur(18px);
        opacity: 0.55;
        animation: floatOrb 11s ease-in-out infinite;
      }

      .orb.one {
        left: -10vw;
        bottom: -14vw;
        background: radial-gradient(circle, rgba(88, 215, 176, 0.58), transparent 68%);
      }

      .orb.two {
        right: -12vw;
        top: -12vw;
        background: radial-gradient(circle, rgba(255, 174, 200, 0.52), transparent 66%);
        animation-delay: -5s;
      }

      .panel {
        position: relative;
        width: min(1060px, 100%);
        min-height: 610px;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 34px;
        background: var(--panel);
        box-shadow: 0 34px 100px var(--shadow);
        backdrop-filter: blur(24px) saturate(1.22);
      }

      .panel::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
          linear-gradient(120deg, rgba(255, 255, 255, 0.62), transparent 28%),
          radial-gradient(circle at 78% 28%, rgba(255, 255, 255, 0.8), transparent 10%),
          linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.34), transparent);
        transform: translateX(-58%);
        animation: panelShine 5.2s ease-in-out infinite;
      }

      .hero {
        position: relative;
        z-index: 1;
        display: grid;
        grid-template-columns: minmax(0, 1.08fr) 360px;
        min-height: inherit;
      }

      .copy {
        position: relative;
        padding: 64px;
      }

      .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        min-height: 34px;
        border: 1px solid rgba(19, 33, 28, 0.12);
        border-radius: 999px;
        padding: 6px 12px;
        color: #245f4d;
        background: rgba(255, 255, 255, 0.52);
        font-size: 13px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
      }

      .pulse {
        width: 9px;
        height: 9px;
        border-radius: 999px;
        background: var(--glow);
        box-shadow: 0 0 0 0 rgba(88, 215, 176, 0.56);
        animation: pulse 1.8s infinite;
      }

      h1 {
        position: relative;
        margin: 34px 0 16px;
        max-width: 650px;
        font-size: clamp(52px, 8vw, 104px);
        line-height: 0.94;
        letter-spacing: -0.08em;
      }

      h1 span {
        display: block;
      }

      .ghost {
        position: absolute;
        left: 7px;
        top: 7px;
        z-index: -1;
        color: transparent;
        -webkit-text-stroke: 1px rgba(36, 95, 77, 0.18);
        transform: translate3d(var(--parallax-x, 0), var(--parallax-y, 0), 0);
      }

      .summary {
        max-width: 570px;
        margin: 0;
        color: var(--muted);
        font-size: 17px;
        line-height: 1.9;
      }

      .stepLabel {
        display: grid;
        gap: 9px;
        margin-top: 34px;
      }

      .stepLabel small {
        color: #759183;
        font-size: 12px;
        letter-spacing: 0.22em;
        text-transform: uppercase;
      }

      .parallaxText {
        position: relative;
        min-height: 58px;
        font-size: clamp(28px, 5vw, 56px);
        font-weight: 800;
        letter-spacing: -0.05em;
      }

      .parallaxText::before,
      .parallaxText::after {
        content: attr(data-text);
        position: absolute;
        inset: 0 auto auto 0;
        pointer-events: none;
      }

      .parallaxText::before {
        color: rgba(123, 215, 255, 0.35);
        transform: translate3d(calc(var(--parallax-x, 0) * -0.8), -7px, 0);
      }

      .parallaxText::after {
        color: rgba(255, 174, 200, 0.34);
        transform: translate3d(calc(var(--parallax-x, 0) * 0.7), 8px, 0);
      }

      .parallaxText strong {
        position: relative;
        z-index: 2;
        background: linear-gradient(100deg, #183a31, #0a8b68 42%, #1773a8);
        -webkit-background-clip: text;
        color: transparent;
      }

      .ticker {
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        overflow: hidden;
        border-top: 1px solid rgba(37, 80, 63, 0.12);
        background: rgba(255, 255, 255, 0.42);
        white-space: nowrap;
      }

      .tickerTrack {
        display: inline-flex;
        gap: 48px;
        min-width: 200%;
        padding: 16px 0;
        color: rgba(19, 33, 28, 0.58);
        font-size: 14px;
        letter-spacing: 0.2em;
        animation: ticker 20s linear infinite;
      }

      .status {
        position: relative;
        border-left: 1px solid rgba(37, 80, 63, 0.14);
        padding: 64px 42px;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.44), rgba(255, 255, 255, 0.2));
      }

      .ring {
        width: 188px;
        height: 188px;
        margin: 0 auto 40px;
        border-radius: 50%;
        display: grid;
        place-items: center;
        background:
          radial-gradient(circle at center, rgba(255, 255, 255, 0.72) 0 58%, transparent 59%),
          conic-gradient(from 90deg, var(--glow), var(--cyan), var(--gold), var(--glow));
        box-shadow: 0 20px 55px rgba(36, 95, 77, 0.14);
        animation: rotateGlow 9s linear infinite;
      }

      .ringText {
        display: grid;
        place-items: center;
        width: 150px;
        height: 150px;
        border-radius: 50%;
        background: rgba(250, 255, 252, 0.82);
        animation: rotateGlow 9s linear infinite reverse;
      }

      .ringText strong {
        font-size: 42px;
        letter-spacing: -0.06em;
      }

      .ringText span {
        color: var(--muted);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.2em;
      }

      .steps {
        display: grid;
        gap: 12px;
        margin: 0;
        padding: 0;
        list-style: none;
      }

      .steps li {
        display: grid;
        grid-template-columns: 28px 1fr;
        gap: 11px;
        align-items: center;
        min-height: 70px;
        border: 1px solid rgba(37, 80, 63, 0.13);
        border-radius: 18px;
        padding: 12px 14px;
        background: rgba(255, 255, 255, 0.48);
        color: var(--muted);
      }

      .steps li.active {
        color: #12362d;
        border-color: rgba(10, 139, 104, 0.35);
        background: rgba(255, 255, 255, 0.74);
      }

      .steps li.done {
        color: #245f4d;
      }

      .index {
        display: grid;
        place-items: center;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: rgba(37, 80, 63, 0.1);
        color: #789286;
        font-weight: 800;
      }

      .steps li.active .index,
      .steps li.done .index {
        color: white;
        background: linear-gradient(135deg, #0a8b68, #5ac8ff);
        box-shadow: 0 0 26px rgba(88, 215, 176, 0.46);
      }

      .steps li.error .index {
        color: white;
        background: #a3403b;
      }

      .stepTitle,
      .stepMeta {
        display: block;
      }

      .stepTitle {
        font-weight: 800;
      }

      .stepMeta {
        margin-top: 3px;
        font-size: 12px;
        line-height: 1.45;
      }

      #elapsed {
        margin: 30px 0 0;
        color: #445c51;
        font-weight: 700;
      }

      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 28px;
      }

      a,
      button {
        min-height: 42px;
        border: 1px solid rgba(37, 80, 63, 0.15);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.64);
        color: var(--ink);
        padding: 0 18px;
        cursor: pointer;
        font: inherit;
        font-weight: 800;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
      }

      .primary {
        border-color: transparent;
        background: linear-gradient(135deg, #0a8b68, #1679a8);
        color: white;
        box-shadow: 0 12px 28px rgba(10, 139, 104, 0.25);
      }

      .candidate-list {
        display: grid;
        gap: 5px;
        margin-top: 18px;
        color: var(--muted);
        font-size: 12px;
        overflow-wrap: anywhere;
      }

      .diagnostics {
        position: absolute;
        left: 42px;
        right: 42px;
        bottom: 48px;
        z-index: 2;
        opacity: 0;
        transform: translateY(8px);
        pointer-events: none;
        transition: opacity 160ms ease, transform 160ms ease;
      }

      .diagnostics.show {
        opacity: 1;
        transform: translateY(0);
      }

      code {
        display: block;
        margin-top: 10px;
        border-radius: 14px;
        background: rgba(17, 26, 22, 0.88);
        color: #d9f1e5;
        padding: 12px;
        line-height: 1.65;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        font-family: "Cascadia Mono", Consolas, monospace;
        font-size: 12px;
      }

      @keyframes lightSweep {
        0%,
        100% {
          transform: translateX(-26%);
        }
        50% {
          transform: translateX(26%);
        }
      }

      @keyframes panelShine {
        0%,
        100% {
          transform: translateX(-62%);
        }
        55% {
          transform: translateX(62%);
        }
      }

      @keyframes pulse {
        70% {
          box-shadow: 0 0 0 13px rgba(88, 215, 176, 0);
        }
        100% {
          box-shadow: 0 0 0 0 rgba(88, 215, 176, 0);
        }
      }

      @keyframes floatOrb {
        0%,
        100% {
          transform: translate3d(0, 0, 0) scale(1);
        }
        50% {
          transform: translate3d(40px, -24px, 0) scale(1.05);
        }
      }

      @keyframes rotateGlow {
        to {
          transform: rotate(360deg);
        }
      }

      @keyframes ticker {
        to {
          transform: translateX(-50%);
        }
      }

      @media (max-width: 860px) {
        body {
          overflow: auto;
        }

        .stage {
          padding: 18px;
        }

        .panel {
          min-height: auto;
          border-radius: 24px;
        }

        .hero {
          grid-template-columns: 1fr;
        }

        .copy,
        .status {
          padding: 32px;
        }

        .status {
          border-left: 0;
          border-top: 1px solid rgba(37, 80, 63, 0.14);
        }

        .ticker {
          position: relative;
        }

        .diagnostics {
          position: static;
          margin: 0 32px 32px;
        }
      }
    </style>
  </head>
  <body>
    <main class="stage">
      <div class="orb one"></div>
      <div class="orb two"></div>
      <section class="panel">
        <div class="hero">
          <div class="copy">
            <span class="eyebrow"><span class="pulse"></span> 正在启动</span>
            <h1>
              <span>iCloud</span>
              <span>同步启动</span>
              <span class="ghost" aria-hidden="true">iCloud<br />同步启动</span>
            </h1>
            <p class="summary" id="message">正在为你准备 iCloud 同步服务，首次启动可能需要多等一会儿。</p>
            <div class="stepLabel">
              <small>当前进行到</small>
              <div class="parallaxText" id="heroStep" data-text="打开应用窗口">
                <strong>打开同步应用</strong>
              </div>
            </div>
            <div class="candidate-list" id="candidateList"></div>
          </div>

          <aside class="status">
            <div class="ring">
              <div class="ringText">
                <strong id="attempts">0</strong>
                <span>CHECKS</span>
              </div>
            </div>
            <ul class="steps">
              <li id="stepWindow" class="done">
                <span class="index">1</span>
                <span><span class="stepTitle">打开同步应用</span><span class="stepMeta">应用入口已准备好</span></span>
              </li>
              <li id="stepService" class="active">
                <span class="index">2</span>
                <span><span class="stepTitle">准备同步服务</span><span class="stepMeta" id="serviceText">正在连接服务</span></span>
              </li>
              <li id="stepDeps">
                <span class="index">3</span>
                <span><span class="stepTitle">初始化运行环境</span><span class="stepMeta">首次启动可能需要数分钟</span></span>
              </li>
              <li id="stepReady">
                <span class="index">4</span>
                <span><span class="stepTitle">进入同步面板</span><span class="stepMeta">准备完成后自动进入</span></span>
              </li>
            </ul>
            <p id="elapsed">已等待 0 秒。</p>
            <div class="actions">
              <a class="primary" id="openLink" href="#" rel="noreferrer">立即尝试进入</a>
              <button type="button" onclick="checkNow()">重新检测</button>
              <button type="button" onclick="toggleDiagnostics()">查看日志</button>
            </div>
          </aside>
          <div class="diagnostics" id="diagnostics">
            <strong>后端还没有响应，先看这些位置。</strong>
            <code>服务日志：${SERVICE_LOG}
设置页日志：${CONFIG_INIT_LOG}
设置保存日志：${CONFIG_CALLBACK_LOG}
PID 文件：${PID_FILE}

SSH 排查命令：
tail -n 200 "${SERVICE_LOG}"
ls -lah "${LOG_DIR}"
cat "${PID_FILE}" 2>/dev/null || true
ss -lntp | grep ":${SERVICE_PORT}" || netstat -lntp 2>/dev/null | grep ":${SERVICE_PORT}" || true
ps -ef | grep -E "waitress|icloudpd|icloud-sync" | grep -v grep</code>
          </div>
          <div class="ticker">
            <div class="tickerTrack">
              <span>打开应用</span>
              <span>准备服务</span>
              <span>同步就绪</span>
              <span>进入面板</span>
              <span>开始使用</span>
              <span>打开应用</span>
              <span>准备服务</span>
              <span>同步就绪</span>
              <span>进入面板</span>
              <span>开始使用</span>
            </div>
          </div>
        </div>
      </section>
    </main>
    <script>
      const configuredPort = "${SERVICE_PORT}";
      const candidates = [
        configuredPort ? "http://" + location.hostname + ":" + configuredPort + "/" : "",
        "http://" + location.hostname + ":8080/",
      ].filter(Boolean).filter((item, index, list) => list.indexOf(item) === index);

      const startedAt = Date.now();
      let attempts = 0;
      let timer = null;
      let bestUrl = candidates[0] || "/";

      const attemptsEl = document.getElementById("attempts");
      const elapsedEl = document.getElementById("elapsed");
      const message = document.getElementById("message");
      const diagnostics = document.getElementById("diagnostics");
      const openLink = document.getElementById("openLink");
      const heroStep = document.getElementById("heroStep");
      const candidateList = document.getElementById("candidateList");
      const serviceText = document.getElementById("serviceText");

      openLink.href = bestUrl;
      serviceText.textContent = "正在连接服务";
      candidateList.innerHTML = candidates.map((url) => "<span>检测地址：" + url + "api/status</span>").join("");
      candidateList.hidden = true;

      function setStep(id, className) {
        document.getElementById(id).className = className || "";
      }

      function setCurrentStep(title, text) {
        heroStep.dataset.text = title;
        heroStep.querySelector("strong").textContent = title;
        message.textContent = text;
      }

      function showDiagnostics() {
        diagnostics.classList.add("show");
        candidateList.hidden = false;
      }

      function toggleDiagnostics() {
        diagnostics.classList.toggle("show");
        candidateList.hidden = !diagnostics.classList.contains("show");
      }

      function updateElapsed() {
        const seconds = Math.floor((Date.now() - startedAt) / 1000);
        elapsedEl.textContent = "已等待 " + seconds + " 秒，检测 " + attempts + " 次。";
        if (seconds > 16 && seconds <= 120) {
          setStep("stepDeps", "active");
          setCurrentStep("初始化运行环境", "同步服务仍在准备中，首次启动可能需要数分钟，请稍等。");
          showDiagnostics();
        }
        if (seconds > 120) {
          setStep("stepService", "error");
          showDiagnostics();
          setCurrentStep("需要重新启动", "等待时间较长，请先在应用中心停止后重新启动本应用。");
        }
      }

      async function probe(rootUrl) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 2500);
        try {
          const response = await fetch(rootUrl + "api/status", { cache: "no-store", signal: controller.signal });
          return response.ok;
        } finally {
          clearTimeout(timeout);
        }
      }

      async function checkNow() {
        attempts += 1;
        attemptsEl.textContent = attempts;
        updateElapsed();

        for (const rootUrl of candidates) {
          try {
            if (await probe(rootUrl)) {
              bestUrl = rootUrl;
              openLink.href = bestUrl;
              setStep("stepService", "done");
              setStep("stepDeps", "done");
              setStep("stepReady", "active");
              setCurrentStep("进入同步面板", "同步服务已准备好，正在为你打开配置面板。");
              clearInterval(timer);
              setTimeout(() => {
                window.location.href = bestUrl;
              }, 500);
              return;
            }
          } catch (error) {
            if (Math.floor((Date.now() - startedAt) / 1000) <= 16) {
              setCurrentStep("准备同步服务", "正在连接同步服务，准备完成后会自动进入面板。");
            }
          }
        }
      }

      window.addEventListener("pointermove", (event) => {
        const x = (event.clientX / window.innerWidth - 0.5) * 18;
        const y = (event.clientY / window.innerHeight - 0.5) * 12;
        document.documentElement.style.setProperty("--parallax-x", x + "px");
        document.documentElement.style.setProperty("--parallax-y", y + "px");
      });

      timer = setInterval(checkNow, 3000);
      checkNow();
    </script>
  </body>
</html>
HTML
