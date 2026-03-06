# 故障排查手册

## 错误代码对照表

### Twitter 端

| 错误 | 日志关键词 | 原因 | 解决方案 |
|------|-----------|------|----------|
| Cookie 过期 | `Redirected to login page` | 登录态失效 | 重新导出 Cookie 到 `cookies/twitter.json`，然后 `docker compose restart` |
| 账号限制 | `auth error code 32` | Twitter 临时/永久限制 | 等待解限或更换浏览账号 |
| 账号锁定 | `auth error code 326` | 需要验证 | 手动登录完成验证后重新导出 Cookie |
| 网络错误 | `Network error reaching Twitter` | 当前机器无法访问 x.com | 运行 `curl -sI https://x.com`，如超时则所在地区被封锁，需更换网络环境 |
| 无 XHR 响应 | `No UserTweets XHR captured` | 页面未正常加载 | 检查网络连通性、Twitter 是否可达 |
| Cookie 文件缺失 | `Cookie file not found` | cookies/twitter.json 不存在 | 导出 Cookie 到 `cookies/twitter.json` |
| 目标页 404 | `page.goto` 异常 | 用户名错误或账号被封 | 检查 `config.yaml` 中的用户名 |

### Binance Square 端

| 错误码 | 日志关键词 | 原因 | 解决方案 |
|--------|-----------|------|----------|
| 220009 | `daily limit reached` | 日发帖上限 | 无需处理，午夜自动重置 |
| 220003 | `API key error` | Key 无效 | 重新申请 API Key |
| 220004 | `API key error` | 权限不足 | 联系币安客服 |
| 20002 | `sensitive content` | 内容含敏感词 | 推文自动跳过，无需处理 |
| 20022 | `sensitive content` | 审核未通过 | 同上 |
| 20013 | `content too long` | 超长 | 自动截断重试，通常成功 |

### Discord 端

| 错误 | 日志关键词 | 原因 | 解决方案 |
|------|-----------|------|----------|
| 401 | `Discord API error 401` | Bot Token 无效 | 检查 `.env` 中的 `DISCORD_BOT_TOKEN` |
| 403 | `Discord API error 403` | Bot 无权发消息 | 检查 Bot 在目标频道的权限 |
| 404 | `Discord API error 404` | Channel ID 错误 | 检查 `.env` 中的 `DISCORD_CHANNEL_ID` |

## 常见场景排查

### 场景 1：服务启动正常但不发帖

1. **使用 health_check 快速诊断**
   ```bash
   # 从 skill 包目录运行
   python3 scripts/health_check.py --project-dir ~/twitter-sync
   ```

2. **或手动检查游标位置**
   ```bash
   docker exec twitter-sync python -c "
   from modules.db import get_sync_state
   print('last_tweet_id:', get_sync_state('last_tweet_id'))
   print('halt_today:', get_sync_state('halt_publishing_today'))
   "
   ```
   - 如果 `halt_today = 1`：日限额已触发，等午夜重置
   - 如果游标 ID 很大：所有推文已在游标之前，等新推文

3. **检查过滤结果**
   ```bash
   docker exec twitter-sync python main.py --test
   ```
   看每条推文的 PASS/DROP 状态

### 场景 2：Discord 通知没收到

1. 确认 Bot 已加入服务器且有目标频道的发消息权限
2. 运行测试模式检查：
   ```bash
   docker exec twitter-sync python main.py --test
   ```
3. 查看日志中是否有 Discord 相关错误：
   ```bash
   docker logs twitter-sync 2>&1 | grep -i discord
   ```

### 场景 3：推文内容乱码或截断

1. 检查 `config.yaml` 中 `max_content_length` 设置
2. 查看数据库中的 `content_clean` 字段：
   ```bash
   docker exec twitter-sync python -c "
   import sqlite3
   conn = sqlite3.connect('./db/state.sqlite')
   conn.row_factory = sqlite3.Row
   rows = conn.execute('SELECT tweet_id, content_clean FROM tweets ORDER BY rowid DESC LIMIT 5').fetchall()
   for r in rows:
       print(f'{r[\"tweet_id\"]}: {r[\"content_clean\"][:100]}')
   "
   ```

### 场景 4：重复发帖

正常不应发生（有 F-00 去重）。如果发生：
1. 检查数据库文件是否被意外删除（`db/state.sqlite`）
2. 确认 `docker-compose.yml` 中 `db` volume 已正确挂载

### 场景 5：容器频繁重启

```bash
# 查看退出原因
docker inspect twitter-sync --format='{{.State.ExitCode}}'
docker logs --tail 30 twitter-sync
```

常见原因：
- OOM Kill：在 `docker-compose.yml` 中调大 `deploy.resources.limits.memory` 或升级 VPS
- Python 异常：查看日志修复代码
- 配置错误：运行 `python3 validate_config.py`

### 场景 6：数据库丢失或损坏

如果 `db/state.sqlite` 被意外删除或损坏：

```bash
# 1. 停止服务
docker compose down

# 2. 如果有备份则恢复
cp db/state.sqlite.bak db/state.sqlite

# 3. 如果没有备份，删除损坏文件让服务重建
rm -f db/state.sqlite

# 4. 重新启动（会自动创建新数据库）
docker compose up -d

# 注意：新数据库意味着：
# - 游标重置：首次运行只处理当天推文，不会重复发布历史推文
# - 去重记录丢失：如果当天有已发布的推文，可能重复发布
```

### 场景 7：构建失败

```bash
# 检查磁盘空间
df -h

# 清理 Docker 缓存释放空间
docker system prune -f

# 重新构建
docker compose up -d --build
```

如果是网络问题导致基础镜像拉取失败，参见 `vps-deployment-guide.md` 中的「构建失败排查」部分。

## 数据库维护

### 备份
```bash
cp db/state.sqlite db/state.sqlite.bak
```

### 手动重置游标（谨慎！会重新处理所有推文）
```bash
docker exec twitter-sync python -c "
from modules.db import set_sync_state
set_sync_state('last_tweet_id', '')
print('Cursor reset')
"
docker compose restart
```

### 手动重置日限额
```bash
docker exec twitter-sync python -c "
from modules.db import set_sync_state
set_sync_state('halt_publishing_today', '0')
print('Daily halt reset')
"
```

### 查看推文统计
```bash
docker exec twitter-sync python -c "
from modules.db import get_daily_stats
stats = get_daily_stats()
for k, v in stats.items():
    print(f'{k}: {v}')
"
```
