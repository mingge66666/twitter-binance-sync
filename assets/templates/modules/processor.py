import requests
from loguru import logger
import time

def translate_to_chinese(text: str, max_retries: int = 3) -> str:
    """使用 MyMemory 翻译成中文"""
    if not text or not text.strip():
        return text

    url = "https://api.mymemory.translated.net/get"
    
    # 推荐加上邮箱，额度提升到 5万字符/天
    # 换成你自己的邮箱
    email = "btcmingge@gmail.com"   # ← 改成你的真实邮箱

    params = {
        "q": text[:450],  # 保险起见，稍微截断一点，避免超过 500 字节
        "langpair": "en|zh-CN",  # 英文 → 简体中文
        "de": email,             # 有邮箱就加上，额度更高
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("responseStatus") == 200:
                translated = data["responseData"]["translatedText"]
                # 有时候会返回和原文一样，或者空
                if translated and translated.strip() and translated != text:
                    return translated
                else:
                    logger.warning(f"MyMemory returned empty or same text: {translated}")
            else:
                logger.warning(f"MyMemory responseStatus: {data.get('responseStatus')}, details: {data.get('responseDetails')}")

        except Exception as e:
            logger.warning(f"MyMemory attempt {attempt} failed: {e}")
            if attempt < max_retries:
                sleep_time = 2 ** attempt
                logger.info(f"MyMemory retry in {sleep_time}s (attempt {attempt+1})")
                time.sleep(sleep_time)

    # 全部失败就返回原文
    logger.error("MyMemory translation completely failed, return original text")
    return text
