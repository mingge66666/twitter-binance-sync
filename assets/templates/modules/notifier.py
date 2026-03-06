import os
import json
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from loguru import logger

UTC8 = timezone(timedelta(hours=8))

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
DISCORD_API = "https://discord.com/api/v10"

QUEUE_FILE = "./tmp/discord_queue.json"


async def _send_message(content):
    """Send a message to Discord channel via Bot API."""
    url = f"{DISCORD_API}/channels/{CHANNEL_ID}/messages"
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"content": content}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status in (200, 201):
                    logger.debug("Discord message sent")
                    return True
                else:
                    body = await resp.text()
                    logger.error(f"Discord API error {resp.status}: {body}")
                    return False
    except Exception as e:
        logger.error(f"Discord send failed: {e}")
        return False


async def _send_with_retry(content):
    """Send with one retry after 30s on failure."""
    if await _send_message(content):
        return True
    logger.info("Discord send failed, retrying in 30s...")
    await asyncio.sleep(30)
    if await _send_message(content):
        return True
    # Queue for next cycle
    _queue_message(content)
    return False


def _queue_message(content):
    """Save failed message to queue file for retry next cycle."""
    queue = []
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r") as f:
                queue = json.load(f)
        except Exception:
            queue = []
    queue.append({"content": content, "queued_at": datetime.now(UTC8).isoformat()})
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, ensure_ascii=False)
    logger.info(f"Message queued to {QUEUE_FILE}, queue size: {len(queue)}")


def send_alert(message, severity="INFO"):
    """Synchronous wrapper for sending alerts."""
    prefix = {
        "CRITICAL": "\U0001f534",
        "ERROR": "\U0001f7e0",
        "WARNING": "\U0001f7e1",
        "INFO": "\U0001f535",
    }.get(severity, "\u2139\ufe0f")
    content = f"{prefix} **[twitter-sync]** {message}"

    try:
        loop = asyncio.get_running_loop()
        asyncio.ensure_future(_send_with_retry(content))
    except RuntimeError:
        # No running loop -- create one and block
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_send_with_retry(content))
        finally:
            asyncio.set_event_loop(None)
            loop.close()


def send_daily_digest(stats):
    """Send daily digest report."""
    now = datetime.now(UTC8)
    content = (
        f"**Daily Sync Report** -- {now.strftime('%Y-%m-%d')}\n"
        f"```\n"
        f"Published:    {stats.get('published', 0)} posts\n"
        f"Filtered:     {stats.get('filtered', 0)} (video/RT/reply/empty)\n"
        f"Failed:       {stats.get('failed', 0)}\n"
        f"Dead:         {stats.get('dead', 0)}\n"
        f"Retried:      {stats.get('retried', 0)}\n"
        f"---\n"
        f"Cycles run:   {stats.get('cycles', 0)}\n"
        f"Avg duration: {stats.get('avg_duration', 0)}s\n"
        f"```"
    )
    send_alert(content, "INFO")


async def flush_queue():
    """Retry sending queued messages."""
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
    logger.info(f"Discord queue flushed: {len(queue) - len(remaining)} sent, {len(remaining)} remaining")
