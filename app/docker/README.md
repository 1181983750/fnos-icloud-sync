# app/docker 模块

`app/docker/` 保存 fnOS Docker 项目配置。

## 关键文件

- `docker-compose.yaml`：启动 `python:3.12-slim` 容器，挂载应用代码、配置目录、日志目录和同步根目录。

## 运行逻辑

- 容器首次启动会创建 `/config/venv`。
- 如果 `/opt/icloud-sync/wheels` 中存在 wheel，优先离线安装依赖。
- Web 服务监听容器内 `8080`，由 fnOS 映射到应用端口。
- 同步文件始终写入容器内 `/data`，Docker Compose 会把 `wizard_sync_root_path` 指向的 NAS 目录挂载到 `/data`。
- 应用代码使用相对路径 `../server:/opt/icloud-sync:ro` 挂载，避免 `${TRIM_APPDEST}` 未传入 Docker Compose 时挂出空目录，导致容器找不到 `requirements.txt`。
- 飞牛应用设置保存同步根目录时，`cmd/config_callback` 会写入 `app/docker/.env`；用户在 Docker 页面重新构建 Compose 时，Compose 会读取该文件保留 `wizard_sync_root_path`。

## 维护注意

- 默认同步根目录为 `/var/apps/icloud-sync/shares/icloud`。
- 修改同步根目录后需要重新创建/启动容器，旧容器不会自动切换已经存在的 `/data` 挂载。
- 页面内服务进程重启不能刷新 Docker 挂载；必须通过应用中心或 Docker Compose 重新创建项目。
- Compose 对 `TRIM_SERVICE_PORT` 和 `TRIM_PKGVAR` 提供默认值，避免用户在 Docker 页面手动重启项目时变量为空导致服务端口或持久化目录异常。
- 修改虚拟环境依赖安装逻辑时，必要时更新 sentinel 文件名，确保旧环境会重新安装依赖。
- 不要把用户密码、Cookie 或下载数据写进镜像层。
