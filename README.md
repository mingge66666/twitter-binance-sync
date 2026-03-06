<div align="center">

<!-- Hero Banner -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1DA1F2,100:F0B90B&height=220&section=header&text=Twitter-Binance-Sync&fontSize=42&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=Auto-sync%20Tweets%20to%20Binance%20Square%20%7C%20%E8%87%AA%E5%8A%A8%E5%90%8C%E6%AD%A5%E6%8E%A8%E6%96%87%E5%88%B0%E5%B8%81%E5%AE%89%E5%B9%BF%E5%9C%BA&descSize=16&descAlignY=55" width="100%"/>

<br/>

<!-- Gold Badges Row -->
<img src="https://img.shields.io/badge/%E2%9C%A8_PRODUCTION-READY-gold?style=for-the-badge" alt="Production Ready"/>
<img src="https://img.shields.io/badge/%F0%9F%94%92_SECURITY-AUDITED-gold?style=for-the-badge" alt="Security Audited"/>
<img src="https://img.shields.io/badge/%F0%9F%9A%80_ZERO_CONFIG-FOR_BEGINNERS-gold?style=for-the-badge" alt="Zero Config"/>

<br/><br/>

<!-- Tech Stack - Big -->
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Playwright](https://img.shields.io/badge/Playwright-1.42-45ba4b?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![SQLite](https://img.shields.io/badge/SQLite-WAL_Mode-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![asyncio](https://img.shields.io/badge/asyncio-Powered-FFD43B?style=for-the-badge&logo=python&logoColor=black)](https://docs.python.org/3/library/asyncio.html)

<!-- Platform Integration -->
[![Binance](https://img.shields.io/badge/Binance_Square-OpenAPI-F0B90B?style=flat-square&logo=binance&logoColor=white)](https://www.binance.com/square)
[![Twitter](https://img.shields.io/badge/Twitter/X-GraphQL-000000?style=flat-square&logo=x&logoColor=white)](https://x.com)
[![Discord](https://img.shields.io/badge/Discord-Alerts-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discord.com)
[![APScheduler](https://img.shields.io/badge/APScheduler-Cron+Interval-FF6B6B?style=flat-square)](https://apscheduler.readthedocs.io)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-blueviolet?style=flat-square)](https://claude.ai)

<!-- Repo Meta - Dynamic -->
[![License](https://img.shields.io/github/license/yansc153/twitter-binance-sync?style=flat-square&color=green)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/yansc153/twitter-binance-sync?style=flat-square&logo=github&color=gold)](https://github.com/yansc153/twitter-binance-sync/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/yansc153/twitter-binance-sync?style=flat-square&logo=github)](https://github.com/yansc153/twitter-binance-sync/network)
[![GitHub last commit](https://img.shields.io/github/last-commit/yansc153/twitter-binance-sync?style=flat-square&color=blue)](https://github.com/yansc153/twitter-binance-sync/commits)
[![GitHub repo size](https://img.shields.io/github/repo-size/yansc153/twitter-binance-sync?style=flat-square)](https://github.com/yansc153/twitter-binance-sync)
[![GitHub issues](https://img.shields.io/github/issues/yansc153/twitter-binance-sync?style=flat-square)](https://github.com/yansc153/twitter-binance-sync/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](https://github.com/yansc153/twitter-binance-sync/pulls)

<br/>

> **🐦 → 🟡 One command to deploy. Zero code to write. Just provide your keys.**
>
> **🐦 → 🟡 一键部署，零代码，只需提供你的密钥。**

<br/>

[English](#english) | [中文](#中文)

---

</div>

## English

### What is this?

A Claude Code skill that automatically syncs tweets from any Twitter/X account to Binance Square. Just tell Claude Code "sync my tweets to Binance Square" and it handles everything.

### Features

| Feature | Description |
|---------|-------------|
| **Smart Filtering** | 7-layer filter chain — skips videos, retweets, replies, threads, image-only, and empty tweets |
| **Auto Retry** | Failed posts are queued and retried automatically (up to 3 times) |
| **Deduplication** | SQLite-backed cursor ensures no tweet is posted twice |
| **Rate Limit Aware** | Detects Binance daily limits, pauses until midnight reset |
| **Discord Alerts** | Optional real-time notifications + daily digest reports |
| **Docker Deploy** | One-command deployment with Playwright pre-configured |

### Architecture

```
Twitter Profile
     │
     ▼
 [Fetcher]  ─── Playwright XHR interception (UserTweets GraphQL)
     │
     ▼
 [Filter]   ─── F-00~F-06 seven-layer filter chain
     │
     ▼
 [Processor] ── Strip URLs, normalize whitespace, truncate
     │
     ▼
 [Publisher] ── Binance Square OpenAPI POST
     │
     ▼
 [DB]       ─── SQLite state persistence (cursor / dedup / retry queue)
     │
     ▼
 [Notifier] ── Discord Bot alerts + daily report
     │
     ▼
 [Scheduler] ─ APScheduler loop (60min + jitter)
```

### What You Need

| Item | Required | How to Get |
|------|----------|------------|
| Twitter username to sync | Yes | The @handle you want to monitor |
| Binance Square API Key | Yes | [Guide](references/binance-api-guide.md) — requires creator status (24-48h approval) |
| Twitter Cookie (JSON) | Yes | [Guide](references/twitter-cookies-guide.md) — exported via Cookie-Editor extension |
| Discord Bot Token | No | [Guide](references/discord-bot-guide.md) — for optional notifications |

### Quick Start

> **For Claude Code users**: Just say "帮我把推文同步到币安广场" or "deploy twitter-binance-sync" — Claude will guide you through everything step by step.

**Manual setup:**

```bash
# 1. Generate project
python3 scripts/init_project.py \
  --twitter-username TARGET_HANDLE \
  --output-dir ~/twitter-sync

# 2. Configure credentials
cd ~/twitter-sync
# Edit .env with your API key
# Copy Cookie-Editor export to cookies/twitter.json

# 3. Validate & deploy
python3 validate_config.py
docker compose up -d --build

# 4. Test (dry run, no actual posting)
docker exec twitter-sync python main.py --test
```

### Project Structure

```
twitter-binance-sync/
├── SKILL.md                    # Skill definition (Claude reads this)
├── README.md                   # You are here
├── scripts/
│   ├── init_project.py         # Project scaffolding
│   ├── validate_config.py      # Pre-deploy validation
│   └── health_check.py         # Runtime diagnostics
├── references/
│   ├── architecture.md         # Pipeline deep-dive
│   ├── twitter-cookies-guide.md
│   ├── binance-api-guide.md
│   ├── discord-bot-guide.md
│   ├── vps-deployment-guide.md
│   ├── troubleshooting.md
│   └── customization-guide.md
└── assets/templates/           # Complete deployable project
    ├── main.py
    ├── config.yaml.template
    ├── .env.template
    ├── Dockerfile
    ├── docker-compose.yml
    ├── validate_config.py
    └── modules/
        ├── fetcher.py          # Playwright tweet fetcher
        ├── filter.py           # 7-layer filter chain
        ├── processor.py        # Text cleanup
        ├── publisher.py        # Binance Square API
        ├── db.py               # SQLite persistence
        ├── scheduler.py        # Sync orchestration
        └── notifier.py         # Discord notifications
```

### Documentation

| Document | Description |
|----------|-------------|
| [Architecture](references/architecture.md) | Data flow, SQLite schema, state machine, cursor mechanism |
| [Twitter Cookies Guide](references/twitter-cookies-guide.md) | How to export cookies with Cookie-Editor |
| [Binance API Guide](references/binance-api-guide.md) | API key setup, endpoints, error codes |
| [Discord Bot Guide](references/discord-bot-guide.md) | Bot creation and channel setup |
| [Deployment Guide](references/vps-deployment-guide.md) | Docker installation and deployment |
| [Troubleshooting](references/troubleshooting.md) | Error codes, common scenarios, database maintenance |
| [Customization](references/customization-guide.md) | Add filters, change platforms, multi-account |

---

## 中文

### 这是什么？

一个 Claude Code 技能包，自动将任意 Twitter/X 账号的推文同步到币安广场。只需对 Claude Code 说"帮我把推文同步到币安广场"，它会全自动帮你完成配置和部署。

### 功能特性

| 功能 | 说明 |
|------|------|
| **智能过滤** | 七层过滤链 —— 自动跳过视频、转推、回复、线程、纯图、空内容 |
| **自动重试** | 发布失败的推文自动排队重试（最多 3 次） |
| **去重机制** | SQLite 游标保证不会重复发帖 |
| **限额感知** | 检测到币安日发帖上限后自动暂停，午夜重置 |
| **Discord 告警** | 可选的实时通知 + 每日同步报告 |
| **Docker 部署** | 一条命令部署，Playwright 已预配置 |

### 架构

```
Twitter 用户主页
     │
     ▼
 [抓取器]  ─── Playwright XHR 拦截（UserTweets GraphQL）
     │
     ▼
 [过滤器]  ─── F-00~F-06 七层过滤链
     │
     ▼
 [处理器]  ─── 去除 URL、规范化空白、截断
     │
     ▼
 [发布器]  ─── 币安广场 OpenAPI POST
     │
     ▼
 [数据库]  ─── SQLite 状态持久化（游标/去重/重试队列）
     │
     ▼
 [通知器]  ─── Discord Bot 告警 + 每日报告
     │
     ▼
 [调度器]  ─── APScheduler 定时循环（60分钟 + 抖动）
```

### 你需要准备什么

| 项目 | 必需 | 获取方式 |
|------|------|----------|
| 要同步的 Twitter 用户名 | 是 | 你想监控的 @用户名 |
| 币安广场 API Key | 是 | [教程](references/binance-api-guide.md) — 需先成为广场创作者（审批 24-48 小时） |
| Twitter Cookie（JSON） | 是 | [教程](references/twitter-cookies-guide.md) — 通过 Cookie-Editor 浏览器扩展导出 |
| Discord Bot Token | 否 | [教程](references/discord-bot-guide.md) — 用于可选的通知功能 |

### 快速开始

> **Claude Code 用户**：直接说"帮我把推文同步到币安广场"或"deploy twitter-binance-sync"，Claude 会一步步引导你完成所有操作。你只需要回答几个问题，不需要手动输入任何命令。

**手动配置：**

```bash
# 1. 生成项目
python3 scripts/init_project.py \
  --twitter-username 目标用户名 \
  --output-dir ~/twitter-sync

# 2. 配置凭证
cd ~/twitter-sync
# 编辑 .env 填入 API Key
# 将 Cookie-Editor 导出的 JSON 复制到 cookies/twitter.json

# 3. 校验并部署
python3 validate_config.py
docker compose up -d --build

# 4. 测试（不实际发帖）
docker exec twitter-sync python main.py --test
```

### 文档

| 文档 | 说明 |
|------|------|
| [架构说明](references/architecture.md) | 数据流、SQLite Schema、状态机、游标机制 |
| [Twitter Cookie 教程](references/twitter-cookies-guide.md) | Cookie-Editor 导出步骤 |
| [币安 API 教程](references/binance-api-guide.md) | API Key 申请、接口说明、错误码 |
| [Discord Bot 教程](references/discord-bot-guide.md) | Bot 创建和频道配置 |
| [部署教程](references/vps-deployment-guide.md) | Docker 安装和部署流程 |
| [故障排查](references/troubleshooting.md) | 错误码对照表、常见场景、数据库维护 |
| [自定义扩展](references/customization-guide.md) | 添加过滤规则、换平台、多账号 |

---

<div align="center">

<br/>

## ⭐ Star History

<a href="https://star-history.com/#yansc153/twitter-binance-sync&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=yansc153/twitter-binance-sync&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=yansc153/twitter-binance-sync&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=yansc153/twitter-binance-sync&type=Date" width="700" />
  </picture>
</a>

<br/><br/>

**If this project helps you, please give it a Star** ⭐ **it means a lot!**

**如果这个项目对你有帮助，请点个 Star** ⭐ **这对我很重要！**

<br/>

<img src="https://img.shields.io/badge/Made_with-%E2%9D%A4%EF%B8%8F-red?style=for-the-badge" alt="Made with love"/>
<img src="https://img.shields.io/badge/Powered_by-Claude_Code-blueviolet?style=for-the-badge" alt="Powered by Claude Code"/>
<img src="https://img.shields.io/badge/3x_Security-Audited-gold?style=for-the-badge" alt="3x Audited"/>

<br/><br/>

<!-- Footer Wave -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1DA1F2,100:F0B90B&height=100&section=footer" width="100%"/>

</div>
