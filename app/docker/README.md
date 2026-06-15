# app/docker 模块

`app/docker/` 保存 fnOS Docker 项目配置。

## 关键文件

- `docker-compose.yaml`：启动 `python:3.12-slim` 容器，挂载应用代码、配置目录、日志目录和同步根目录。

## 运行逻辑

- 容器首次启动会创建 `/config/venv`。
- 如果 `/opt/icloud-sync/wheels` 中存在 wheel，优先离线安装依赖。
- Web 服务监听容器内 `8080`，由 fnOS 映射到应用端口。

## 维护注意

- 默认同步根目录为 `/var/apps/icloud-sync/shares/icloud`。
- 修改虚拟环境依赖安装逻辑时，必要时更新 sentinel 文件名，确保旧环境会重新安装依赖。
- 不要把用户密码、Cookie 或下载数据写进镜像层。
