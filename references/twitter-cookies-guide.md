# Twitter Cookie 获取教程

> **重要**：必须在 `x.com` 域名下导出 Cookie（不是 `twitter.com`）。如果从 `twitter.com` 导出，Playwright 拦截可能无法正常工作。

## 前置准备

1. 一个 Twitter/X 账号（建议使用小号，非目标账号本身）
2. Chrome 或 Edge 浏览器
3. 安装 **Cookie-Editor** 浏览器扩展

## 步骤

### 1. 安装 Cookie-Editor

- Chrome Web Store 搜索 "Cookie-Editor"
- 或直接到扩展商店安装

### 2. 登录 Twitter

- 打开 `https://x.com` 并登录你的浏览账号
- 确保能正常访问目标用户的个人页（如 `https://x.com/target_user`）

### 3. 导出 Cookie

1. 在 Twitter 页面上点击 Cookie-Editor 扩展图标
2. 点击右下角的 **Export** 按钮（选择 JSON 格式）
3. Cookie 数据会复制到剪贴板

### 4. 保存 Cookie 文件

1. 在项目的 `cookies/` 目录下创建 `twitter.json`
2. 粘贴 **Cookie-Editor 导出的完整 JSON 数组**（不要只粘贴 3 个 cookie，要粘贴整个数组）
3. 确认文件内容以 `[` 开头、`]` 结尾（是一个 JSON 数组）

### 5. 验证 Cookie

运行验证脚本检查 Cookie 完整性：

```bash
python3 validate_config.py
```

确认输出中显示：
- `auth_token` present
- `ct0` present
- `twid` present
- browsing user ID 正确提取

## 关键 Cookie 说明

| Cookie 名 | 用途 | 必需 |
|-----------|------|------|
| `auth_token` | 登录凭证 | 是 |
| `ct0` | CSRF Token | 是 |
| `twid` | 用户 ID（格式 `u%3D{数字ID}`） | 是 |
| `kdt` | 设备 Token | 否（但建议保留） |
| `guest_id` | 访客 ID | 否 |

## Cookie 过期与刷新

- Twitter Cookie 通常有效 **1 年**（`expirationDate` 字段）
- 如果服务日志出现 `Redirected to login page` 或 `auth error code 32`，说明 Cookie 已过期
- 重新执行上述步骤导出新 Cookie 即可

## 注意事项

- **不要使用目标账号的 Cookie**，使用一个专门的浏览小号
- Cookie 中包含登录凭证，请妥善保管，不要提交到 Git
- 确保 `.gitignore` 中包含 `cookies/` 目录
- 导出时确保是在 `x.com` 域名下导出，而非第三方页面
