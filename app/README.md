# app 模块

`app/` 是 FPK 安装后复制到 fnOS 的运行时应用目录。

## 子模块

- `docker/`：Docker Compose 项目，负责启动后端容器。
- `server/`：Flask 后端、同步任务逻辑和 Web 面板静态资源。
- `ui/`：fnOS 桌面入口 CGI 和入口配置。

## 维护注意

- 这里的内容会被 `fnpack` 打进 `app.tgz`。
- 修改后端、前端或桌面入口后，都需要重新运行 `scripts/build-fpk.ps1` 生成 FPK 验包。
- 不要把运行时生成的配置、Cookie、日志放进本目录；这些数据应保存在 `/config`、`/logs` 或应用共享目录。
