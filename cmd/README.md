# cmd 模块

`cmd/` 保存 FPK 生命周期脚本。

## 关键脚本

- `install_callback`：安装后创建配置、日志和默认共享目录。
- `install_init`：安装前检查系统是否有可用的 Python 3.11.x 和 `venv` 支持；缺失时中止安装并提示用户先安装。
- `main`：管理原生 Web 服务，负责创建虚拟环境、安装依赖、启动、停止和状态检查。
- `config_init`：打开应用设置前生成配置向导。
- `config_callback`：保存应用设置后的回调，写入同步根目录配置。
- `config_shared.sh`：配置向导和回调共用的路径选择逻辑。
- `uninstall_callback`：卸载时处理共享目录保留策略。
- `upgrade_*`、`install_*`、`uninstall_*`：fnOS 生命周期入口脚本。

## 维护注意

- 默认同步根目录为 `/var/apps/${TRIM_APPNAME}/shares/icloud`。
- `manifest` 不声明静态 Python 依赖；脚本会优先复用系统自带 Python 3.11.x，避免已有运行时的设备仍被强制提示安装额外依赖。
- 内置 wheel 面向 Linux x86_64 Python 3.11；运行时只接受 Python 3.11.x，避免用其他 Python 版本创建不兼容虚拟环境。
- 旧默认目录 `icloud-photos` 只作为兼容迁移路径识别。
- `config_init` 会把飞牛授权目录生成到应用设置下拉框；保存后 `cmd/main` 会在下次启动时把服务数据目录指向所选宿主目录。
- 脚本应尽量容错并 `exit 0`，避免应用设置页因为非关键错误失败。
