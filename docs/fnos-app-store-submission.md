# iCloud 同步 - fnOS 应用上架资料

## 基础信息

- 应用名称：iCloud 同步
- 应用包名：icloud-sync
- 当前版本：0.2.20
- 应用类型：Docker 型 FPK 应用
- 支持平台：x86_64
- 最低系统版本：fnOS 1.1.8
- 服务端口：8080
- GitHub 仓库：https://github.com/1181983750/fnos-icloud-sync
- Release 地址：https://github.com/1181983750/fnos-icloud-sync/releases/tag/v0.2.20
- FPK 下载地址：https://github.com/1181983750/fnos-icloud-sync/releases/download/v0.2.20/icloud-sync-0.2.20.fpk
- FPK SHA256：6E12F59836CECA25CE97370666BB800B88BA77BBDFEA84D76396CF9C5B13C9A2

## 应用简介

iCloud 同步是在飞牛 NAS 上运行的 iCloud 数据同步工具。应用通过 Web 面板配置 Apple ID、认证验证码、同步范围和存储位置，支持把 iCloud 照片、视频下载到 NAS，并提供实验性的 iCloud 备忘录 IMAP 导出能力。应用支持多同步方案，适合家庭成员、多 Apple ID 或不同同步策略分开管理。默认只下载到 NAS，不删除 iCloud 云端；用户也可以手动启用高风险“下载后删除 iCloud 云端”模式，用于把媒体转存到 NAS 后清理 iCloud 空间。

## 主要功能

- 照片同步：调用 icloudpd 将 iCloud Photos 照片下载到 NAS。
- 视频同步：可单独同步视频文件，默认保存到 videos 目录。
- 多方案管理：支持创建多个同步方案，方案之间的 Cookie、目录、状态相互隔离。
- Apple ID 认证：支持 iCloud.com 和中国区 iCloud，页面提供验证码/控制台输入发送入口。
- 同步范围配置：支持照片、视频、备忘录开关。
- 媒体下载选项：支持目录结构、相册、资料库、最近天数、照片尺寸、Live Photo、保留中文文件名、写入 EXIF 时间等配置。
- 计划同步：支持按分钟间隔自动同步媒体文件。
- 云端清理：可选高风险 Move 模式，媒体同步到 NAS 后请求删除 iCloud 云端对应照片/视频。
- 备忘录导出：通过 iCloud Mail IMAP 读取 Notes/备忘录文件夹，可导出为 Markdown 或 HTML。
- 存储位置选择：默认使用应用共享目录 `应用文件/icloud`，也可以在飞牛应用设置中选择已授权目录作为同步根目录。
- 启动引导：桌面入口先进入启动检测页，显示 Docker、依赖和 Web 服务状态，后端就绪后进入同步面板。
- 离线依赖：FPK 内置 Flask 与 icloudpd 运行依赖 wheel，减少首次启动下载等待。

## 权限与数据说明

- 应用数据默认保存到 `/var/apps/icloud-sync/shares/icloud`。
- 配置、Cookie、日志保存到应用私有持久化目录。
- Apple ID、密码和 Cookie 只保存在本机，不上传到第三方服务器。
- 如果用户不勾选保存密码，计划同步依赖 Cookie；Cookie 过期后需要重新手动认证。
- 应用需要访问 Docker 服务、应用共享目录以及用户在应用设置中授权的目录。
- “同步本地删除”只会处理 NAS 本地已同步文件，不会删除 iCloud 云端照片。
- “下载后删除 iCloud 云端”会请求删除 iCloud 云端对应媒体文件，属于高风险手动选项，默认关闭，并在保存和运行同步前要求输入确认文字。

## 使用注意事项

- 首次启动需要等待 Docker 容器、Python 虚拟环境和依赖准备完成。
- 如果启用“下载后删除 iCloud 云端”，请先确认 NAS 文件完整且有额外备份；不建议与相册、资料库、最近天数等过滤条件混用，除非明确知道会影响哪些媒体。
- iCloud 登录可能触发双重认证，用户需要在页面右侧验证码输入框中发送验证码。
- 备忘录导出不是 Apple 官方同步 API，依赖 iCloud Mail 中可访问的 Notes/备忘录 IMAP 文件夹。
- 当前包只提供 x86_64 架构；如果需要适配 ARM 设备，需要重新准备 ARM 可用的 icloudpd 依赖包。
- 应用图标使用 FPK 原始图标配置，桌面入口配置为 `showDesktop=true`、`allUsers=true`、`noDisplay=false`。

## 审核测试建议

1. 在 fnOS 应用中心手动安装 `icloud-sync-0.2.20.fpk`。
2. 启动应用，确认桌面入口可打开启动检测页。
3. 等待容器启动完成，进入 iCloud 同步面板。
4. 打开 `/api/status`，确认 `icloudpd_available` 为 `true`，并能看到 `icloudpd_path`。
5. 在应用设置里确认默认共享目录为 `应用文件/icloud`。
6. 选择一个已授权目录作为同步根目录，保存后重启应用，确认面板显示新目录。
7. 填写 Apple ID，点击认证 iCloud，并按页面提示输入验证码。
8. 勾选照片/视频后运行同步，确认文件写入所选同步根目录。
9. 如需测试备忘录，填写 iCloud IMAP 账号和 App 专用密码，导出 Notes/备忘录文件夹。

## Release 说明

0.2.20 移除了同步面板顶部的依赖状态徽标。进入面板代表 Web 后端已经就绪，页面只保留任务状态，避免后端已运行时仍显示“依赖安装中”造成误解。
