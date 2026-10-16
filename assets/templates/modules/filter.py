import re
from modules import db
from modules.processor import process_tweet
from loguru import logger


PERSONAL_LINK_PATTERNS = [
    r"(?i)t\.me/",
    r"(?i)telegram\.me/",
    r"(?i)discord\.gg/",
    r"(?i)discord\.com/invite",
    r"(?i)youtube\.com/",
    r"(?i)youtu\.be/",
    r"(?i)instagram\.com/",
    r"(?i)tiktok\.com/",
    r"(?i)onlyfans\.com/",
    r"(?i)linktr\.ee/",
    r"(?i)bio\.link/",
    r"(?i)carrd\.co/",
    r"(?i)bit\.ly/",
    r"(?i)tinyurl\.com/",
]

PROMO_KEYWORDS = [
    "follow me", "follow for", "subscribe", "giveaway", "airdrop",
    "dm me", "join my", "my channel", "my group", "my community",
    "click the link", "link in bio", "check my", "retweet and",
    "like and rt", "tag your friends",
]

OFFTOPIC_KEYWORDS = [
    "happy birthday", "celebrating my", "enjoying life",
    "wedding", "vacation", "holiday",
]


def has_personal_link(text: str) -> bool:
    if not text:
        return False
    return any(re.search(p, text) for p in PERSONAL_LINK_PATTERNS)


def has_promo_or_offtopic(text: str) -> bool:
    lower = (text or "").lower()
    return any(k in lower for k in PROMO_KEYWORDS + OFFTOPIC_KEYWORDS)


def get_media_types(tweet):
    media_list = []
    legacy = tweet.get("legacy", {})
    for source in [legacy.get("extended_entities", {}), legacy.get("entities", {})]:
        for m in source.get("media", []):
            media_list.append(m.get("type", ""))
    return media_list


def get_image_urls(tweet, max_images=4):
    """提取最多 4 张图，按 media_id 去重。"""
    urls = []
    seen = set()
    legacy = tweet.get("legacy", {})
    if legacy.get("extended_entities"):
        sources = [legacy["extended_entities"]]
    elif legacy.get("entities"):
        sources = [legacy["entities"]]
    else:
        sources = []

    for source in sources:
        for m in source.get("media") or []:
            if m.get("type") != "photo":
                continue
            mid = str(m.get("id_str") or m.get("id") or "")
            u = m.get("media_url_https") or m.get("media_url")
            if not u:
                continue
            base = u.split("?")[0]
            key = mid or base
            if key in seen:
                continue
            seen.add(key)
            if "pbs.twimg.com" in u and "name=" not in u:
                u = u + ("&" if "?" in u else "?") + "name=orig"
            urls.append(u)
            if len(urls) >= max_images:
                return urls
    return urls


def get_tweet_text(tweet):
    legacy = tweet.get("legacy", {})
    return legacy.get("full_text", "") or tweet.get("text", "")


def filter_tweet(tweet, target_user_id, max_content_length=900):
    """
    F-00 ~ F-08 过滤链。
    Returns (passed: bool, filter_result: str, tweet_data: dict)
    """
    tweet_id = tweet.get("rest_id", "") or tweet.get("id_str", "")
    legacy = tweet.get("legacy", {})
    raw_text = get_tweet_text(tweet)
    media_types = get_media_types(tweet)

    tweet_data = {
        "tweet_id": tweet_id,
        "content_raw": raw_text,
        "has_images": 1 if "photo" in media_types else 0,
        "has_video": 1 if ("video" in media_types or "animated_gif" in media_types) else 0,
        "tweet_type": "original",
        "image_urls": get_image_urls(tweet),
    }

    # F-00: 去重
    if db.tweet_exists(tweet_id):
        logger.debug(f"F-00 dedup: {tweet_id}")
        return False, "dedup", tweet_data

    # F-01: 视频
    if "video" in media_types or "animated_gif" in media_types:
        logger.debug(f"F-01 drop_video: {tweet_id}")
        return False, "drop_video", tweet_data

    # F-02: 转推
    if legacy.get("retweeted_status_result") or raw_text.startswith("RT @"):
        tweet_data["tweet_type"] = "retweet"
        logger.debug(f"F-02 drop_rt: {tweet_id}")
        return False, "drop_rt", tweet_data

    # F-03: 回复他人
    reply_to_user = legacy.get("in_reply_to_user_id_str", "")
    if reply_to_user and reply_to_user != target_user_id:
        tweet_data["tweet_type"] = "reply"
        logger.debug(f"F-03 drop_reply: {tweet_id}")
        return False, "drop_reply", tweet_data

    # F-04: 自己的串帖续贴
    if reply_to_user == target_user_id:
        tweet_data["tweet_type"] = "thread_continuation"
        logger.debug(f"F-04 drop_thread: {tweet_id}")
        return False, "drop_thread", tweet_data

    # F-05 / F-06: 纯图无字 / 空内容
    clean_text = process_tweet(raw_text, max_length=max_content_length)
    if "photo" in media_types and not clean_text.strip():
        logger.debug(f"F-05 drop_image_only: {tweet_id}")
        return False, "drop_image_only", tweet_data
    if not clean_text.strip():
        logger.debug(f"F-06 drop_empty: {tweet_id}")
        return False, "drop_empty", tweet_data

    # F-07: 个人引流链接（用原文，避免 URL 被剥掉）
    if has_personal_link(raw_text):
        logger.debug(f"F-07 drop_personal_link: {tweet_id}")
        return False, "drop_personal_link", tweet_data

    # F-08: 推广 / 非行情
    if has_promo_or_offtopic(raw_text) or has_promo_or_offtopic(clean_text):
        logger.debug(f"F-08 drop_offtopic: {tweet_id}")
        return False, "drop_offtopic", tweet_data

    tweet_data["content_clean"] = clean_text
    tweet_data["filter_result"] = "pass"
    tweet_data["status"] = "pending"
    logger.info(f"Tweet {tweet_id} passed filter, text: {clean_text[:80]}...")
    return True, "pass", tweet_data
