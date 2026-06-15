#!/bin/bash

cat <<'HTML'
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
        font-family: "HarmonyOS Sans SC", "MiSans", "Microsoft YaHei", sans-serif;
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

      .side {
        position: relative;
        display: grid;
        align-content: center;
        gap: 16px;
        border-left: 1px solid rgba(37, 80, 63, 0.12);
        padding: 44px 34px;
        background:
          linear-gradient(180deg, rgba(255, 255, 255, 0.42), rgba(255, 255, 255, 0.1)),
          radial-gradient(circle at 50% 18%, rgba(255, 229, 154, 0.32), transparent 48%);
      }

      .ring {
        position: relative;
        width: 184px;
        height: 184px;
        margin: 0 auto 16px;
        border-radius: 999px;
        display: grid;
        place-items: center;
        background: rgba(255, 255, 255, 0.34);
        overflow: hidden;
      }

      .ring::after {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: inherit;
        background:
          conic-gradient(from 210deg, var(--glow), var(--cyan), var(--gold), var(--glow));
        animation: rotate 5s linear infinite;
      }

      .ring::before {
        content: "";
        position: absolute;
        inset: 10px;
        z-index: 1;
        border-radius: inherit;
        background: rgba(250, 255, 252, 0.9);
      }

      .ringText {
        position: relative;
        z-index: 2;
        text-align: center;
      }

      .ringText strong {
        display: block;
        font-size: 42px;
        letter-spacing: -0.08em;
      }

      .ringText span {
        color: var(--muted);
        font-size: 12px;
        letter-spacing: 0.18em;
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
        min-height: 54px;
        border: 1px solid rgba(37, 80, 63, 0.12);
        border-radius: 18px;
        padding: 10px 12px;
        background: rgba(255, 255, 255, 0.44);
        color: #779082;
        transition: transform 260ms ease, border-color 260ms ease, background 260ms ease, color 260ms ease;
      }

      .steps li.active {
        color: #12362d;
        border-color: rgba(10, 139, 104, 0.35);
        background: rgba(255, 255, 255, 0.74);
        transform: translateX(-8px);
      }

      .steps li.done {
        color: #245f4d;
      }

      .index {
        width: 28px;
        height: 28px;
        border-radius: 999px;
        display: grid;
        place-items: center;
        background: rgba(19, 33, 28, 0.08);
        font-size: 12px;
        font-weight: 800;
      }

      .steps li.active .index,
      .steps li.done .index {
        color: white;
        background: linear-gradient(135deg, #0a8b68, #5ac8ff);
        box-shadow: 0 0 26px rgba(88, 215, 176, 0.46);
      }

      .stepTitle {
        display: block;
        font-size: 14px;
        font-weight: 800;
      }

      .stepMeta {
        display: block;
        margin-top: 2px;
        font-size: 12px;
      }

      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 4px;
      }

      a,
      button {
        min-height: 40px;
        border: 1px solid rgba(19, 33, 28, 0.14);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.58);
        color: #164235;
        padding: 9px 16px;
        text-decoration: none;
        cursor: pointer;
        font: inherit;
        font-weight: 700;
      }

      a.primary {
        color: white;
        border-color: transparent;
        background: linear-gradient(135deg, #0a8b68, #1773a8);
        box-shadow: 0 16px 36px rgba(10, 139, 104, 0.22);
      }

      .diagnostics {
        display: none;
        grid-column: 1 / -1;
        border-top: 1px solid rgba(37, 80, 63, 0.12);
        padding: 18px 64px 60px;
        color: var(--muted);
      }

      .diagnostics.show {
        display: block;
      }

      code {
        display: block;
        overflow-wrap: anywhere;
        border-radius: 18px;
        background: rgba(14, 25, 21, 0.86);
        color: #d9f9eb;
        padding: 14px;
        margin-top: 10px;
        font-family: Consolas, "Courier New", monospace;
        font-size: 12px;
        line-height: 1.7;
      }

      @keyframes lightSweep {
        0%, 100% { transform: translateX(-26%) rotate(-4deg); opacity: 0.24; }
        45% { transform: translateX(32%) rotate(-4deg); opacity: 0.72; }
      }

      @keyframes panelShine {
        0%, 100% { transform: translateX(-58%); opacity: 0.28; }
        50% { transform: translateX(58%); opacity: 0.8; }
      }

      @keyframes ticker {
        to { transform: translateX(-50%); }
      }

      @keyframes pulse {
        70% { box-shadow: 0 0 0 12px rgba(88, 215, 176, 0); }
        100% { box-shadow: 0 0 0 0 rgba(88, 215, 176, 0); }
      }

      @keyframes rotate {
        to { transform: rotate(360deg); }
      }

      @keyframes floatOrb {
        0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
        50% { transform: translate3d(36px, -28px, 0) scale(1.08); }
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
        }

        .hero {
          grid-template-columns: 1fr;
        }

        .copy {
          padding: 38px 26px 92px;
        }

        .side {
          border-left: 0;
          border-top: 1px solid rgba(37, 80, 63, 0.12);
          padding: 28px 22px 34px;
        }

        .diagnostics {
          padding: 18px 24px 32px;
        }
      }
    </style>
  </head>
  <body>
    <main class="stage" id="stage">
      <div class="orb one" aria-hidden="true"></div>
      <div class="orb two" aria-hidden="true"></div>
      <section class="panel">
        <div class="hero">
          <div class="copy">
            <span class="eyebrow"><span class="pulse"></span> launch sequence</span>
            <h1>
              <span>iCloud</span>
              <span>同步启动</span>
              <span class="ghost" aria-hidden="true">iCloud<br />同步启动</span>
            </h1>
            <p class="summary" id="message">正在打开应用窗口，检测后端服务是否已经准备好。首启需要拉取镜像、安装依赖，耐心一点点，光已经在路上。</p>
            <div class="stepLabel">
              <small>当前进行到</small>
              <div class="parallaxText" id="heroStep" data-text="打开应用窗口">
                <strong>打开应用窗口</strong>
              </div>
            </div>
          </div>
          <aside class="side" aria-label="启动进度">
            <div class="ring" aria-hidden="true">
              <div class="ringText">
                <strong id="attempts">0</strong>
                <span>CHECKS</span>
              </div>
            </div>
            <ul class="steps">
              <li id="stepWindow" class="done">
                <span class="index">1</span>
                <span><span class="stepTitle">应用窗口已打开</span><span class="stepMeta">入口页加载完成</span></span>
              </li>
              <li id="stepService" class="active">
                <span class="index">2</span>
                <span><span class="stepTitle">等待 Web 服务监听</span><span class="stepMeta">正在检测 8080 端口</span></span>
              </li>
              <li id="stepDeps">
                <span class="index">3</span>
                <span><span class="stepTitle">准备 Docker 与依赖</span><span class="stepMeta">首启可能需要数分钟</span></span>
              </li>
              <li id="stepReady">
                <span class="index">4</span>
                <span><span class="stepTitle">进入同步面板</span><span class="stepMeta">服务就绪后自动跳转</span></span>
              </li>
            </ul>
            <p id="elapsed">已等待 0 秒。</p>
            <div class="actions">
              <a class="primary" id="openLink" href="#" rel="noreferrer">立即尝试进入</a>
              <button type="button" onclick="checkNow()">重新检测</button>
            </div>
          </aside>
          <div class="diagnostics" id="diagnostics">
            <strong>超过 2 分钟仍未进入时，可以在 SSH 里看容器状态：</strong>
            <code>docker ps -a | grep fnos-icloud-sync
