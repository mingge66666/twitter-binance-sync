import os
import re
import time
import requests
from loguru import logger

URL_PATTERN = re.compile(r"https?://\S+")


def is_mostly_english(text: str) -> bool:
    """简单判断文本是否主要为英文"""
    if not text or not text.strip():
        return False
    letters = sum(1 for c in text if c.isalpha())
    if letters == 0:
        return False
    ascii_letters = sum(1 for c in text if "a" <= c.lower() <= "z")
    return (ascii_letters / letters) > 0.6


def translate_to_chinese(text: str, max_retries: int = 3) -> str:
    """使用 DeepL API 将英文翻译成简体中文"""
    if not text or not text.strip():
        return text

    api_key = os.getenv("DEEPL_API_KEY", "").strip()
    if not api_key:
        logger.warning("DEEPL_API_KEY not set, skip translation")
        return text

    # 免费 Key 通常以 :fx 结尾
    if api_key.endswith(":fx"):
        base_url = "https://api-free.deepl.com/v2/translate"
    else:
        base_url = "https://api.deepl.com/v2/translate"

    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": [text[:4500]],  # DeepL 单次有长度限制，推文足够
        "source_lang": "EN",
        "target_lang": "ZH",  # 简体中文
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                base_url, headers=headers, json=payload, timeout=15
            )
            if resp.status_code == 403:
                logger.error("DeepL 403: API key invalid or plan not allowed")
                return text
            if resp.status_code == 456:
                logger.error("DeepL quota exceeded")
                return text
            resp.raise_for_status()
            data = resp.json()
            translations = data.get("translations") or []
            if translations:
                translated = (translations[0].get("text") or "").strip()
                if translated and translated != text.strip():
                    logger.info(f"Translated via DeepL: {translated[:80]}...")
                    return translated
            logger.warning(f"DeepL empty result: {data}")
        except Exception as e:
            logger.warning(f"DeepL attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    logger.warning("DeepL translation failed, using original text")
    return text


def process_tweet(raw_text, max_length=900):
    """去链接、规范化空白、英文则 DeepL 翻译、超长截断"""
    text = URL_PATTERN.sub("", raw_text)
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if is_mostly_english(text):
        text = translate_to_chinese(text)

    if len(text) > max_length:
        truncated = text[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        text = truncated.rstrip() + "..."
        logger.warning(f"Tweet truncated to {len(text)} chars")

    return text
