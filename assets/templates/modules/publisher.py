import os
import time
import aiohttp
import asyncio
from loguru import logger

def _get_api_key():
    key = os.getenv("BINANCE_SQUARE_API_KEY", "")
    if not key:
        raise RuntimeError("BINANCE_SQUARE_API_KEY is not set")
    return key


async def publish_to_square(clean_text, api_endpoint, delay=10, _retry_truncate=False):
    """Publish text to Binance Square. Returns (success, result_dict)."""
    headers = {
        "X-Square-OpenAPI-Key": _get_api_key(),
        "Content-Type": "application/json",
    }
    payload = {"bodyTextOnly": clean_text}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_endpoint, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()

        code = data.get("code", "")
        msg = data.get("message", "")

        if code == "000000":
            post_id = data.get("data", {}).get("id", "")
            post_url = f"https://www.binance.com/square/post/{post_id}" if post_id else ""
            logger.info(f"Published to Square: {post_url}")
            return True, {
                "square_post_id": str(post_id),
                "square_post_url": post_url,
            }

        # Error handling
        result = {"error_code": str(code), "error_msg": msg}

        if code in ("220009",):
            # Daily limit exceeded
            logger.warning(f"Square daily limit reached: {code} {msg}")
            result["halt_today"] = True
            return False, result

        if code in ("220003", "220004"):
            # API key invalid
            logger.error(f"Square API key error: {code} {msg}")
            result["halt_permanent"] = True
            return False, result

        if code in ("20002", "20022"):
            # Sensitive content
            logger.warning(f"Square sensitive content rejection: {code} {msg}")
            result["skip_permanent"] = True
            return False, result

        if code == "20013" and not _retry_truncate:
            # Content too long -- truncate and retry once (no further recursion)
            logger.warning("Square content too long, truncating and retrying")
            truncated = clean_text[:800].rstrip() + "..."
            await asyncio.sleep(delay)
            return await publish_to_square(truncated, api_endpoint, delay, _retry_truncate=True)

        # Other errors
        logger.error(f"Square API error: {code} {msg}")
        return False, result

    except Exception as e:
        logger.error(f"Square publish exception: {e}")
        return False, {"error_code": "exception", "error_msg": str(e)}
