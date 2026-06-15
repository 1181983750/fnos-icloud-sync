# scripts 模块

`scripts/` 保存本地构建辅助脚本。

## 关键脚本

- `build-fpk.ps1`：Windows 下调用 `fnpack` 构建 FPK，并把产物移动到 `dist/`。
- `build-fpk.sh`：Linux/macOS 下调用 `fnpack` 构建 FPK。

## 维护注意

- `build-fpk.ps1` 会根据 `manifest` 中的 `appname` 和 `version` 命名输出包。
- 发布前应确认 `dist/` 只保留最新版本 FPK。
- 如果本机没有全局 `fnpack`，可通过 `FNPACK_BIN` 指定路径。