docker logs fnos-icloud-sync --tail 200</code>
          </div>
        </div>
        <div class="ticker" aria-hidden="true">
          <div class="tickerTrack" id="tickerTrack">
            <span>启动窗口</span>
            <span>检测服务</span>
            <span>等待容器</span>
            <span>安装依赖</span>
            <span>进入面板</span>
            <span>启动窗口</span>
            <span>检测服务</span>
            <span>等待容器</span>
            <span>安装依赖</span>
            <span>进入面板</span>
          </div>
        </div>
      </section>
    </main>
    <script>
      const url = `http://${location.hostname}:8080/`;
      const statusUrl = `${url}api/status`;
      const startedAt = Date.now();
      const stepText = document.getElementById("heroStep");
      const message = document.getElementById("message");
      const attemptsEl = document.getElementById("attempts");
      const elapsedEl = document.getElementById("elapsed");
      const diagnostics = document.getElementById("diagnostics");
      const stage = document.getElementById("stage");
      let attempts = 0;
      let timer = null;
      document.getElementById("openLink").href = url;

      function setCurrentStep(text, detail) {
        stepText.dataset.text = text;
        stepText.querySelector("strong").textContent = text;
        message.textContent = detail;
      }

      function setStep(id, className) {
        document.getElementById(id).className = className;
      }

      function updateElapsed() {
        const seconds = Math.floor((Date.now() - startedAt) / 1000);
        elapsedEl.textContent = `已等待 ${seconds} 秒，检测 ${attempts} 次。`;
        if (seconds > 16 && seconds <= 120) {
          setStep("stepDeps", "active");
          setCurrentStep("准备 Docker 与依赖", "后端暂未响应，首次启动可能正在拉取镜像、创建虚拟环境或安装 icloudpd。");
        }
        if (seconds > 120) {
          diagnostics.classList.add("show");
          setCurrentStep("等待人工排查", "后端服务还没有响应，建议查看容器状态和日志。");
        }
      }

      async function checkNow() {
        attempts += 1;
        attemptsEl.textContent = attempts;
        updateElapsed();
        try {
          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), 2600);
          const response = await fetch(statusUrl, { cache: "no-store", signal: controller.signal });
          clearTimeout(timeout);
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          setStep("stepService", "done");
          setStep("stepDeps", "done");
          setStep("stepReady", "active");
          setCurrentStep("进入同步面板", "后端服务已就绪，正在为你打开 iCloud 同步配置面板。");
          clearInterval(timer);
          setTimeout(() => {
            window.location.href = url;
          }, 680);
        } catch (error) {
          if (Math.floor((Date.now() - startedAt) / 1000) <= 16) {
            setCurrentStep("等待 Web 服务监听", "正在检测 8080 端口，服务启动完成后会自动进入面板。");
          }
        }
      }

      stage.addEventListener("pointermove", (event) => {
        const x = (event.clientX / window.innerWidth - 0.5) * 18;
        const y = (event.clientY / window.innerHeight - 0.5) * 12;
        document.documentElement.style.setProperty("--parallax-x", `${x}px`);
        document.documentElement.style.setProperty("--parallax-y", `${y}px`);
      });

      timer = setInterval(checkNow, 3000);
      checkNow();
    </script>
  </body>
</html>
HTML
