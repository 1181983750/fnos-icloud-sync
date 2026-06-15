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
        --bg: #f4f6f4;
        --surface: #ffffff;
        --line: #d7ded9;
        --text: #1d2521;
        --muted: #65746c;
        --green: #14795b;
        --red: #a3403b;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        background: var(--bg);
        color: var(--text);
        font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      }
      .wrap {
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
      }
      .panel {
        width: min(720px, 100%);
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        padding: 22px;
        box-shadow: 0 12px 30px rgba(25, 40, 32, 0.08);
      }
      .brand {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 14px;
      }
      .mark {
        width: 42px;
        height: 42px;
        border-radius: 8px;
        background: var(--green);
        display: grid;
        place-items: center;
      }
      .mark::before {
        content: "";
        width: 22px;
        height: 14px;
        border-radius: 999px;
        background: white;
        box-shadow: 8px -6px 0 0 white, -7px -2px 0 0 white;
      }
      h1 {
        margin: 0 0 8px;
        font-size: 24px;
        letter-spacing: 0;
      }
      h2 {
        margin: 18px 0 8px;
        font-size: 15px;
      }
      p {
        margin: 8px 0;
        line-height: 1.7;
        color: var(--muted);
      }
      .loader {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 14px 0;
      }
      .spinner {
        width: 20px;
        height: 20px;
        border: 3px solid #dbe6df;
        border-top-color: var(--green);
        border-radius: 999px;
        animation: spin 900ms linear infinite;
      }
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
      .steps {
        display: grid;
        gap: 8px;
        margin: 12px 0;
        padding: 0;
        list-style: none;
      }
      .steps li {
        display: flex;
        align-items: center;
        gap: 9px;
        min-height: 32px;
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 7px 10px;
        color: var(--muted);
      }
      .dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: #c6d1ca;
        flex: 0 0 auto;
      }
      .steps li.active .dot {
        background: var(--green);
      }
      .steps li.done .dot {
        background: #376fa3;
      }
      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 16px;
      }
      a, button {
        min-height: 36px;
        border: 1px solid var(--green);
        border-radius: 6px;
        background: var(--green);
        color: white;
        padding: 8px 14px;
        text-decoration: none;
        cursor: pointer;
        font: inherit;
      }
      button.secondary, a.secondary {
        background: white;
        color: var(--green);
      }
      code {
        display: block;
        overflow-wrap: anywhere;
        border-radius: 6px;
        background: #111a16;
        color: #d9f1e5;
        padding: 10px;
        margin-top: 10px;
        font-family: Consolas, monospace;
        font-size: 12px;
        line-height: 1.6;
      }
      .warn {
        color: var(--red);
      }
      .hidden {
        display: none;
      }
    </style>
  </head>
  <body>
    <main class="wrap">
      <section class="panel">
        <div class="brand">
          <span class="mark" aria-hidden="true"></span>
          <div>
            <h1>iCloud 同步正在启动</h1>
            <p id="message">正在等待后端服务就绪，完成后会自动进入配置面板。</p>
          </div>
        </div>
        <div class="loader">
          <span class="spinner" aria-hidden="true"></span>
          <strong id="loadingText">连接中...</strong>
        </div>
        <ul class="steps" aria-label="启动进度">
          <li class="done"><span class="dot"></span><span>应用窗口已打开</span></li>
          <li id="stepService" class="active"><span class="dot"></span><span>等待 Web 服务监听</span></li>
          <li id="stepDeps"><span class="dot"></span><span>首次启动可能正在拉取镜像和安装依赖</span></li>
          <li id="stepReady"><span class="dot"></span><span>进入 iCloud 同步面板</span></li>
        </ul>
        <p id="elapsed">已等待 0 秒。</p>
        <p>服务地址：</p>
        <code id="serviceUrl">检测中...</code>
        <div class="actions">
          <a id="openLink" href="#" rel="noreferrer">立即尝试进入</a>
          <button class="secondary" type="button" onclick="checkNow()">重新检测</button>
        </div>
        <div id="diagnostics" class="hidden">
          <h2 class="warn">如果超过 2 分钟仍未进入</h2>
          <p>通常是 NAS 网络无法访问 Docker Hub 或 PyPI，或者容器启动失败。SSH 到飞牛后看下面两条：</p>
          <code>docker ps -a | grep fnos-icloud-sync
docker logs fnos-icloud-sync --tail 200</code>
        </div>
      </section>
    </main>
    <script>
      const url = `http://${location.hostname}:8080/`;
      const statusUrl = `${url}api/status`;
      const startedAt = Date.now();
      let attempts = 0;
      let timer = null;
      document.getElementById("serviceUrl").textContent = url;
      document.getElementById("openLink").href = url;

      function setStep(id, className) {
        const el = document.getElementById(id);
        el.className = className;
      }

      function updateElapsed() {
        const seconds = Math.floor((Date.now() - startedAt) / 1000);
        document.getElementById("elapsed").textContent = `已等待 ${seconds} 秒，检测 ${attempts} 次。`;
        if (seconds > 20) {
          setStep("stepDeps", "active");
          document.getElementById("loadingText").textContent = "仍在等待，首次启动可能需要更久...";
        }
        if (seconds > 120) {
          document.getElementById("diagnostics").classList.remove("hidden");
          document.getElementById("message").textContent = "后端服务还没有响应，请按下方命令查看容器日志。";
        }
      }

      async function checkNow() {
        attempts += 1;
        updateElapsed();
        try {
          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), 2500);
          const response = await fetch(statusUrl, { cache: "no-store", signal: controller.signal });
          clearTimeout(timeout);
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          setStep("stepService", "done");
          setStep("stepDeps", "done");
          setStep("stepReady", "active");
          document.getElementById("loadingText").textContent = "服务已就绪，正在进入...";
          document.getElementById("message").textContent = "后端服务已经响应。";
          clearInterval(timer);
          setTimeout(() => {
            window.location.href = url;
          }, 500);
        } catch (error) {
          document.getElementById("loadingText").textContent = "服务暂未响应，继续等待...";
        }
      }

      timer = setInterval(checkNow, 3000);
      checkNow();
    </script>
  </body>
</html>
HTML
