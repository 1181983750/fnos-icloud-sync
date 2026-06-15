# config 模块

`config/` 保存 FPK 资源和权限声明。

## 关键文件

- `resource`：声明 Docker 项目和应用共享目录。
- `privilege`：声明应用运行所需权限。

## 维护注意

- 当前共享目录名称为 `icloud`，对应用户可见路径 `应用文件/icloud`。
- 修改共享目录名时，需要同步更新 `cmd/`、`wizard/`、`app/docker/` 和后端默认路径。
- 权限变更会影响官方审核，需要在上架资料中说明原因。
