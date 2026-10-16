import os
import json
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from loguru import logger

UTC8 = timezone(timedelta(hours=8))

OPS_TOKEN = os.getenv("TELEGRAM_OPS_BOT_TOKEN", "").strip()
OPS_CHAT = os.getenv("TELEGRAM_OPS_CHAT_ID", "").strip()
QUEUE_FILE = "./tmp/telegram_ops_queue.json"


async def _send_message(content: str) -> bool:
    if not OPS_TOKEN or not OPS_CHAT:
        logger.debug("Telegram OPS not configured, skip alert")
        return False
    if len(content) > 4000:
        content = content[:4000] + "..."
    url = f"https://api.telegram.org/bot{OPS_TOKEN}/sendMessage"
    payload = {"chat_id": OPS_CHAT, "text": content, "disable_web_page_preview": True}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    logger.debug("Telegram OPS message sent")
                    return True
                logger.error(f"Telegram OPS error: {data}")
                return False
    except Exception as e:
        logger.error(f"Telegram OPS send failed: {e}")
        return False


async def _send_with_retry(content: str) -> bool:
    if await _send_message(content):
        return True
    logger.info("Telegram OPS failed, retry in 30s...")
    await asyncio.sleep(30)
    if await _send_message(content):
        return True
    _queue_message(content)
    return False


def _queue_message(content: str):
    queue = []
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r") as f:
                queue = json.load(f)
        except Exception:
            queue = []
    queue.append({"content": content, "queued_at": datetime.now(UTC8).isoformat()})
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, ensure_ascii=False)
    logger.info(f"OPS message queued, size={len(queue)}")


def send_alert(message, severity="INFO"):
    prefix = {
        "CRITICAL": "🔴",
        "ERROR": "🟠",
        "WARNING": "🟡",
        "INFO": "🔵",
    }.get(severity, "ℹ️")
    content = f"{prefix} [twitter-sync] {message}"
    try:
        loop = asyncio.get_running_loop()
        asyncio.ensure_future(_send_with_retry(content))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_send_with_retry(content))
        finally:
            asyncio.set_event_loop(None)
            loop.close()


def send_daily_digest(stats):
    now = datetime.now(UTC8)
    content = (
        f"📊 Daily Sync Report — {now.strftime('%Y-%m-%d')}\n"
        f"Published: {stats.get('published', 0)}\n"
        f"Filtered:  {stats.get('filtered', 0)}\n"
        f"Failed:    {stats.get('failed', 0)}\n"
        f"Dead:      {stats.get('dead', 0)}\n"
        f"Retried:   {stats.get('retried', 0)}\n"
        f"Cycles:    {stats.get('cycles', 0)}\n"
        f"Avg dur:   {stats.get('avg_duration', 0)}s"
    )
    send_alert(content, "INFO")


async def flush_queue():
    if not os.path.exists(QUEUE_FILE):
        return
    try:
        with open(QUEUE_FILE, "r") as f:
            queue = json.load(f)
    except Exception:
        return
    if not queue:
        return
    remaining = []
    for item in queue:
        if not await _send_message(item["content"]):
            remaining.append(item)
    if remaining:
        with open(QUEUE_FILE, "w") as f:
            json.dump(remaining, f, ensure_ascii=False)
    else:
        os.remove(QUEUE_FILE)
    logger.info(
        f"OPS queue flushed: {len(queue) - len(remaining)} sent, {len(remaining)} left"
    )
