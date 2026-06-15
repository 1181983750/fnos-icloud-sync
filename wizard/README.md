# wizard 模块

`wizard/` 保存 fnOS 安装/配置向导定义。

## 关键文件

- `config`：应用设置页使用的配置项，由 `cmd/config_init` 动态生成。
- `install`：安装向导配置。
- `uninstall`：卸载向导配置。

## 维护注意

- 同步根目录选项来自 `cmd/config_shared.sh` 检测到的授权目录。
- 默认同步根目录应保持为 `/var/apps/icloud-sync/shares/icloud`。
- 修改向导字段名时，需要同步更新 `cmd/config_callback` 和 Docker Compose 变量引用。
