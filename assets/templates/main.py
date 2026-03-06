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
        print(f"[FATAL] config.yaml not found at {config_path}")
        print("        Did you run init_project.py or rename config.yaml.template?")
        sys.exit(1)
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def validate_env():
    """Check that required environment variables are set before starting."""
    missing = []
    for var in ["BINANCE_SQUARE_API_KEY"]:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        print(f"[FATAL] Required environment variables are empty: {', '.join(missing)}")
        print("        Edit .env and fill in the values. See references/binance-api-guide.md.")
        sys.exit(1)

    # Discord is optional but warn if not configured
    if not os.getenv("DISCORD_BOT_TOKEN") or not os.getenv("DISCORD_CHANNEL_ID"):
        print("[WARN] DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID is empty.")
        print("       Discord notifications will be disabled. Service will still run.")


def setup_logging(config):
    log_config = config.get("logging", {})
    log_file = log_config.get("file", "./logs/sync.log")
    log_level = log_config.get("level", "INFO")
    max_bytes = log_config.get("max_bytes", 52428800)
    backup_count = log_config.get("backup_count", 5)

    # Ensure log directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console output
    logger.add(sys.stderr, level=log_level, format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}")

    # File output with rotation
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
    """Restrict cookie file to owner-only read on shared systems."""
    cookies_path = config["twitter"]["cookies_path"]
    if os.path.exists(cookies_path):
        mode = os.stat(cookies_path).st_mode
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            os.chmod(cookies_path, 0o600)
            logger.warning(f"Fixed cookie file permissions to 600: {cookies_path}")


async def run_sync_cycle(config):
    """Wrapper to run sync_cycle with error handling."""
    try:
        await sync_cycle(config)
    except Exception as e:
        logger.exception(f"Sync cycle crashed: {e}")
        notifier.send_alert(f"Sync cycle crashed: {e}", "ERROR")


async def test_mode(config):
    """Dry run: fetch and filter only, no publishing."""
    logger.info("=== TEST MODE (dry run, no publishing) ===")

    # Test Discord notification
    notifier.send_alert("Test mode started - this is a connectivity test.", "INFO")
    print("[INFO] Discord test message sent -- check your Discord channel to confirm delivery.")

    # Check cookie file exists
    cookies_path = config["twitter"]["cookies_path"]
    if not os.path.exists(cookies_path):
        print(f"\n[FAIL] Cookie file not found: {cookies_path}")
        print("       Copy your Cookie-Editor export to this path.")
        return

    # Test fetch
    from modules import fetcher, filter as tweet_filter
    raw_tweets, auth_error = await fetcher.fetch_tweets(config)

    if auth_error:
        logger.error(f"Auth error: {auth_error}")
        print(f"\n[FAIL] Twitter auth error: {auth_error}")
        return

    print(f"\n[OK] Fetched {len(raw_tweets)} tweets from Twitter")

    # Determine target user ID
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
        status = "PASS" if ok else f"DROP ({result})"
        text_preview = data.get("content_raw", "")[:60]
        print(f"  {tweet_id}: {status} | {text_preview}")
        if ok:
            passed += 1

    print(f"\n[SUMMARY] {passed}/{len(raw_tweets)} tweets would be published")
    print("[OK] Test mode complete. No posts were made to Binance Square.")


def main():
    load_dotenv()
    config = load_config()
    ensure_dirs()
    validate_env()
    setup_logging(config)
    enforce_cookie_permissions(config)
    db.init_db()

    # Handle --test flag
    if "--test" in sys.argv:
        asyncio.run(test_mode(config))
        return

    logger.info("Twitter-to-Binance-Square sync service starting")
    notifier.send_alert(
        f"Service started at {datetime.now(UTC8).strftime('%Y-%m-%d %H:%M:%S')}",
        "INFO"
    )

    # Create event loop FIRST, then bind APScheduler to it
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai", event_loop=loop)

    # Primary sync job: every 60 minutes with jitter
    interval = config["scheduler"]["interval_minutes"]
    jitter = config["scheduler"]["jitter_minutes"] * 60  # convert to seconds

    scheduler.add_job(
        run_sync_cycle,
        "interval",
        minutes=interval,
        jitter=jitter,
        args=[config],
        id="sync_cycle",
        name="Twitter Sync Cycle",
        max_instances=1,
    )

    # Daily digest at 21:00 UTC+8
    digest_hour = config["scheduler"]["daily_digest_hour_utc8"]
    scheduler.add_job(
        daily_digest,
        "cron",
        hour=digest_hour,
        minute=0,
        id="daily_digest",
        name="Daily Digest",
    )

    # Midnight reset at 00:00 UTC+8
    reset_hour = config["scheduler"]["midnight_reset_hour_utc8"]
    scheduler.add_job(
        midnight_reset,
        "cron",
        hour=reset_hour,
        minute=0,
        id="midnight_reset",
        name="Midnight Reset",
    )

    # Graceful shutdown
    def shutdown(signum, frame):
        logger.info("Received shutdown signal, cleaning up...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    scheduler.start()
    logger.info(f"Scheduler started: sync every {interval}min (+-{config['scheduler']['jitter_minutes']}min jitter)")

    # Run first cycle immediately, then keep event loop running
    loop.run_until_complete(run_sync_cycle(config))

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Service stopped")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
