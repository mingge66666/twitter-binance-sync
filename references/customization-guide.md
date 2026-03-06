# 自定义扩展指南

## 添加过滤规则

在 `modules/filter.py` 的 `filter_tweet()` 函数中，在 `# PASS` 之前插入新规则：

```python
# F-07: 自定义规则示例 -- 过滤包含特定关键词的推文
if "某关键词" in raw_text:
    logger.debug(f"F-07 drop_keyword: {tweet_id}")
    return False, "drop_keyword", tweet_data
```

规则命名建议：`F-{编号}` 递增，`filter_result` 使用 `drop_` 前缀。

## 换目标平台

替换 `modules/publisher.py` 中的 `publish_to_square()` 函数，保持相同接口即可：

```python
async def publish_to_square(clean_text, api_endpoint, delay=10):
    """
    返回 (success: bool, result: dict)

    result 字典支持的 key:
    - success 时: square_post_id, square_post_url
    - fail 时: error_code, error_msg
    - 特殊标记: halt_today (日限额), halt_permanent (Key 失效), skip_permanent (敏感内容)
    """
    ...
```

例如替换为 Telegram Channel 发布、微博发布等，只需实现这个接口。

## 更换监控账号

如果你想改为同步另一个 Twitter 用户的推文：

1. 修改 `config.yaml` 中的 `twitter.username` 和 `twitter.profile_url`
2. **必须重置游标**，否则服务会用旧账号的推文 ID 做过滤，导致新账号推文全被跳过：

```bash
docker exec twitter-sync python -c "
from modules.db import set_sync_state
set_sync_state('last_tweet_id', '')
print('Cursor reset for new account')
"
docker compose restart
```

> **注意**：重置游标后首次运行只处理当天推文（安全机制），不会回溯发布历史内容。

## 多账号同步

1. 复制整个项目目录
2. 修改 `config.yaml` 中的 `twitter.username` 和 `twitter.profile_url`
3. 修改 `docker-compose.yml` 中的 `container_name`（避免冲突）
4. 使用不同的 `cookies/twitter.json`（可以用同一个浏览账号）
5. 可以共用同一个 Discord 频道，也可以分开

```bash
# 示例：同步第二个账号
cp -r ~/my-sync-project ~/my-sync-project-2
cd ~/my-sync-project-2
# 编辑 config.yaml 改用户名
# 编辑 docker-compose.yml 改容器名为 twitter-sync-2
docker compose up -d --build
```
