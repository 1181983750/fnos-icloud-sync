# iCloud 同步 FPK

这是一个给飞牛 fnOS 使用的 Docker 型 FPK 应用。安装后会出现「iCloud 同步」桌面入口，打开后可以配置 Apple ID、选择照片/视频/备忘录，并查看同步任务日志。

## 功能

- 照片同步：调用 `icloudpd` 下载 iCloud Photos 照片到应用共享目录。
- 视频同步：可单独下载视频到 `videos` 目录。
- 备忘录导出：实验性 IMAP 导出，保存为 Markdown 或 HTML。
- 2FA 输入：认证时可在面板里发送 Apple 双重认证验证码。
- 计划同步：按分钟间隔自动同步媒体文件。
- 本地持久化：配置、Cookie、日志存在应用数据目录，下载结果存在 `shares/icloud`。
- 多账号目录隔离：每个同步方案都可以设置自己的保存文件夹。
- 目录可选：可在飞牛“应用设置”里把同步根目录切换到本应用已授权的任意目录。
- 云端清理：可选高风险 Move 模式，媒体同步到 NAS 后删除 iCloud 云端对应照片/视频。

## 目录

```text
fnos-icloud-sync/
├── manifest
├── config/
├── wizard/
├── cmd/
├── app/
│   ├── docker/docker-compose.yaml
│   ├── server/
│   └── ui/
└── scripts/
```

## 模块说明

每个源码模块目录都带有独立 `README.md`，用于说明职责、关键文件和维护注意事项。

- `app/`：FPK 运行时应用目录，包含 Docker 服务、后端面板和桌面入口。
- `app/docker/`：fnOS Docker 项目配置，负责启动 Python 容器和挂载数据目录。
- `app/server/`：Flask 后端和 Web 面板静态资源，负责配置、认证、同步任务和状态接口。
- `app/server/static/`：浏览器端页面、样式和交互脚本。
- `app/server/wheels/`：离线 Python wheel 依赖，减少 NAS 首次启动下载等待。
- `app/ui/`：fnOS 桌面入口和启动等待页。
- `app/ui/images/`：桌面入口图标资源。
- `cmd/`：FPK 安装、配置、卸载等生命周期脚本。
- `config/`：FPK 资源、权限和应用共享目录声明。
- `wizard/`：fnOS 安装/配置向导定义。
- `scripts/`：本地构建辅助脚本。
- `tools/`：本地构建工具放置目录。
- `docs/`：上架、限制说明和维护文档。

下载结果安装后位于同步根目录下。每个方案可以设置自己的相对文件夹，例如：

```text
/var/apps/icloud-sync/shares/icloud/<方案文件夹>/photos
/var/apps/icloud-sync/shares/icloud/<方案文件夹>/videos
/var/apps/icloud-sync/shares/icloud/<方案文件夹>/notes
```

## 打包

先下载飞牛官方 `fnpack`，或者把 `FNPACK_BIN` 指到本机的 `fnpack` 可执行文件。

Windows:

```powershell
cd C:\Project\NAS相关\fnos-icloud-sync
.\scripts\build-fpk.ps1
```

Linux/macOS:

```bash
cd /path/to/fnos-icloud-sync
chmod +x scripts/build-fpk.sh
./scripts/build-fpk.sh
```

也可以直接运行：

```bash
fnpack build --directory .
```

成功后会在 `dist/` 里得到当前版本的 `icloud-sync-*.fpk`。

## 使用

1. 在飞牛应用中心手动安装 `.fpk`。
2. 启动应用，首次启动会拉取 `python:3.12-slim` 并安装 `flask`、`icloudpd`。
3. 如果想把文件存到任意位置，先进入飞牛“应用设置”，为本应用授权目录，并在配置向导里选择同步根目录；保存后重启应用。
4. 打开桌面入口「iCloud 同步」。
5. 填写方案名称、Apple ID 和当前方案保存文件夹。
6. 填写密码，点击「认证 iCloud」。
7. 如果日志提示验证码，在输入框填入 6 位验证码并发送。
8. 选择照片/视频/备忘录，保存配置后运行同步。

## 注意

- iCloud 照片/视频使用 `icloudpd==1.32.3`，这是 2026 年 5 月底修复新版 Apple 2FA 流程的版本。
- 默认是 Copy 模式，只下载新增内容，不删除云端文件。
- 「同步本地删除」只会删除 NAS 本地已从 iCloud 移除的文件，不会删除 iCloud 云端照片。
- 「下载后删除 iCloud 云端」会在媒体同步成功后请求删除云端对应照片/视频；这是不可轻易回退的危险操作，启用前请确认 NAS 文件完整并已有其他备份。
- 备忘录没有 Apple 官方稳定第三方同步 API。这里走 IMAP 导出，只在 iCloud Mail 能看到 Notes/备忘录文件夹时有效。
- 如果需要计划同步但不保存 Apple ID 密码，Cookie 过期后需要重新手动认证。
- 若 NAS 无法访问 Docker Hub 或 PyPI，首次启动依赖安装会失败；可改用自建镜像后再调整 `app/docker/docker-compose.yaml`。
