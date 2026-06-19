# app/server 模块

`app/server/` 是 iCloud 同步的后端服务目录。

## 关键文件

- `server.py`：Flask API、配置读写、任务调度、iCloud 认证、媒体同步和备忘录导出。
- `requirements.txt`：运行时 Python 依赖版本。
- `static/`：Web 面板页面、样式和脚本。
- `wheels/`：离线依赖 wheel 文件。

## 主要接口

- `GET /api/status`：返回任务状态、计划同步调度状态、存储路径、依赖检测结果和统计信息。
- `POST /api/config`：保存当前同步方案配置。
- `POST /api/auth`：执行 iCloud 认证。
- `POST /api/sync/media`：同步照片/视频。
- `POST /api/sync/notes`：导出备忘录。

## 维护注意

- `media_mode=copy` 只下载新增内容，不删除 iCloud 云端。
- `media_mode=mirror` 使用 `--auto-delete`，只让 NAS 本地跟随云端删除。
- `media_mode=move` 使用 `--keep-icloud-recent-days 0`，会请求删除 iCloud 云端对应媒体，是高风险模式。
- 媒体同步失败会按 `retry_attempts` 和 `retry_delay_seconds` 自动重试；重试等待期间如果用户停止任务，不应继续拉起下一次同步。
- 当前内置 `icloudpd==1.32.3` 不支持 `--download-delay` 和 `--max-concurrent-downloads`，不要把这些参数写进运行命令；多线程和下载延时节流放在未来实现规划中。
- 认证任务不应带媒体删除参数，避免认证阶段触发危险行为。
- 当前任务执行模型是“每个方案一次一个任务”，不同方案之间允许并行；同一方案仍然禁止同时启动多个认证、媒体或备忘录任务，避免共享目录、Cookie 和控制台输入互相干扰。
- 当前并发实现使用 Web 服务内线程编排，每个媒体/认证任务再启动各自的 `icloudpd` 子进程；备忘录导出继续用独立线程执行 IMAP I/O。
- 修改同步根目录后，需要在应用中心停止并重新启动应用，让原生服务读取新的根目录。
