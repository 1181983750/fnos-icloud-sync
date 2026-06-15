# tools 模块

`tools/` 用于放置本地构建工具。

## 常见内容

- `fnpack` 或 `fnpack.exe`：飞牛 FPK 打包工具。

## 维护注意

- `.gitignore` 默认忽略 `tools/fnpack*`，避免把平台相关二进制工具提交到仓库。
- 如果更换 `fnpack` 版本，请在本地验证打包输出和安装效果。
