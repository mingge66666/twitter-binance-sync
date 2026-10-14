import re
from loguru import logger

try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    logger.warning("deep-translator not installed, translation disabled")

URL_PATTERN = re.compile(r'https?://\S+')


def is_mostly_english(text: str) -> bool:
    """简单判断文本是否主要为英文"""
    if not text or not text.strip():
        return False
    # 统计 ASCII 字母占比
    letters = sum(1 for c in text if c.isalpha())
    if letters == 0:
        return False
    ascii_letters = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return (ascii_letters / letters) > 0.6


def translate_to_chinese(text: str) -> str:
    """英文翻译成中文，失败则返回原文"""
    if not TRANSLATOR_AVAILABLE:
        return text
    try:
        # 自动检测源语言，目标为简体中文
        result = GoogleTranslator(source='auto', target='zh-CN').translate(text)
        if result and result.strip():
            return result.strip()
    except Exception as e:
        logger.warning(f"Translation failed: {e}")
    return text


def process_tweet(raw_text, max_length=900):
    """Strip URLs, normalize whitespace, optionally translate, truncate if needed."""
    # Step 1: Strip URLs
    text = URL_PATTERN.sub('', raw_text)

    # Step 2: Normalize whitespace
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    # Step 3: 如果是英文，翻译成中文
    if is_mostly_english(text):
        original = text
        text = translate_to_chinese(text)
        if text != original:
            logger.info(f"Translated to Chinese: {text[:80]}...")

    # Step 4: Truncate if exceeds max length
    if len(text) > max_length:
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        text = truncated.rstrip() + "..."
        logger.warning(f"Tweet truncated from {len(raw_text)} to {len(text)} chars")

    return text
