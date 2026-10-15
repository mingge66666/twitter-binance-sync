import os
import time
import asyncio
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from loguru import logger

def _get_api_key():
    key = os.getenv("BINANCE_SQUARE_API_KEY", "")
    if not key:
        raise RuntimeError("BINANCE_SQUARE_API_KEY is not set")
    return key

API_V1 = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi"
API_V2 = "https://www.binance.com/bapi/composite/v2/public/pgc/openApi"
TMP_DIR = Path("./tmp/images")
MAX_IMAGES = 4


def _headers_json():
    return {
        "X-Square-OpenAPI-Key": _get_api_key(),
        "Content-Type": "application/json",
        "clienttype": "binanceSkill",
    }


async def _api_post(session, base, path, body):
    async with session.post(
        f"{base}{path}",
        headers=_headers_json(),
        json=body,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as resp:
        return await resp.json()


async def upload_tweet_images(image_urls: list) -> list:
    """
    下载推特图片 → 上传币安 → 返回 imageList（币安 imageUrl 列表）
    失败的单张会跳过；全部失败则返回 []，仍可发纯文字。
    """
    if not image_urls:
        return []

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    result = []

    async with aiohttp.ClientSession() as session:
        for i, url in enumerate(image_urls[:MAX_IMAGES]):
            ext = Path(urlparse(url).path).suffix.lower() or ".jpg"
            if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                ext = ".jpg"
            local = TMP_DIR / f"tw_{int(time.time())}_{i}{ext}"

            # 1) 下载
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
                    if r.status != 200:
                        logger.warning(f"Download image HTTP {r.status}: {url}")
                        continue
                    local.write_bytes(await r.read())
            except Exception as e:
                logger.warning(f"Download image error: {e}")
                continue

            # 2) 获取预签名
            data = await _api_post(
                session, API_V2, "/image/presignedUrl", {"imageName": local.name}
            )
            if data.get("code") != "000000":
                logger.error(f"presignedUrl failed: {data}")
                local.unlink(missing_ok=True)
                continue

            presigned = data["data"]["presignedUrl"]
            ticket = data["data"]["fileTicket"]
            ctype = mimetypes.guess_type(str(local))[0] or "image/jpeg"

            # 3) PUT 到 S3
            try:
                async with session.put(
                    presigned,
                    data=local.read_bytes(),
                    headers={"Content-Type": ctype},
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as r:
                    if r.status not in (200, 201):
                        logger.error(f"S3 upload HTTP {r.status}")
                        local.unlink(missing_ok=True)
                        continue
            except Exception as e:
                logger.error(f"S3 upload error: {e}")
                local.unlink(missing_ok=True)
                continue

            # 4) 轮询处理结果
            image_url = None
            for _ in range(12):
                await asyncio.sleep(3)
                st = await _api_post(
                    session, API_V2, "/image/imageStatus", {"fileTicket": ticket}
                )
                if st.get("code") != "000000":
                    continue
                d = st.get("data") or {}
                if d.get("status") == 1:
                    image_url = d.get("imageUrl")
                    break
                if d.get("status") == 2:
                    logger.error(f"Image process failed: {d.get('failedReason')}")
                    break

            local.unlink(missing_ok=True)

            if image_url:
                result.append(image_url)
                logger.info(f"Image ready: {image_url}")
            else:
                logger.warning(f"Image upload timeout/fail for: {url}")

    return result


async def publish_to_square(
    clean_text,
    api_endpoint,
    delay=10,
    image_urls=None,
    _retry_truncate=False,
):
    """发布到币安广场；image_urls 为推特图片直链列表（可选）。"""

    image_list = []
    if image_urls and not _retry_truncate:
        try:
            image_list = await upload_tweet_images(image_urls)
            logger.info(f"Uploaded images: {len(image_list)}/{len(image_urls or [])}")
        except Exception as e:
            logger.error(f"Image upload failed, fallback text-only: {e}")

    payload = {
        "contentType": 1,
        "bodyTextOnly": clean_text,
    }
    if image_list:
        payload["imageList"] = image_list

    # 下面保持你原来的 POST 与错误处理逻辑不变
    # 注意：headers 建议带上 clienttype
    headers = {
        "X-Square-OpenAPI-Key": _get_api_key(),
        "Content-Type": "application/json",
        "clienttype": "binanceSkill",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_endpoint,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=45),
            ) as resp:
                data = await resp.json()

        code = str(data.get("code", ""))
        msg = data.get("message", "")

        if code == "000000":
            post_id = (data.get("data") or {}).get("id", "")
            post_url = f"https://www.binance.com/square/post/{post_id}" if post_id else ""
            logger.info(f"Published to Square: {post_url}")
            return True, {
                "square_post_id": str(post_id),
                "square_post_url": post_url,
            }

        result = {"error_code": code, "error_msg": msg}

        if code == "220009":
            result["halt_today"] = True
            return False, result
        if code in ("220003", "220004"):
            result["halt_permanent"] = True
            return False, result
        if code in ("20002", "20022"):
            result["skip_permanent"] = True
            return False, result

        # 内容过长：截断后重试（不再带图，避免重复上传）
        if code == "20013" and not _retry_truncate:
            truncated = clean_text[:800].rstrip() + "..."
            await asyncio.sleep(delay)
            return await publish_to_square(
                truncated, api_endpoint, delay,
                image_urls=None, _retry_truncate=True,
            )

        # 图片日上传上限：降级为纯文字
        if code == "220014":
            logger.warning("Image daily limit, retry text-only")
            await asyncio.sleep(delay)
            return await publish_to_square(
                clean_text, api_endpoint, delay,
                image_urls=None, _retry_truncate=True,
            )

        logger.error(f"Square API error: {code} {msg}")
        return False, result

    except Exception as e:
        logger.error(f"Square publish exception: {e}")
        return False, {"error_code": "exception", "error_msg": str(e)}

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
