from modules import db
from modules.processor import process_tweet
from loguru import logger


def get_media_types(tweet):
    """Extract media types from tweet object."""
    media_list = []
    legacy = tweet.get("legacy", {})

    # Check extended_entities first (more reliable), then entities
    for source in [legacy.get("extended_entities", {}), legacy.get("entities", {})]:
        for m in source.get("media", []):
            media_list.append(m.get("type", ""))

    return media_list

def get_image_urls(tweet, max_images=4):
    """从推文对象提取最多 4 张图片直链。"""
    urls = []
    legacy = tweet.get("legacy", {})
    for source in (legacy.get("extended_entities") or {}, legacy.get("entities") or {}):
        for m in source.get("media") or []:
            if m.get("type") != "photo":
                continue
            u = m.get("media_url_https") or m.get("media_url")
            if not u or u in urls:
                continue
            # 尽量要原图
            if "pbs.twimg.com" in u and "name=" not in u:
                u = u + ("&" if "?" in u else "?") + "name=orig"
            urls.append(u)
            if len(urls) >= max_images:
                return urls
    return urls


def get_tweet_text(tweet):
    """Get the full text from a tweet object."""
    legacy = tweet.get("legacy", {})
    return legacy.get("full_text", "") or tweet.get("text", "")


def filter_tweet(tweet, target_user_id, max_content_length=900):
    """
    Apply filter chain F-00 through F-06.
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
        "image_urls": get_image_urls(tweet),  # ← 新增
    }

    # F-00: Dedup check
    if db.tweet_exists(tweet_id):
        logger.debug(f"F-00 dedup: {tweet_id}")
        return False, "dedup", tweet_data

    # F-01: Video
    if "video" in media_types or "animated_gif" in media_types:
        tweet_data["tweet_type"] = "original"
        logger.debug(f"F-01 drop_video: {tweet_id}")
        return False, "drop_video", tweet_data

    # F-02: Retweet
    if legacy.get("retweeted_status_result") or raw_text.startswith("RT @"):
        tweet_data["tweet_type"] = "retweet"
        logger.debug(f"F-02 drop_rt: {tweet_id}")
        return False, "drop_rt", tweet_data

    # F-03: Reply to other
    reply_to_user = legacy.get("in_reply_to_user_id_str", "")
    if reply_to_user and reply_to_user != target_user_id:
        tweet_data["tweet_type"] = "reply"
        logger.debug(f"F-03 drop_reply: {tweet_id}")
        return False, "drop_reply", tweet_data

    # F-04: Thread continuation (self-reply)
    if reply_to_user == target_user_id:
        tweet_data["tweet_type"] = "thread_continuation"
        logger.debug(f"F-04 drop_thread: {tweet_id}")
        return False, "drop_thread", tweet_data

    # F-05: Image-only (has images but no text after URL stripping)
    clean_text = process_tweet(raw_text, max_length=max_content_length)
    if "photo" in media_types and not clean_text.strip():
        logger.debug(f"F-05 drop_image_only: {tweet_id}")
        return False, "drop_image_only", tweet_data

    # F-06: Empty body
    if not clean_text.strip():
        logger.debug(f"F-06 drop_empty: {tweet_id}")
        return False, "drop_empty", tweet_data

    # PASS
    tweet_data["content_clean"] = clean_text
    tweet_data["filter_result"] = "pass"
    tweet_data["status"] = "pending"
    logger.info(f"Tweet {tweet_id} passed filter, text: {clean_text[:80]}...")
    return True, "pass", tweet_data
