---
name: twitter-binance-sync
description: "This skill should be used when the user wants to set up, deploy, configure, or troubleshoot a Twitter/X to Binance Square auto-sync pipeline. Common triggers: sync tweets to Binance Square, deploy twitter-binance-sync, configure Binance Square auto-posting, troubleshoot tweet sync, Twitter to Binance automation, 推文自动发布到币安, Twitter 同步到币安广场."
---

# Twitter-Binance-Sync Skill

自动将 Twitter/X 推文同步到币安广场（Binance Square）的管道服务。支持过滤、去重、失败重试、Discord 通知，Docker 一键部署。

```
Twitter Profile → [Fetcher] → [Filter] → [Processor] → [Publisher] → Binance Square
                     ↓            ↓                          ↓
               Playwright    F-00~F-06                   OpenAPI POST
               XHR 拦截      七层过滤                    ↓
                                                   [DB] SQLite 持久化
                                                   [Notifier] Discord 告警
                                                   [Scheduler] 60min 循环
```

## 用户需要提供的信息

部署此服务需要向用户收集以下信息。**逐项询问**，不要一次全部要求。用户可能完全不懂技术，用简单中文引导。

### 必需（3 项）

| # | 要问的 | 怎么问用户 | 用户还没有时怎么办 |
|---|--------|-----------|-------------------|
| 1 | **Twitter 用户名** | "你想同步哪个 Twitter 账号的推文？给我他的用户名（@后面的部分）" | 无——用户必须知道 |
| 2 | **Binance Square API Key** | "你有币安广场的 API Key 吗？" | 引导用户按 `references/binance-api-guide.md` 申请。**注意：需先成为广场创作者，审批可能要 24-48 小时**，这期间无法继续，告知用户等审批通过后再来 |
| 3 | **Twitter Cookie JSON 文件** | "你需要用浏览器导出 Twitter 的 Cookie。我来一步步教你" | 按 `references/twitter-cookies-guide.md` 逐步引导用户操作 Cookie-Editor 导出。用户完成后让他把文件路径给你，或直接把内容粘贴给你 |

### 可选（1 项）

| # | 要问的 | 怎么问用户 | 用户说不要时 |
|---|--------|-----------|-------------|
| 4 | **Discord 通知** | "你想收到 Discord 通知吗？（服务异常告警、每日同步报告）如果不需要可以跳过" | 跳过，服务正常运行，只是没有通知。如果要，按 `references/discord-bot-guide.md` 引导用户创建 Bot 并提供 Token + Channel ID |

## 你（Claude）要自动完成的操作

收集到上述信息后，按以下步骤执行。**所有步骤由你完成，不要让用户手动操作命令行。**

### Step 1: 环境检查

```bash
# 检查 Python
python3 --version

# 检查 Docker（如未安装，自动安装）
docker --version || (curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER)
docker compose version

# 检查网络连通性
curl -sI --max-time 10 https://x.com | head -1
curl -sI --max-time 10 https://www.binance.com | head -1
```

如果网络检查失败（超时或被拦截），**停止部署**，告知用户："当前机器无法访问 Twitter 或币安，可能是地区网络限制。需要更换一台能访问这两个网站的机器。"

### Step 2: 生成项目

```bash
cd skills/twitter-binance-sync
python3 scripts/init_project.py \
  --twitter-username {用户提供的用户名} \
  --output-dir ~/twitter-sync
```

### Step 3: 写入凭证

```bash
cd ~/twitter-sync
```

将用户提供的 API Key 写入 `.env`：
```
BINANCE_SQUARE_API_KEY={用户提供的 Key}
DISCORD_BOT_TOKEN={如有}
DISCORD_CHANNEL_ID={如有}
```

将用户提供的 Cookie JSON 写入 `cookies/twitter.json`。
- 如果用户给了文件路径：`cp {路径} cookies/twitter.json`
- 如果用户粘贴了内容：直接写入文件

### Step 4: 校验

```bash
python3 validate_config.py
```

如果有 FAIL 项，根据提示自动修复或询问用户补充信息。常见问题：
- Cookie 过期 → 让用户重新导出
- Cookie 是 twitter.com 域名 → 让用户在 x.com 上重新导出
- 占位符未替换 → 检查 init_project.py 是否正确执行

### Step 5: 构建部署

```bash
docker compose up -d --build
```

> 首次构建需下载 ~1.5GB Playwright 镜像，可能需要 10-20 分钟。告知用户正在构建中请稍候。

### Step 6: 验证

```bash
# 确认容器运行中
docker ps --filter name=twitter-sync

# 运行测试（不实际发帖）
docker exec twitter-sync python main.py --test
```

测试通过后，告诉用户：
- "部署完成！服务每 60 分钟自动同步一次新推文到你的币安广场。"
- "只同步原创文字推文，视频/转推/回复会自动过滤掉。"
- "如果推文触发币安敏感词检测会自动跳过，不影响其他推文。"
- 如果配了 Discord："你的 Discord 频道会收到每日同步报告和异常告警。"

## 故障排查

当用户报告问题时，先运行诊断：

```bash
# 快速诊断
python3 scripts/health_check.py --project-dir ~/twitter-sync

# 或查看日志
docker logs --tail 50 twitter-sync
```

| 现象 | 原因 | 你应该做什么 |
|------|------|-------------|
| `Cookie file not found` | Cookie 文件丢失 | 让用户重新导出 Cookie，你写入 `cookies/twitter.json` |
| `Redirected to login page` | Cookie 过期 | 同上 |
| `Network error reaching Twitter` | 机器无法访问 x.com | 告知用户网络限制问题 |
| `auth error code 32` | Twitter 账号被限制 | 让用户换一个浏览小号重新导出 Cookie |
| `API key error 220003` | Key 无效 | 让用户重新检查/申请 Key |
| `daily limit 220009` | 日发帖上限 | 告知用户"今天发帖已达上限，明天会自动恢复，无需操作" |
| 容器不存在或退出 | 启动失败 | 运行 `docker logs twitter-sync` 查看原因，对应修复 |

详细排查参见 `references/troubleshooting.md`。

## 参考配置（通常不需要用户改动）

以下配置使用合理默认值，仅当用户明确要求调整时才修改。

### config.yaml 可调参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `scheduler.interval_minutes` | `60` | 同步频率（分钟） |
| `scheduler.jitter_minutes` | `5` | 随机抖动（分钟） |
| `binance_square.inter_request_delay_seconds` | `10` | 发帖间隔（秒） |
| `binance_square.max_content_length` | `900` | 最大内容长度 |
| `limits.max_retries` | `3` | 失败重试次数 |

### 过滤规则（自动生效，无需配置）

| 代号 | 说明 |
|------|------|
| F-00 `dedup` | 已发布的不重复发 |
| F-01 `drop_video` | 币安广场不支持视频，跳过 |
| F-02 `drop_rt` | 跳过转推，只同步原创 |
| F-03 `drop_reply` | 跳过回复 |
| F-04 `drop_thread` | 跳过线程续帖 |
| F-05 `drop_image_only` | 跳过纯图无文字 |
| F-06 `drop_empty` | 跳过空内容 |

## 日常运维命令

```bash
# 查看日志
docker logs -f --tail 100 twitter-sync

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 健康检查
python3 scripts/health_check.py --project-dir ~/twitter-sync
```

## 进阶扩展

详见 `references/customization-guide.md`：添加过滤规则、换目标平台、多账号同步、更换监控账号。
详见 `references/architecture.md`：管道数据流、SQLite Schema、状态机、游标机制。
