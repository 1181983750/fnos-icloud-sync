# cmd 模块

`cmd/` 保存 FPK 生命周期脚本。

## 关键脚本

- `install_callback`：安装后创建配置、日志和默认共享目录。
- `config_init`：打开应用设置前生成配置向导。
- `config_callback`：保存应用设置后的回调，写入同步根目录配置。
- `config_shared.sh`：配置向导和回调共用的路径选择逻辑。
- `uninstall_callback`：卸载时处理共享目录保留策略。
- `upgrade_*`、`install_*`、`uninstall_*`：fnOS 生命周期入口脚本。

## 维护注意

- 默认同步根目录为 `/var/apps/${TRIM_APPNAME}/shares/icloud`。
- 旧默认目录 `icloud-photos` 只作为兼容迁移路径识别。
- `config_init` 会把飞牛授权目录生成到应用设置下拉框；保存后由 Docker Compose 把所选宿主目录挂载到容器 `/data`。
- 脚本应尽量容错并 `exit 0`，避免应用设置页因为非关键错误失败。
