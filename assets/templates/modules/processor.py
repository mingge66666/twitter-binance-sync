import re
import time
import requests
from loguru import logger

URL_PATTERN = re.compile(r'https?://\S+')


def is_mostly_english(text: str) -> bool:
    """简单判断文本是否主要为英文"""
    if not text or not text.strip():
        return False
    letters = sum(1 for c in text if c.isalpha())
    if letters == 0:
        return False
    ascii_letters = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return (ascii_letters / letters) > 0.6


def translate_to_chinese(text: str, max_retries: int = 3) -> str:
    """使用 MyMemory 公开 API 翻译成中文"""
    if not text or not text.strip():
        return text

    url = "https://api.mymemory.translated.net/get"
    email = "btcmingge@gmail.com"  # 可选，提高免费额度

    params = {
        "q": text[:450],
        "langpair": "en|zh-CN",
        "de": email,
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("responseStatus") == 200:
                translated = data["responseData"]["translatedText"]
                if translated and translated.strip() and translated.strip() != text.strip():
                    logger.info(f"Translated via MyMemory API: {translated[:80]}...")
                    return translated.strip()
                else:
                    logger.warning(f"MyMemory returned empty or same text: {translated}")
            else:
                logger.warning(
                    f"MyMemory responseStatus: {data.get('responseStatus')}, "
                    f"details: {data.get('responseDetails')}"
                )
        except Exception as e:
            logger.warning(f"MyMemory attempt {attempt} failed: {e}")
            if attempt < max_retries:
                sleep_time = 2 ** attempt
                time.sleep(sleep_time)

    logger.warning("MyMemory translation failed, using original text")
    return text


def process_tweet(raw_text, max_length=900):
    """Strip URLs, normalize whitespace, translate if English, truncate if needed."""
    # 1. 去掉 URL
    text = URL_PATTERN.sub('', raw_text)

    # 2. 规范化空白
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    # 3. 英文则翻译
    if is_mostly_english(text):
        text = translate_to_chinese(text)

    # 4. 超长截断
    if len(text) > max_length:
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        text = truncated.rstrip() + "..."
        logger.warning(f"Tweet truncated to {len(text)} chars")

    return text
