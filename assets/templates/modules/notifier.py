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
        logger.debug("未配置 Telegram 运维机器人，跳过通知")
        return False
    if len(content) > 4000:
        content = content[:4000] + "..."
    url = f"https://api.telegram.org/bot{OPS_TOKEN}/sendMessage"
    payload = {
        "chat_id": OPS_CHAT,
        "text": content,
        "disable_web_page_preview": True,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    logger.debug("Telegram 运维消息已发送")
                    return True
                logger.error(f"Telegram 运维发送失败: {data}")
                return False
    except Exception as e:
        logger.error(f"Telegram 运维发送异常: {e}")
        return False


async def _send_with_retry(content: str) -> bool:
    if await _send_message(content):
        return True
    logger.info("Telegram 运维发送失败，30 秒后重试…")
    await asyncio.sleep(30)
    if await _send_message(content):
        return True
    _queue_message(content)
    return False


def _queue_message(content: str):
    queue = []
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                queue = json.load(f)
        except Exception:
            queue = []
    queue.append({
        "content": content,
        "queued_at": datetime.now(UTC8).isoformat(),
    })
    os.makedirs(os.path.dirname(QUEUE_FILE) or ".", exist_ok=True)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False)
    logger.info(f"运维消息已入队，当前队列长度={len(queue)}")


def send_alert(message, severity="INFO"):
    """发送运维告警到 Telegram 私密频道。"""
    prefix = {
        "CRITICAL": "🔴【严重】",
        "ERROR": "🟠【错误】",
        "WARNING": "🟡【警告】",
        "INFO": "🔵【信息】",
    }.get(severity, "ℹ️【通知】")
    content = f"{prefix} [twitter-sync]\n{message}"

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
    """每日同步报告（中文）。"""
    now = datetime.now(UTC8)
    content = (
        f"📊 每日同步报告 — {now.strftime('%Y-%m-%d')}\n"
        f"━━━━━━━━━━━━\n"
        f"成功发布：{stats.get('published', 0)} 条\n"
        f"已过滤：{stats.get('filtered', 0)} 条\n"
        f"失败：{stats.get('failed', 0)} 条\n"
        f"永久失败：{stats.get('dead', 0)} 条\n"
        f"重试次数：{stats.get('retried', 0)}\n"
        f"运行周期：{stats.get('cycles', 0)} 次\n"
        f"平均耗时：{stats.get('avg_duration', 0)} 秒"
    )
    send_alert(content, "INFO")


async def flush_queue():
    """重试发送队列中失败的运维消息。"""
    if not os.path.exists(QUEUE_FILE):
        return
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
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
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(remaining, f, ensure_ascii=False)
    else:
        os.remove(QUEUE_FILE)

    logger.info(
        f"运维队列已处理：成功 {len(queue) - len(remaining)} 条，剩余 {len(remaining)} 条"
    )
