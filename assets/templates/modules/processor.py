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
    """英文翻译成中文：优先 MyMemory，失败再试 Google"""
    if not TRANSLATOR_AVAILABLE:
        logger.warning("Translator not available, skip translation")
        return text

    if len(text.strip()) < 3:
        return text

    import time

    engines = [
        # MyMemory 必须用完整语言名或地区代码
        ("MyMemory", lambda: MyMemoryTranslator(
            source='english', target='chinese simplified'
        ).translate(text)),
        ("Google", lambda: GoogleTranslator(
            source='auto', target='zh-CN'
        ).translate(text)),
    ]

    for name, fn in engines:
        for attempt in range(2):
            try:
                time.sleep(0.8)
                result = fn()
                if result and result.strip() and result.strip() != text.strip():
                    logger.info(f"Translated via {name}: {result[:80]}...")
                    return result.strip()
            except Exception as e:
                logger.warning(f"{name} translation attempt {attempt+1} failed: {e}")
                time.sleep(1.5 * (attempt + 1))

    logger.warning("All translators failed, using original English text")
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
