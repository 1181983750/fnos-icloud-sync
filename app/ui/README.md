# app/ui 模块

`app/ui/` 保存 fnOS 桌面入口配置和启动等待页。

## 关键文件

- `config`：fnOS 桌面入口声明，包含入口标题、图标、URL、桌面显示开关等。
- `index.cgi`：桌面入口打开后的启动检测页，等待后端服务就绪后跳转到 Web 面板。
- `images/`：入口图标资源。

## 维护注意

- 桌面入口当前配置为 `showDesktop=true`、`allUsers=true`、`noDisplay=false`。
- `index.cgi` 需要保持可执行权限，安装脚本会尝试 `chmod +x`。
- 启动页用于避免后端端口未就绪时直接显示浏览器拒绝连接。
