<div align="center">

<!-- Hero Banner -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1DA1F2,50:6C5CE7,100:F0B90B&height=250&section=header&text=Twitter-Binance-Sync&fontSize=48&fontColor=ffffff&animation=twinkling&fontAlignY=32&desc=🐦%20Auto-sync%20Tweets%20to%20Binance%20Square%20%F0%9F%9F%A1&descSize=20&descAlignY=52" width="100%"/>

<br/>

<!-- Typing SVG -->
<a href="https://github.com/yansc153/twitter-binance-sync">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3000&pause=1000&color=F0B90B&center=true&vCenter=true&multiline=true&repeat=true&width=600&height=80&lines=%F0%9F%9A%80+One+command+to+deploy.+Zero+code+to+write.;%F0%9F%94%91+Just+provide+your+keys%2C+we+handle+the+rest." alt="Typing SVG" />
</a>

<br/><br/>

<!-- Gold Certification Badges -->
<img src="https://img.shields.io/badge/%E2%9C%A8_PRODUCTION-READY-C9A84C?style=for-the-badge&labelColor=2B2B2B" alt="Production Ready"/>
&nbsp;
<img src="https://img.shields.io/badge/%F0%9F%94%92_3x_SECURITY-AUDITED-C9A84C?style=for-the-badge&labelColor=2B2B2B" alt="Security Audited"/>
&nbsp;
<img src="https://img.shields.io/badge/%F0%9F%8E%AF_ZERO_CONFIG-FOR_BEGINNERS-C9A84C?style=for-the-badge&labelColor=2B2B2B" alt="Zero Config"/>

<br/><br/>

<!-- Tech Stack -->
<img src="https://skillicons.dev/icons?i=python,docker,sqlite,discord&theme=dark" alt="Tech Stack" height="45"/>

<br/><br/>

