# app/server 模块

`app/server/` 是 iCloud 同步的后端服务目录。

## 关键文件

- `server.py`：Flask API、配置读写、任务调度、iCloud 认证、媒体同步和备忘录导出。
- `requirements.txt`：运行时 Python 依赖版本。
- `static/`：Web 面板页面、样式和脚本。
- `wheels/`：离线依赖 wheel 文件。

## 主要接口

- `GET /api/status`：返回任务状态、存储路径、依赖检测结果和统计信息。
- `POST /api/config`：保存当前同步方案配置。
- `POST /api/auth`：执行 iCloud 认证。
- `POST /api/sync/media`：同步照片/视频。
- `POST /api/sync/notes`：导出备忘录。

## 维护注意

- `media_mode=copy` 只下载新增内容，不删除 iCloud 云端。
- `media_mode=mirror` 使用 `--auto-delete`，只让 NAS 本地跟随云端删除。
- `media_mode=move` 使用 `--keep-icloud-recent-days 0`，会请求删除 iCloud 云端对应媒体，是高风险模式。
- 认证任务不应带媒体删除参数，避免认证阶段触发危险行为。
