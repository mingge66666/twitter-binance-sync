# 管道架构说明

## 数据流

```
                    Twitter Profile Page
                           |
                    [Playwright Browser]
                           |
                  XHR 拦截 UserTweets GraphQL
                           |
                    ┌──────┴──────┐
                    │  raw tweets  │  (JSON objects)
                    └──────┬──────┘
                           |
                    [Filter Chain]
                    F-00: 去重 (SQLite)
                    F-01: 视频/GIF
                    F-02: 转推
                    F-03: 他人回复
                    F-04: 自回复/线程
                    F-05: 纯图无字
                    F-06: 空正文
                           |
                    ┌──────┴──────┐
                    │ passed tweets│
                    └──────┬──────┘
                           |
                    [Processor]
                    去 URL → 规范空白 → 截断
                           |
                    ┌──────┴──────┐
                    │  clean text  │
                    └──────┬──────┘
                           |
                    [Publisher]
                    POST → Binance Square OpenAPI
                           |
                    ┌──────┴──────┐
                    │   result     │
                    └──────┬──────┘
                           |
              ┌────────────┼────────────┐
              │            │            │
           success      fail         halt
              │            │            │
        status=published  retry_count++ halt_today=1
        save post URL     save error    暂停至午夜
```

## SQLite Schema

### tweets 表

| 字段 | 类型 | 说明 |
|------|------|------|
| tweet_id | TEXT PK | Twitter 推文 ID |
| content_raw | TEXT | 原始推文文本 |
| content_clean | TEXT | 处理后文本 |
| has_images | INTEGER | 是否含图 (0/1) |
| has_video | INTEGER | 是否含视频 (0/1) |
| tweet_type | TEXT | original/retweet/reply/thread_continuation |
| filter_result | TEXT | pass/dedup/drop_video/drop_rt/... |
| fetched_at | TEXT | 抓取时间 (ISO 8601, UTC+8) |
| status | TEXT | pending/published/failed/dead/skipped |
| retry_count | INTEGER | 重试次数 |
| published_at | TEXT | 发布时间 |
| square_post_id | TEXT | 币安广场帖子 ID |
| square_post_url | TEXT | 币安广场帖子 URL |
| error_code | TEXT | 错误码 |
| error_msg | TEXT | 错误信息 |

### sync_state 表

| key | 说明 |
|-----|------|
| last_tweet_id | 游标：最近处理的最大 tweet_id |
| last_run_at | 最近一次运行时间 |
| halt_publishing_today | "1" 表示今日已触发日限额 |
| daily_publish_count | 今日发布计数 |
| daily_count_date | 计数日期 |

### run_logs 表

记录每次同步周期的统计：fetched_count、passed_filter、published_count、failed_count、retried_count、skipped_count、duration_seconds、error_summary。

## 状态机

```
              ┌──── pending ────┐
              │                 │
              v                 │
         [publish]              │
          /     \               │
         v       v              │
    published   failed ──retry──┘
                  │
                  v (retry_count >= max_retries)
                 dead

    skipped ← filter drop / sensitive content
```

## 游标机制

- 使用 Twitter 推文 ID（snowflake ID，单调递增）作为游标
- 每轮结束时记录本轮最大 tweet_id 到 `sync_state.last_tweet_id`
- 下轮只处理 ID > last_tweet_id 的推文
- 首次运行（无游标）时只处理当天的推文，避免历史数据洪泛

## 调度策略

- 主循环：每 60 分钟 ± 5 分钟抖动（APScheduler interval job）
- 每轮开始先处理重试队列、刷 Discord 消息队列
- 每日 21:00 UTC+8 发送日报
- 每日 00:00 UTC+8 重置日限额标志
