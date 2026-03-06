# Docker 部署教程

## 部署环境

本服务通过 Docker 部署。如果 Claude Code 已在当前机器上运行，直接在本地部署即可，无需另购 VPS。

### 最低配置

| 项目 | 最低要求 | 推荐 |
|------|----------|------|
| CPU | 1 核 | 2 核 |
| 内存 | 1 GB | 2 GB |
| 存储 | 10 GB | 20 GB |
| 系统 | Ubuntu 20.04+ / 任何支持 Docker 的 Linux | Ubuntu 22.04 LTS |
| 网络 | 能同时访问 `x.com` 和 `binance.com` | -- |

> 如果需要单独购买 VPS：Vultr, DigitalOcean, Linode, AWS Lightsail, 搬瓦工等均可。选择能同时访问 Twitter 和 Binance 的地区节点。

## 部署步骤

### 1. 安装 Docker（如已安装可跳过）

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 添加当前用户到 docker 组（免 sudo）
sudo usermod -aG docker $USER
newgrp docker

# 验证
docker --version
docker compose version
```

### 2. 准备项目

如果已通过 `init_project.py` 生成项目，直接进入项目目录：
```bash
cd ~/my-sync-project
```

如果需要从远程机器传输项目：
```bash
# 方式一：Git Clone
git clone your-repo-url ~/twitter-sync && cd ~/twitter-sync

# 方式二：SCP 从本地上传到远程
scp -r ~/my-sync-project user@remote-ip:~/twitter-sync
```

### 3. 网络连通性预检

在构建之前，先确认当前机器能同时访问 Twitter 和 Binance：

```bash
curl -sI https://x.com | head -1
# 应返回 HTTP/2 200 或 301

curl -sI https://www.binance.com | head -1
# 应返回 HTTP/2 200 或 301
```

如果任一请求超时或被拦截，说明 VPS 所在地区有网络限制，需要更换节点。

### 4. 配置项目

```bash
cd ~/twitter-sync

# 确认配置文件
ls -la .env config.yaml cookies/twitter.json

# 检查配置完整性
python3 validate_config.py
```

### 5. 构建并启动

> **注意**: 首次构建会下载 Playwright Python Docker 镜像（约 1.5GB），根据 VPS 带宽可能需要 10-20 分钟。期间看似卡住是正常的，请耐心等待。

```bash
# 构建镜像并启动
docker compose up -d --build

# 查看构建进度（如果需要）
docker compose logs -f

# 查看容器状态
docker ps --filter name=twitter-sync
```

**Go/No-Go 检查**：容器启动后确认以下三项全部通过才算部署成功：

```bash
# 1. 容器在运行？
docker ps --filter name=twitter-sync
# STATUS 应为 "Up X seconds"

# 2. 日志无致命错误？
docker logs twitter-sync 2>&1 | tail -20
# 不应有 CRITICAL 或 traceback

# 3. 测试模式通过？
docker exec twitter-sync python main.py --test
# 应能抓到推文、过滤正常
```

如果任一项失败，参见下方「构建失败排查」或 `troubleshooting.md`。

```bash
# 查看实时日志
docker logs -f twitter-sync
```

### 6. 验证运行

```bash
# 等一个同步周期（默认 60 分钟）后，使用 health_check 脚本检查状态
# 如果你是从 skill 包目录运行：
python3 scripts/health_check.py --project-dir ~/twitter-sync

# 或者手动检查：
docker logs --tail 50 twitter-sync
```

## 日常运维

### 查看日志
```bash
docker logs -f --tail 100 twitter-sync
```

### 重启服务
```bash
docker compose restart
```

### 更新代码
```bash
git pull  # 或 scp 新文件
docker compose up -d --build
```

### 刷新 Cookie
```bash
# 1. 在浏览器中重新导出 Cookie（参见 twitter-cookies-guide.md）
# 2. 将新 Cookie 文件放入项目目录
cp /path/to/new_cookies.json cookies/twitter.json

# 3. 重启服务
docker compose restart
```

### 查看磁盘使用
```bash
du -sh db/ logs/
```

### 清理旧日志
```bash
# Docker 日志已自动限制大小（10MB x 3 文件）
# 应用日志通过 loguru rotation 自动管理
```

## 常见问题

### 构建失败排查

**镜像拉取超时**
```bash
# 单独拉取基础镜像，观察进度
docker pull mcr.microsoft.com/playwright/python:v1.42.0-jammy
# 如果超时，检查 VPS 到 Docker Hub / MCR 的连通性
```

**磁盘空间不足**
```bash
df -h
# Playwright 镜像约 1.5GB，加上构建缓存需要至少 5GB 可用空间
docker system prune -f  # 清理旧镜像释放空间
```

**重新构建**
```bash
docker compose down
docker compose up -d --build
```

### 容器启动后立刻退出
```bash
docker logs twitter-sync  # 查看错误
```
常见原因：
- `.env` 文件缺失或格式错误
- `config.yaml` 语法错误或不存在
- `cookies/twitter.json` 不存在
- `BINANCE_SQUARE_API_KEY` 为空（启动时会校验）

### 内存不足
容器已限制 768MB 内存。如果仍 OOM：
```bash
# 查看内存使用
docker stats twitter-sync
```
考虑升级 VPS 或在 `docker-compose.yml` 中调大 `deploy.resources.limits.memory`。

### 时区问题
服务内部使用 UTC+8，APScheduler 配置为 `Asia/Shanghai`。VPS 系统时区不影响服务逻辑。
