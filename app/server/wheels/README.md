# app/server/wheels 模块

`app/server/wheels/` 保存容器首次启动所需的离线 Python wheel 包。

## 作用

- 减少 NAS 首次启动时从 PyPI 下载依赖的等待。
- 避免 `icloudpd` 大文件下载缓慢导致页面长时间显示依赖安装中。

## 当前依赖

- Flask 及其依赖。
- `icloudpd==1.32.3`。

## 维护注意

- 当前 wheel 面向 Linux x86_64 Python 3.12 容器，不适用于 Windows 或 ARM 设备。
- 升级 Python 镜像、`icloudpd` 或目标架构时，需要重新生成对应 wheel。
- 不要删除本目录中的 wheel，除非同步修改 Docker 安装逻辑和打包说明。
