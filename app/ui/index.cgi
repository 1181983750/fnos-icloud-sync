#!/bin/bash

SERVICE_PORT="${TRIM_SERVICE_PORT:-8080}"

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
        --bg: #f4f6f4;
        --surface: #ffffff;
        --surface-soft: #eef5f1;
        --line: #d7ded9;
        --text: #1d2521;
        --muted: #65746c;
        --green: #14795b;
        --green-deep: #0d5f47;
        --amber: #9b6718;
        --red: #a3403b;
        --blue: #376fa3;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        background: var(--bg);
        color: var(--text);
        font-family: Inter, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
        font-size: 14px;
      }

      main {
        width: min(980px, calc(100% - 32px));
        min-height: 100vh;
        margin: 0 auto;
        display: grid;
        align-content: center;
        gap: 14px;
        padding: 28px 0;
      }

      .topline {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
      }

      .eyebrow {
        margin: 0 0 6px;
        color: var(--green);
        font-size: 13px;
        font-weight: 800;
      }

      h1,
      h2,
      p {
        margin: 0;
      }

      h1 {
        font-size: clamp(28px, 4vw, 44px);
        letter-spacing: 0;
      }

      .pill {
        display: inline-flex;
        align-items: center;
        min-height: 32px;
        border-radius: 6px;
        padding: 0 10px;
        background: #e5f3ed;
        color: var(--green-deep);
        font-weight: 800;
        white-space: nowrap;
      }

      .panel {
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        padding: 18px;
        box-shadow: 0 12px 30px rgba(25, 40, 32, 0.08);
      }

      .status-grid {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 280px;
        gap: 14px;
      }

      .lead {
        color: var(--muted);
        line-height: 1.8;
        margin-top: 10px;
      }

      .steps {
        display: grid;
        gap: 10px;
        margin: 0;
        padding: 0;
        list-style: none;
      }

      .step {
        display: grid;
        grid-template-columns: 28px minmax(0, 1fr);
        gap: 10px;
        align-items: center;
        min-height: 58px;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 10px;
        background: #fbfcfb;
        color: var(--muted);
      }

      .step strong,
      .step span {
        display: block;
      }

      .step strong {
        color: var(--text);
      }

      .step .num {
        display: grid;
        place-items: center;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: #dfe8e3;
        color: #415249;
        font-size: 12px;
        font-weight: 800;
      }

      .step.active {
        border-color: #9dc9b9;
        background: #f0faf5;
      }

      .step.done .num,
      .step.active .num {
        background: var(--green);
        color: #fff;
      }

      .step.error {
        border-color: #efc0ba;
        background: #fff6f4;
      }

      .step.error .num {
        background: var(--red);
        color: #fff;
      }

      .metrics {
        display: grid;
        gap: 10px;
      }

      .metric {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 12px;
        background: var(--surface-soft);
      }

      .metric span {
        display: block;
        color: var(--muted);
        margin-bottom: 6px;
      }

      .metric strong {
        display: block;
        font-size: 22px;
      }

      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 16px;
      }

      a,
      button {
        min-height: 36px;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: #fff;
        color: var(--text);
        padding: 0 14px;
        cursor: pointer;
        font: inherit;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
      }

      .primary {
        border-color: var(--green);
        background: var(--green);
        color: #fff;
        font-weight: 800;
      }

      .diagnostics {
        display: none;
      }

      .diagnostics.show {
        display: block;
      }

      code {
        display: block;
        margin-top: 10px;
        border-radius: 8px;
        background: #111a16;
        color: #d9f1e5;
        padding: 12px;
        line-height: 1.65;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        font-family: "Cascadia Mono", Consolas, monospace;
        font-size: 12px;
      }

      .candidate-list {
        display: grid;
        gap: 6px;
        margin-top: 10px;
        color: var(--muted);
      }

      @media (max-width: 760px) {
        .topline,
        .status-grid {
          grid-template-columns: 1fr;
        }

        .topline {
          align-items: flex-start;
          flex-direction: column;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <section class="topline">
        <div>
          <p class="eyebrow">FNOS iCloud Sync</p>
          <h1>iCloud 同步正在启动</h1>
        </div>
        <span id="statePill" class="pill">检测中</span>
      </section>

      <section class="panel status-grid">
        <div>
          <h2 id="headline">正在连接 Web 面板</h2>
          <p id="message" class="lead">窗口已经打开，正在检测后端服务。如果是首次启动，Docker 拉取镜像和安装依赖可能需要几分钟。</p>
          <div class="actions">
            <a id="openLink" class="primary" href="#" rel="noreferrer">立即尝试进入</a>
            <button type="button" onclick="checkNow()">重新检测</button>
          </div>
          <div id="candidateList" class="candidate-list"></div>
        </div>

        <div class="metrics">
          <div class="metric">
            <span>检测次数</span>
            <strong id="attempts">0</strong>
          </div>
          <div class="metric">
            <span>等待时间</span>
            <strong id="elapsed">0 秒</strong>
          </div>
        </div>
      </section>

      <section class="panel">
        <ol class="steps">
          <li id="stepWindow" class="step done">
            <span class="num">1</span>
            <span><strong>应用窗口已打开</strong><span>本地启动页加载完成</span></span>
          </li>
          <li id="stepService" class="step active">
            <span class="num">2</span>
            <span><strong>等待 Web 服务监听</strong><span id="serviceText">正在检测服务端口</span></span>
          </li>
          <li id="stepReady" class="step">
            <span class="num">3</span>
            <span><strong>进入同步面板</strong><span>服务就绪后自动跳转</span></span>
          </li>
        </ol>
      </section>

      <section id="diagnostics" class="panel diagnostics">
        <h2>还没有连上时这样排查</h2>
        <p class="lead">如果超过 2 分钟仍停在这里，通常是容器未启动、服务端口未映射成功，或依赖安装失败。可以在飞牛 SSH 中查看：</p>
        <code>docker ps -a | grep fnos-icloud-sync
docker logs fnos-icloud-sync --tail 200</code>
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
      const headline = document.getElementById("headline");
      const message = document.getElementById("message");
      const statePill = document.getElementById("statePill");
      const diagnostics = document.getElementById("diagnostics");
      const openLink = document.getElementById("openLink");
      const candidateList = document.getElementById("candidateList");
      const serviceText = document.getElementById("serviceText");

      openLink.href = bestUrl;
      serviceText.textContent = "正在检测：" + candidates.join("，");
      candidateList.innerHTML = candidates.map((url) => "<span>候选入口：" + url + "</span>").join("");

      function setStep(id, className) {
        document.getElementById(id).className = ("step " + className).trim();
      }

      function updateElapsed() {
        const seconds = Math.floor((Date.now() - startedAt) / 1000);
        elapsedEl.textContent = seconds + " 秒";
        if (seconds > 20 && seconds <= 120) {
          headline.textContent = "正在等待容器与依赖";
          message.textContent = "后端暂未响应。首次启动可能正在拉取 python:3.12-slim、创建虚拟环境或安装 icloudpd。";
          statePill.textContent = "等待中";
        }
        if (seconds > 120) {
          headline.textContent = "需要查看容器日志";
          message.textContent = "后端服务仍未响应，建议打开运行日志或用 SSH 查看容器状态。";
          statePill.textContent = "需排查";
          statePill.style.background = "#fbe6e2";
          statePill.style.color = "#a3403b";
          setStep("stepService", "error");
          diagnostics.classList.add("show");
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
              headline.textContent = "服务已就绪";
              message.textContent = "正在进入 iCloud 同步配置面板。";
              statePill.textContent = "已连接";
              setStep("stepService", "done");
              setStep("stepReady", "active");
              clearInterval(timer);
              setTimeout(() => {
                window.location.href = bestUrl;
              }, 500);
              return;
            }
          } catch (error) {
            // Keep trying the next candidate.
          }
        }
      }

      timer = setInterval(checkNow, 3000);
      checkNow();
    </script>
  </body>
</html>
HTML
