# 备忘录同步限制

Apple 没有公开稳定的 iCloud Notes 第三方同步 API，因此本应用把「备忘录」实现为 IMAP 导出能力：

- 连接 `imap.mail.me.com`。
- 读取配置的 `Notes` 或 `备忘录` 文件夹。
- 将邮件样式的笔记内容导出为 Markdown 或 HTML。

这适合旧版/邮件侧可见的 Notes 数据，不等同于完整 Apple Notes 数据库同步。若你的 iCloud IMAP 中看不到 Notes 文件夹，应用会在日志里报错，照片和视频同步仍可正常使用。

建议为 IMAP 使用 Apple App 专用密码，不要使用主密码。
