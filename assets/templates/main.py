import os
import sys
import stat
import signal
import asyncio
import yaml
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from modules import db, notifier
from modules.scheduler import sync_cycle, daily_digest, midnight_reset

UTC8 = timezone(timedelta(hours=8))


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if not os.path.exists(config_path):
        print(f"[致命] 未找到 config.yaml，路径: {config_path}")
        print("        请确认已运行 init_project.py，或已将 config.yaml.template 重命名为 config.yaml。")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_env():
    """启动前检查必要的环境变量。"""
    missing = []
    for var in ["BINANCE_SQUARE_API_KEY"]:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        print(f"[致命] 以下环境变量为空: {', '.join(missing)}")
        print("        请编辑 .env 填入对应值。可参考 references/binance-api-guide.md。")
        sys.exit(1)

    if not os.getenv("TELEGRAM_OPS_BOT_TOKEN") or not os.getenv("TELEGRAM_OPS_CHAT_ID"):
        print("[警告] 未配置 TELEGRAM_OPS_BOT_TOKEN 或 TELEGRAM_OPS_CHAT_ID。")
        print("       运维通知将禁用，服务仍会正常运行。")

    if not os.getenv("TELEGRAM_SYNC_BOT_TOKEN") or not os.getenv("TELEGRAM_SYNC_CHAT_ID"):
        print("[警告] 未配置 TELEGRAM_SYNC_BOT_TOKEN 或 TELEGRAM_SYNC_CHAT_ID。")
        print("       公开频道同步将禁用。")


def setup_logging(config):
    log_config = config.get("logging", {})
    log_file = log_config.get("file", "./logs/sync.log")
    log_level = log_config.get("level", "INFO")
    max_bytes = log_config.get("max_bytes", 52428800)
    backup_count = log_config.get("backup_count", 5)

    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)

    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
    )
    logger.add(
        log_file,
        level=log_level,
        rotation=max_bytes,
        retention=backup_count,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {module}:{function}:{line} | {message}",
        encoding="utf-8",
    )


def ensure_dirs():
    for d in ["db", "logs", "tmp", "cookies"]:
        os.makedirs(d, exist_ok=True)


def enforce_cookie_permissions(config):
    """在共享环境下将 Cookie 文件权限收紧为仅所有者可读。"""
    cookies_path = config["twitter"]["cookies_path"]
    if os.path.exists(cookies_path):
        mode = os.stat(cookies_path).st_mode
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            os.chmod(cookies_path, 0o600)
            logger.warning(f"已将 Cookie 文件权限调整为 600: {cookies_path}")


async def run_sync_cycle(config):
    """包装同步周期，捕获异常并发送运维通知。"""
    try:
        await sync_cycle(config)
    except Exception as e:
        logger.exception(f"同步周期异常退出: {e}")
        notifier.send_alert(f"同步周期异常退出：{e}", "ERROR")


async def test_mode(config):
    """测试模式：只抓取和过滤，不实际发布。"""
    logger.info("=== 测试模式（仅抓取过滤，不实际发布）===")

    notifier.send_alert("测试模式已启动，这是一条连通性测试消息。", "INFO")
    print("[信息] 已发送运维测试消息，请到 Telegram 私密运维频道确认是否收到。")

    cookies_path = config["twitter"]["cookies_path"]
    if not os.path.exists(cookies_path):
        print(f"\n[失败] 未找到 Cookie 文件: {cookies_path}")
        print("       请将 Cookie-Editor 导出的 JSON 复制到该路径。")
        return

    from modules import fetcher, filter as tweet_filter

    raw_tweets, auth_error = await fetcher.fetch_tweets(config)

    if auth_error:
        logger.error(f"登录异常: {auth_error}")
        print(f"\n[失败] Twitter/X 登录异常: {auth_error}")
        return

    print(f"\n[成功] 已从 Twitter/X 抓取 {len(raw_tweets)} 条推文")

    target_user_id = None
    for t in raw_tweets:
        core = t.get("core", {})
        uid = core.get("user_results", {}).get("result", {}).get("rest_id", "")
        if uid:
            target_user_id = uid
            break

    passed = 0
    for tweet in raw_tweets:
        tweet_id = tweet.get("rest_id", "")
        ok, result, data = tweet_filter.filter_tweet(tweet, target_user_id or "")
        status = "通过" if ok else f"丢弃({result})"
        text_preview = data.get("content_raw", "")[:60]
        print(f"  {tweet_id}: {status} | {text_preview}")
        if ok:
            passed += 1

    print(f"\n[汇总] {passed}/{len(raw_tweets)} 条推文将通过过滤并可能被发布")
    print("[完成] 测试模式结束，未向币安广场发帖。")


def main():
    load_dotenv()
    config = load_config()
    ensure_dirs()
    validate_env()
    setup_logging(config)
    enforce_cookie_permissions(config)
    db.init_db()

    if "--test" in sys.argv:
        asyncio.run(test_mode(config))
        return

    logger.info("Twitter → 币安广场同步服务正在启动")
    notifier.send_alert(
        f"服务已启动：{datetime.now(UTC8).strftime('%Y-%m-%d %H:%M:%S')}",
        "INFO",
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai", event_loop=loop)

    interval = config["scheduler"]["interval_minutes"]
    jitter = config["scheduler"]["jitter_minutes"] * 60

    scheduler.add_job(
        run_sync_cycle,
        "interval",
        minutes=interval,
        jitter=jitter,
        args=[config],
        id="sync_cycle",
        name="Twitter 同步周期",
        max_instances=1,
    )

    digest_hour = config["scheduler"]["daily_digest_hour_utc8"]
    scheduler.add_job(
        daily_digest,
        "cron",
        hour=digest_hour,
        minute=0,
        id="daily_digest",
        name="每日报告",
    )

    reset_hour = config["scheduler"]["midnight_reset_hour_utc8"]
    scheduler.add_job(
        midnight_reset,
        "cron",
        hour=reset_hour,
        minute=0,
        id="midnight_reset",
        name="午夜重置",
    )

    def shutdown(signum, frame):
        logger.info("收到停止信号，正在清理…")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    scheduler.start()
    logger.info(
        f"调度器已启动：每 {interval} 分钟同步一次"
        f"（抖动 ±{config['scheduler']['jitter_minutes']} 分钟）"
    )

    loop.run_until_complete(run_sync_cycle(config))

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("服务已停止")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
