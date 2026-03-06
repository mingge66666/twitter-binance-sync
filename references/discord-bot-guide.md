# Discord Bot 创建与配置教程

## 前置准备

1. 一个 Discord 账号
2. 一个你有管理权限的 Discord 服务器

## 步骤

### 1. 创建 Discord Application

1. 打开 Discord Developer Portal: `https://discord.com/developers/applications`
2. 点击 **New Application**
3. 输入名称（如 "Twitter Sync Bot"）并创建

### 2. 创建 Bot

1. 在左侧菜单选择 **Bot**
2. 点击 **Add Bot**
3. 在 **TOKEN** 部分点击 **Reset Token** 获取 Bot Token
4. 复制并保存 Token（只显示一次！）

### 3. 配置 Bot 权限

在 Bot 页面：
- 确保 `Send Messages` 权限开启
- 滚动到 **Privileged Gateway Intents** 部分，开启 **Message Content Intent**（否则 Bot 可能无法读取消息内容）

### 4. 邀请 Bot 到服务器

1. 左侧菜单选择 **OAuth2** → **URL Generator**
2. Scopes 勾选 `bot`
3. Bot Permissions 勾选 `Send Messages`
4. 复制生成的 URL，在浏览器中打开
5. 选择目标服务器并授权

### 5. 获取 Channel ID

1. 在 Discord 中打开设置 → **高级** → 开启 **开发者模式**
2. 右键点击你想接收通知的频道
3. 点击 **复制频道 ID**

### 6. 配置到项目

编辑 `.env` 文件：

```
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
```

### 7. 测试

部署后运行测试模式，检查 Discord 频道是否收到消息：

```bash
docker exec twitter-sync python main.py --test
```

你应该在频道中看到一条测试消息。

## 通知说明

服务会发送以下类型的通知：

| 图标 | 级别 | 触发场景 |
|------|------|----------|
| 🔴 | CRITICAL | Cookie 过期、API Key 失效 |
| 🟠 | ERROR | 推文发布永久失败、同步崩溃 |
| 🟡 | WARNING | 日限额、敏感内容 |
| 🔵 | INFO | 服务启动、测试、日报 |

## 注意事项

- Bot Token 是敏感凭证，不要公开分享
- **如果 Token 丢失**，回到 Developer Portal → Bot → **Reset Token** 生成新的（旧 Token 立即失效）
- 建议创建专用频道接收通知，避免干扰其他对话
- 如果 Bot 无法发消息，检查频道权限设置
- Discord API 有频率限制，服务已内置重试和队列机制
- Discord 通知是可选功能——不配置 `DISCORD_BOT_TOKEN` 和 `DISCORD_CHANNEL_ID` 服务仍然正常运行，只是没有告警和日报
