# iCloud 同步 FPK

这是一个给飞牛 `fnOS` 使用的 iCloud 同步应用。安装后桌面会出现「iCloud 同步」入口，打开后就能把 iCloud 照片、视频和备忘录保存到 NAS。

## 它能做什么

- 把 iCloud 照片和视频下载到 NAS
- 支持多个同步方案，不同账号可分开保存
- 支持验证码输入、计划同步、失败自动重试
- 支持导出 iCloud 备忘录
- 支持危险模式：下载完成后删除 iCloud 云端对应媒体

## 适合谁

- 想把 iPhone / iPad 上的照片长期备份到飞牛 NAS
- 想把家人账号、工作账号分开同步
- 想定时自动拉取新照片，不想每次手动下载

## 安装

1. 打开仓库里的 `dist/` 目录，选择最新的 `icloud-sync-*.fpk`。
2. 在飞牛应用中心手动安装这个 `fpk`。
3. 安装完成后，从桌面打开「iCloud 同步」。

## 使用

1. 新建一个同步方案。
2. 填写 Apple ID。
3. 选择当前方案保存文件夹。
4. 按需勾选照片、视频、备忘录。
5. 点击「认证 iCloud」完成登录。
6. 如果页面提示验证码或确认文字，直接在页面下方输入并发送。
7. 保存后开始同步。

## 常用说明

- 默认模式只下载到 NAS，不会删除 iCloud 云端文件。
- 如果你修改了同步根目录，需要在应用中心停止并重新启动应用后才会生效。
- 不同方案可以同时运行；同一个方案一次只会运行一个任务。
- 如果开启“下载后删除 iCloud 云端”，请先确认 NAS 上的文件已经完整保存，并且你自己有额外备份。
- Live Photo、RAW 和同名文件处理都可以在页面里单独设置。

## 打包

如果你只是安装使用，这一节可以跳过。

Windows:

```powershell
cd F:\project\fnos_sync_icloud
.\scripts\build-fpk.ps1
```

Linux / macOS:

```bash
cd /path/to/fnos_sync_icloud
chmod +x scripts/build-fpk.sh
./scripts/build-fpk.sh
```

打包完成后，新的安装包会出现在 `dist/` 目录。

## 目录说明

- `dist/`：已经打好的安装包
- `app/`：应用页面和后端服务
- `scripts/`：本地打包脚本
