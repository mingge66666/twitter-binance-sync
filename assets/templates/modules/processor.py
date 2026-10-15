import re
import time
from loguru import logger

try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    logger.warning("deep-translator not installed, translation disabled")

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


def translate_to_chinese(text: str) -> str:
    """英文翻译成中文，失败则返回原文"""
    if not TRANSLATOR_AVAILABLE:
        logger.warning("Translator not available, skip translation")
        return text
    import time
    for attempt in range(3):
        try:
            time.sleep(0.8)
            result = GoogleTranslator(source='auto', target='zh-CN').translate(text)
            if result and result.strip() and result.strip() != text.strip():
                return result.strip()
        except Exception as e:
            logger.warning(f"Translation attempt {attempt+1} failed: {e}")
            time.sleep(1.5 * (attempt + 1))
    logger.warning("All translation attempts failed, using original text")
    return text


def process_tweet(raw_text, max_length=900):
    """Strip URLs, normalize whitespace, optionally translate, truncate if needed."""
    text = URL_PATTERN.sub('', raw_text)
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    if is_mostly_english(text):
        original = text
        text = translate_to_chinese(text)
        if text == original:
            logger.info("Kept original English (translation unavailable or failed)")

    if len(text) > max_length:
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        text = truncated.rstrip() + "..."
        logger.warning(f"Tweet truncated from {len(raw_text)} to {len(text)} chars")

    return text
