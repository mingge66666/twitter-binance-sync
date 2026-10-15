import re
import time
import urllib.parse
import urllib.request
import json
from loguru import logger

URL_PATTERN = re.compile(r"https?://\S+")


def is_mostly_english(text: str) -> bool:
    if not text or not text.strip():
        return False
    letters = sum(1 for c in text if c.isalpha())
    if letters == 0:
        return False
    ascii_letters = sum(1 for c in text if "a" <= c.lower() <= "z")
    return (ascii_letters / letters) > 0.6


def translate_to_chinese(text: str) -> str:
    """
    仅用 Google 免费接口（不用 deep_translator，减少限流）。
    失败返回原文。
    """
    if not text or not text.strip():
        return text

    # 已有较多中文则不译
    chinese = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    if chinese > len(text) * 0.3:
        return text

    url = (
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=en&tl=zh-CN&dt=t&q={urllib.parse.quote(text)}"
    )

    for attempt in range(3):
        try:
            if attempt > 0:
                # 被限流时多等一会儿
                wait = 5 * attempt
                logger.info(f"Google translate retry in {wait}s (attempt {attempt+1})")
                time.sleep(wait)

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    )
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            # 结构: [[["中文片段", "英文", ...], ...], ...]
            parts = []
            for item in data[0]:
                if item and item[0]:
                    parts.append(item[0])
            result = "".join(parts).strip()
            if result:
                logger.info("Google translate OK")
                return result
            logger.warning(f"Google returned empty (attempt {attempt+1})")
        except Exception as e:
            logger.warning(f"Google translate attempt {attempt+1} failed: {e}")

    logger.warning("All Google translation attempts failed, using original text")
    return text


def process_tweet(raw_text, max_length=900):
    """Strip URLs, normalize whitespace, translate EN→ZH, truncate if needed."""
    text = URL_PATTERN.sub("", raw_text)
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if is_mostly_english(text):
        original = text
        text = translate_to_chinese(text)
        if text == original:
            logger.info("Kept original English (translation failed or limited)")
        else:
            logger.info(f"Translated: {original[:40]}... -> {text[:40]}...")

    if len(text) > max_length:
        truncated = text[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        text = truncated.rstrip() + "..."
        logger.warning(f"Tweet truncated from {len(raw_text)} to {len(text)} chars")

    return text
