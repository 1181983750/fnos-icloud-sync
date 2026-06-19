# app/server/wheels 模块

`app/server/wheels/` 保存应用首次启动时创建虚拟环境所需的离线 Python wheel 包。

## 作用

- 减少 NAS 首次启动时从 PyPI 下载依赖的等待。
- 避免 `icloudpd` 大文件下载缓慢导致页面长时间显示依赖安装中。

## 当前依赖

- Flask 及其依赖。
- `icloudpd==1.32.3`。

## 维护注意

- 当前 wheel 面向 Linux x86_64 Python 3.12，不适用于其他 Python 版本、Windows 或 ARM 设备。
- `cmd/install_init` 会在安装前检查系统里是否存在可用的 Python 3.12 和 `venv` 支持；`cmd/main` 启动时也会做同样校验。
- 升级 Python 版本、`icloudpd` 或目标架构时，需要重新生成对应 wheel。
- 不要删除本目录中的 wheel，除非同步修改 `cmd/main` 的安装逻辑和打包说明。
