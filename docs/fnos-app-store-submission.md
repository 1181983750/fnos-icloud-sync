# iCloud 同步 - fnOS 应用上架资料

## 基础信息

- 应用名称：iCloud 同步
- 应用包名：icloud-sync
- 当前版本：0.2.32
- 应用类型：Docker 型 FPK 应用
- 支持平台：x86_64
- 最低系统版本：fnOS 1.1.8
- 服务端口：8080
- GitHub 仓库：https://github.com/1181983750/fnos-icloud-sync
- Release 地址：https://github.com/1181983750/fnos-icloud-sync/releases/tag/v0.2.32
- FPK 下载地址：https://github.com/1181983750/fnos-icloud-sync/releases/download/v0.2.32/icloud-sync-0.2.32.fpk
- FPK SHA256：AC7E6036ACD30512ABEEF046787E641F690A5CE94FC077F61D7714A1E1BBB4FD

## 应用简介

iCloud 同步是在飞牛 NAS 上运行的 iCloud 数据同步工具。应用通过 Web 面板配置 Apple ID、认证验证码、同步范围和存储位置，支持把 iCloud 照片、视频下载到 NAS，并提供实验性的 iCloud 备忘录 IMAP 导出能力。应用支持多同步方案，适合家庭成员、多 Apple ID 或不同同步策略分开管理。默认只下载到 NAS，不删除 iCloud 云端；用户也可以手动启用高风险“下载后删除 iCloud 云端”模式，用于把媒体转存到 NAS 后清理 iCloud 空间。

## 主要功能

- 照片同步：调用 icloudpd 将 iCloud Photos 照片下载到 NAS。
- 视频同步：可单独同步视频文件，默认保存到 videos 目录。
- 多方案管理：支持创建多个同步方案，方案之间的 Cookie、目录、状态相互隔离。
- Apple ID 认证：支持 iCloud.com 和中国区 iCloud，默认选择中国区，页面提供验证码/控制台输入发送入口。
- 同步范围配置：支持照片、视频、备忘录开关。
- 媒体下载选项：支持目录结构、相册、资料库、最近天数、照片尺寸、Live Photo、保留中文文件名、写入 EXIF 时间等配置；页面内提供目录占位符、相册名称和资料库选择说明。
- 计划同步：支持按分钟间隔自动同步媒体文件。
- 失败重试：媒体同步遇到 Apple 503、连接重置、临时网络抖动等非 0 退出时，可按配置等待后自动重试。
- 云端清理：可选高风险 Move 模式，媒体同步到 NAS 后请求删除 iCloud 云端对应照片/视频。
- 备忘录导出：通过 iCloud Mail IMAP 读取 Notes/备忘录文件夹，可导出为 Markdown 或 HTML；默认 IMAP 参数已折叠为高级设置，通常只需填写用户名和 App 专用密码。
- 存储位置选择：默认使用应用共享目录 `应用文件/icloud`，也可以在飞牛应用设置中选择已授权目录作为同步根目录。容器内固定写入 `/data`，飞牛会把当前同步根目录挂载到 `/data`；页面会同时展示 NAS 目标目录和容器实际写入目录，修改根目录后需要停止并重新启动应用。
- 启动引导：桌面入口先进入光效视差启动页，显示 Docker、依赖和 Web 服务状态，后端就绪后进入同步面板。
- 启动引导面向普通用户展示“正在准备同步服务”，默认隐藏端口、候选入口、Docker 和依赖等调试信息。
- 玻璃面板：启动页和主同步面板统一为 iOS 26 风格玻璃视觉，下拉框、按钮和提示控件使用高透明玻璃样式。
- 日志查看：运行日志不会在用户手动上翻时强制滚动到底部，便于排查中途报错。
- 离线依赖：FPK 内置 Flask 与 icloudpd 运行依赖 wheel，减少首次启动下载等待。

## 权限与数据说明

- 应用下载结果默认保存到 `/var/apps/icloud-sync/shares/icloud`。如果用户在飞牛应用设置中选择 `/vol1/1000/windows用盘符Z`，并把方案保存文件夹设为 `wyl_icloud`，重启应用后照片、视频、备忘录分别保存到 `/vol1/1000/windows用盘符Z/wyl_icloud/photos`、`/videos`、`/notes`。
- 配置、Cookie、日志保存到应用私有持久化目录。
- Apple ID、密码和 Cookie 只保存在本机，不上传到第三方服务器。
- 如果用户不勾选保存密码，计划同步依赖 Cookie；Cookie 过期后需要重新手动认证。
- 应用需要访问 Docker 服务、应用共享目录以及用户在应用设置中授权的目录。
- “同步本地删除”只会处理 NAS 本地已同步文件，不会删除 iCloud 云端照片。
- “下载后删除 iCloud 云端”会请求删除 iCloud 云端对应媒体文件，属于高风险手动选项，默认关闭，并在保存和运行同步前要求输入确认文字。

## 使用注意事项

- 首次启动需要等待 Docker 容器、Python 虚拟环境和依赖准备完成。
- 修改同步根目录后必须在应用中心停止并重新启动应用；如果页面提示当前容器仍挂载旧目录，说明当前任务仍会写入旧目录。
- 如果启用“下载后删除 iCloud 云端”，请先确认 NAS 文件完整且有额外备份；不建议与相册、资料库、最近天数等过滤条件混用，除非明确知道会影响哪些媒体。
- iCloud 登录可能触发双重认证，用户需要在页面右侧验证码输入框中发送验证码。
- 备忘录导出不是 Apple 官方同步 API，依赖 iCloud Mail 中可访问的 Notes/备忘录 IMAP 文件夹。
- 当前包只提供 x86_64 架构；如果需要适配 ARM 设备，需要重新准备 ARM 可用的 icloudpd 依赖包。
- 当前内置 `icloudpd==1.32.3` 不支持 `--download-delay` 和 `--max-concurrent-downloads`，下载延时和多线程/并发下载记录为未来实现，不写入当前运行命令。
- 应用图标使用 iCloud 云朵、同步箭头和 NAS 设备组合图标，桌面入口配置为 `showDesktop=true`、`allUsers=true`、`noDisplay=false`。

## 审核测试建议

1. 在 fnOS 应用中心手动安装 `icloud-sync-0.2.32.fpk`。
2. 启动应用，确认桌面入口可打开光效视差启动页。
3. 等待容器启动完成，进入 iCloud 同步面板。
4. 打开 `/api/status`，确认 `icloudpd_available` 为 `true`，并能看到 `icloudpd_path`。
5. 在应用设置里确认默认共享目录为 `应用文件/icloud`。
6. 选择一个已授权目录作为同步根目录，保存后停止并重新启动应用，确认面板直接展示照片、视频、备忘录最终保存位置。
7. 填写 Apple ID，点击认证 iCloud，并按页面提示输入验证码。
8. 勾选照片/视频后运行同步，确认文件写入所选同步根目录。
9. 如需测试备忘录，填写 iCloud IMAP 账号和 App 专用密码，导出 Notes/备忘录文件夹。

## Release 说明

0.2.32 飞牛应用设置保存同步根目录时会同步生成 Docker Compose .env，避免在 Docker 页面重新构建 Compose 后丢失同步根目录变量又回到默认应用目录；移除无效的页面内重启按钮，未重新创建挂载时会阻止开始同步；运行中允许切换左侧方案查看，当前版本仍保持单任务运行。