<!-- Shields - Tech -->
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose_v2-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Playwright](https://img.shields.io/badge/Playwright-1.42-45ba4b?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev)
[![SQLite](https://img.shields.io/badge/SQLite-WAL_Mode-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![asyncio](https://img.shields.io/badge/asyncio-Native-FFD43B?style=flat-square&logo=python&logoColor=black)](https://docs.python.org/3/library/asyncio.html)
[![Binance](https://img.shields.io/badge/Binance_Square-OpenAPI-F0B90B?style=flat-square&logo=binance&logoColor=white)](https://www.binance.com/square)
[![Twitter](https://img.shields.io/badge/Twitter/X-GraphQL-000000?style=flat-square&logo=x&logoColor=white)](https://x.com)
[![Discord](https://img.shields.io/badge/Discord-Bot_API-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discord.com)

<!-- Shields - Repo -->
[![License](https://img.shields.io/github/license/yansc153/twitter-binance-sync?style=flat-square&color=green)](LICENSE)
[![Stars](https://img.shields.io/github/stars/yansc153/twitter-binance-sync?style=flat-square&logo=github&color=gold)](https://github.com/yansc153/twitter-binance-sync/stargazers)
[![Forks](https://img.shields.io/github/forks/yansc153/twitter-binance-sync?style=flat-square&logo=github)](https://github.com/yansc153/twitter-binance-sync/network)
[![Issues](https://img.shields.io/github/issues/yansc153/twitter-binance-sync?style=flat-square)](https://github.com/yansc153/twitter-binance-sync/issues)
[![Last Commit](https://img.shields.io/github/last-commit/yansc153/twitter-binance-sync?style=flat-square&color=blue)](https://github.com/yansc153/twitter-binance-sync/commits)
[![Repo Size](https://img.shields.io/github/repo-size/yansc153/twitter-binance-sync?style=flat-square)](https://github.com/yansc153/twitter-binance-sync)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](https://github.com/yansc153/twitter-binance-sync/pulls)

<br/>

---

**[English](#-english)** &nbsp;&bull;&nbsp; **[中文](#-中文)**

---

</div>

<br/>

## 🇺🇸 English

<div align="center">

### 💬 Just say this to Claude Code:

```
"Help me sync my tweets to Binance Square"
```

**That's it. Claude handles everything else.**

</div>

<br/>

### ✨ Features

<table>
<tr>
<td width="50%">

#### 🧠 Smart Filtering
7-layer filter chain automatically skips:
- ❌ Videos & GIFs (unsupported by Binance)
- ❌ Retweets (only original content)
- ❌ Replies & thread continuations
- ❌ Image-only & empty tweets

</td>
<td width="50%">

#### 🔄 Auto Retry & Dedup
- 🔁 Failed posts queued for retry (max 3x)
- 🔒 SQLite cursor-based deduplication
- ⏸️ Auto-pause on Binance daily limit
- 🕛 Auto-resume at midnight

</td>
</tr>
<tr>
<td width="50%">

#### 🐳 One-Command Deploy
```bash
docker compose up -d --build
```
- Playwright pre-installed
- Non-root container (security)
- Auto log rotation
- Memory-limited (768MB)

</td>
<td width="50%">

#### 🔔 Discord Notifications
- 🔴 Critical: Cookie expired, API key error
- 🟠 Error: Permanent publish failure
- 🟡 Warning: Daily limit, sensitive content
- 🔵 Info: Daily digest report

</td>
</tr>
</table>

### 🏗️ Architecture

```mermaid
graph LR
    A[🐦 Twitter/X] -->|Playwright XHR| B[Fetcher]
    B -->|Raw Tweets| C[Filter]
    C -->|7-Layer Chain| D[Processor]
    D -->|Clean Text| E[Publisher]
    E -->|OpenAPI POST| F[🟡 Binance Square]

    G[(SQLite DB)] ---|Cursor & Dedup| B
    G ---|Status & Retry| E
    H[📢 Discord] ---|Alerts & Digest| E
    I[⏰ Scheduler] ---|60min Loop| B

    style A fill:#1DA1F2,color:#fff
    style F fill:#F0B90B,color:#000
    style G fill:#003B57,color:#fff
    style H fill:#5865F2,color:#fff
```

### 🔑 What You Need

| | Item | Required | How to Get |
|---|------|:--------:|------------|
| 🐦 | **Twitter Username** | ✅ | The @handle you want to monitor |
| 🟡 | **Binance Square API Key** | ✅ | [Guide →](references/binance-api-guide.md) &nbsp; ⏱️ Creator approval: 24-48h |
| 🍪 | **Twitter Cookie (JSON)** | ✅ | [Guide →](references/twitter-cookies-guide.md) &nbsp; 🔧 via Cookie-Editor |
| 💬 | **Discord Bot Token** | ❌ | [Guide →](references/discord-bot-guide.md) &nbsp; Optional notifications |

### 🚀 Quick Start

> [!TIP]
> **Claude Code users**: Just say *"帮我把推文同步到币安广场"* — Claude will ask you 3 questions and handle everything automatically. No commands needed.

<details>
<summary><b>📋 Manual Setup (click to expand)</b></summary>

```bash
# 1. Generate project
python3 scripts/init_project.py \
  --twitter-username TARGET_HANDLE \
  --output-dir ~/twitter-sync

# 2. Configure credentials
cd ~/twitter-sync
# Edit .env → add your Binance API Key
# Copy Cookie-Editor export → cookies/twitter.json

# 3. Validate & deploy
python3 validate_config.py
docker compose up -d --build

# 4. Test (dry run, no actual posting)
docker exec twitter-sync python main.py --test
```

</details>

### 📁 Project Structure

<details>
<summary><b>Click to expand</b></summary>

```
twitter-binance-sync/
├── 📄 SKILL.md                    # Skill definition (Claude reads this)
├── 📖 README.md                   # You are here
├── 📜 LICENSE                     # MIT License
├── 🔧 scripts/
│   ├── init_project.py            # Project scaffolding
│   ├── validate_config.py         # Pre-deploy validation
│   └── health_check.py            # Runtime diagnostics
├── 📚 references/
│   ├── architecture.md            # Pipeline deep-dive
│   ├── twitter-cookies-guide.md   # Cookie export tutorial
│   ├── binance-api-guide.md       # API key setup
│   ├── discord-bot-guide.md       # Bot creation
│   ├── vps-deployment-guide.md    # Docker deployment
│   ├── troubleshooting.md         # Error codes & fixes
│   └── customization-guide.md     # Extend & customize
└── 📦 assets/templates/           # Complete deployable project
    ├── main.py                    # Entry point
    ├── Dockerfile                 # Non-root container
    ├── docker-compose.yml         # Orchestration
    └── modules/                   # Pipeline modules
        ├── fetcher.py             # Playwright tweet fetcher
        ├── filter.py              # 7-layer filter chain
        ├── processor.py           # Text cleanup
        ├── publisher.py           # Binance Square API
        ├── db.py                  # SQLite persistence
        ├── scheduler.py           # Sync orchestration
        └── notifier.py            # Discord notifications
```

</details>

### 📚 Documentation

| | Document | Description |
|---|----------|-------------|
| 🏗️ | [Architecture](references/architecture.md) | Data flow, SQLite schema, state machine, cursor |
| 🍪 | [Twitter Cookies](references/twitter-cookies-guide.md) | Cookie-Editor export walkthrough |
| 🟡 | [Binance API](references/binance-api-guide.md) | Key setup, endpoints, error codes |
| 💬 | [Discord Bot](references/discord-bot-guide.md) | Bot creation & channel config |
| 🐳 | [Deployment](references/vps-deployment-guide.md) | Docker install & deploy |
| 🔧 | [Troubleshooting](references/troubleshooting.md) | 7 common scenarios & fixes |
| ⚙️ | [Customization](references/customization-guide.md) | Filters, platforms, multi-account |

---

<br/>

## 🇨🇳 中文

<div align="center">

### 💬 对 Claude Code 说一句话就行：

```
"帮我把推文同步到币安广场"
```

**就这样。Claude 会帮你搞定一切。**

</div>

<br/>

### ✨ 功能特性

<table>
<tr>
<td width="50%">

#### 🧠 智能过滤
七层过滤链自动跳过：
- ❌ 视频和 GIF（币安广场不支持）
- ❌ 转推（只同步原创内容）
- ❌ 回复和线程续帖
- ❌ 纯图无文字、空内容

</td>
<td width="50%">

#### 🔄 自动重试与去重
- 🔁 发布失败自动排队重试（最多 3 次）
- 🔒 SQLite 游标去重，绝不重复发帖
- ⏸️ 检测到日限额自动暂停
- 🕛 午夜自动恢复

</td>
</tr>
<tr>
<td width="50%">

#### 🐳 一键部署
```bash
docker compose up -d --build
```
- Playwright 预装就绪
- 非 root 运行（安全）
- 日志自动轮转
- 内存限制 768MB

</td>
<td width="50%">

#### 🔔 Discord 通知
- 🔴 致命：Cookie 过期、API Key 失效
- 🟠 错误：推文永久发布失败
- 🟡 警告：日限额、敏感内容
- 🔵 信息：每日同步报告

</td>
</tr>
</table>

### 🔑 你只需要准备

| | 项目 | 必需 | 获取方式 |
|---|------|:----:|----------|
| 🐦 | **Twitter 用户名** | ✅ | 你想监控的 @用户名 |
| 🟡 | **币安广场 API Key** | ✅ | [教程 →](references/binance-api-guide.md) &nbsp; ⏱️ 创作者审批 24-48 小时 |
| 🍪 | **Twitter Cookie（JSON）** | ✅ | [教程 →](references/twitter-cookies-guide.md) &nbsp; 🔧 通过 Cookie-Editor 导出 |
| 💬 | **Discord Bot Token** | ❌ | [教程 →](references/discord-bot-guide.md) &nbsp; 可选通知功能 |

### 🚀 快速开始

> [!TIP]
> **Claude Code 用户**：直接说 *"帮我把推文同步到币安广场"*，Claude 只会问你 3 个问题，然后全自动完成配置和部署。**不需要你输入任何命令。**

<details>
<summary><b>📋 手动配置（点击展开）</b></summary>

```bash
# 1. 生成项目
python3 scripts/init_project.py \
  --twitter-username 目标用户名 \
  --output-dir ~/twitter-sync

# 2. 配置凭证
cd ~/twitter-sync
# 编辑 .env → 填入币安 API Key
# Cookie-Editor 导出 → cookies/twitter.json

# 3. 校验并部署
python3 validate_config.py
docker compose up -d --build

# 4. 测试（不实际发帖）
docker exec twitter-sync python main.py --test
```

</details>

### 📚 文档

| | 文档 | 说明 |
|---|------|------|
| 🏗️ | [架构说明](references/architecture.md) | 数据流、SQLite Schema、状态机、游标机制 |
| 🍪 | [Twitter Cookie 教程](references/twitter-cookies-guide.md) | Cookie-Editor 导出步骤 |
| 🟡 | [币安 API 教程](references/binance-api-guide.md) | API Key 申请、接口说明、错误码 |
| 💬 | [Discord Bot 教程](references/discord-bot-guide.md) | Bot 创建和频道配置 |
| 🐳 | [部署教程](references/vps-deployment-guide.md) | Docker 安装和部署流程 |
| 🔧 | [故障排查](references/troubleshooting.md) | 错误码对照、7 个常见场景 |
| ⚙️ | [自定义扩展](references/customization-guide.md) | 过滤规则、换平台、多账号 |

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

### 💖 Support This Project

**If this helps you, a Star means the world!** ⭐

**如果对你有帮助，一个 Star 就是最大的支持！** ⭐

<br/>

<img src="https://img.shields.io/badge/Made_with-❤️-ff3860?style=for-the-badge" alt="Made with love"/>
&nbsp;
<img src="https://img.shields.io/badge/Powered_by-Claude_Code-7C3AED?style=for-the-badge" alt="Claude Code"/>
&nbsp;
<img src="https://img.shields.io/badge/3×_Security-Audited-C9A84C?style=for-the-badge" alt="3x Audited"/>

<br/><br/>

<!-- Activity Graph -->
<img src="https://github-readme-activity-graph.vercel.app/graph?username=yansc153&repo=twitter-binance-sync&theme=github-compact&hide_border=true&area=true&custom_title=Commit%20Activity" width="90%"/>

<br/>

<!-- Footer Wave -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1DA1F2,50:6C5CE7,100:F0B90B&height=120&section=footer" width="100%"/>

</div>
