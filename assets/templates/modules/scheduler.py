import time
import asyncio
from datetime import datetime, timezone, timedelta
from loguru import logger

from modules import db, fetcher, filter as tweet_filter, processor, publisher, notifier

UTC8 = timezone(timedelta(hours=8))


def get_target_user_id(tweets):
    """Extract the target profile's user ID from fetched tweets."""
    for t in tweets:
        core = t.get("core", {})
        user_result = core.get("user_results", {}).get("result", {})
        uid = user_result.get("rest_id", "")
        if uid:
            return uid
    return None


async def sync_cycle(config):
    """Main sync cycle: fetch -> filter -> process -> publish."""
    run_start = datetime.now(UTC8)
    logger.info("=" * 50)
    logger.info(f"Sync cycle started at {run_start.isoformat()}")

    errors = []
    stats = {
        "run_at": run_start.isoformat(),
        "fetched_count": 0,
        "passed_filter": 0,
        "published_count": 0,
        "failed_count": 0,
        "retried_count": 0,
        "skipped_count": 0,
        "errors": [],
    }

    halt_today = db.get_sync_state("halt_publishing_today") == "1"
    last_tweet_id = db.get_sync_state("last_tweet_id")

    # Step 1: Flush Discord queue
    await notifier.flush_queue()

    # Step 2: Process retry queue (unless halted)
    if not halt_today:
        failed_tweets = db.get_failed_tweets(max_retries=config["limits"]["max_retries"])
        for ft in failed_tweets:
            stats["retried_count"] += 1
            api_endpoint = config["binance_square"]["api_endpoint"]
            delay = config["binance_square"]["inter_request_delay_seconds"]

            success, result = await publisher.publish_to_square(
                ft["content_clean"], api_endpoint, delay
            )

            if success:
                db.update_tweet_status(
                    ft["tweet_id"],
                    status="published",
                    published_at=datetime.now(UTC8).isoformat(),
                    square_post_id=result.get("square_post_id", ""),
                    square_post_url=result.get("square_post_url", ""),
                    retry_count=ft["retry_count"] + 1,
                )
                stats["published_count"] += 1
                logger.info(f"Retry published: {ft['tweet_id']}")
            else:
                new_retry = ft["retry_count"] + 1
                if result.get("halt_today"):
                    db.set_sync_state("halt_publishing_today", "1")
                    halt_today = True
                    notifier.send_alert(
                        "Binance Square daily limit reached. Publishing paused until midnight.",
                        "WARNING"
                    )
                    break

                if result.get("halt_permanent"):
                    notifier.send_alert(
                        f"Binance Square API key error {result.get('error_code')}. Publishing halted.",
                        "CRITICAL"
                    )
                    break

                if new_retry >= config["limits"]["max_retries"]:
                    db.update_tweet_status(
                        ft["tweet_id"],
                        status="dead",
                        retry_count=new_retry,
                        error_code=result.get("error_code", ""),
                        error_msg=result.get("error_msg", ""),
                    )
                    notifier.send_alert(
                        f"Tweet {ft['tweet_id']} failed permanently after {new_retry} retries. "
                        f"Error: {result.get('error_code')} -- {result.get('error_msg')}",
                        "ERROR"
                    )
                    stats["failed_count"] += 1
                else:
                    db.update_tweet_status(
                        ft["tweet_id"],
                        status="failed",
                        retry_count=new_retry,
                        error_code=result.get("error_code", ""),
                        error_msg=result.get("error_msg", ""),
                    )

            await asyncio.sleep(config["binance_square"]["inter_request_delay_seconds"])

    # Step 3: Fetch new tweets
    raw_tweets, auth_error = await fetcher.fetch_tweets(config)

    if auth_error:
        notifier.send_alert(
            f"Twitter session invalid: {auth_error}. Manual cookie refresh required.",
            "CRITICAL"
        )
        errors.append(f"auth_error: {auth_error}")
        stats["errors"] = errors
        duration = (datetime.now(UTC8) - run_start).total_seconds()
        stats["duration_seconds"] = duration
        db.save_run_log(stats)
        db.set_sync_state("last_run_at", datetime.now(UTC8).isoformat())
        return

    stats["fetched_count"] = len(raw_tweets)

    if not raw_tweets:
        logger.info("No tweets fetched this cycle")
        duration = (datetime.now(UTC8) - run_start).total_seconds()
        stats["duration_seconds"] = duration
        db.save_run_log(stats)
        db.set_sync_state("last_run_at", datetime.now(UTC8).isoformat())
        return

    # Determine target user ID from tweets
    target_user_id = get_target_user_id(raw_tweets)
    if not target_user_id:
        logger.warning("Could not determine target user ID from tweets")
        target_user_id = ""

    # Step 4-5: Filter and process each tweet
    highest_tweet_id = last_tweet_id
    today_str = datetime.now(UTC8).strftime("%Y-%m-%d")

    tweets_to_publish = []

    for tweet in raw_tweets:
        tweet_id = tweet.get("rest_id", "")
        if not tweet_id:
            continue

        # Skip tweets we've already processed (cursor-based)
        if last_tweet_id and int(tweet_id) <= int(last_tweet_id):
            continue

        # On first run, only process today's tweets
        if not last_tweet_id:
            created_at = tweet.get("legacy", {}).get("created_at", "")
            if created_at:
                try:
                    tweet_dt = datetime.strptime(
                        created_at, "%a %b %d %H:%M:%S %z %Y"
                    )
                    tweet_date = tweet_dt.astimezone(UTC8).strftime("%Y-%m-%d")
                    if tweet_date != today_str:
                        continue
                except ValueError:
                    pass

        # Track highest tweet_id
        if not highest_tweet_id or int(tweet_id) > int(highest_tweet_id):
            highest_tweet_id = tweet_id

        # Apply filter
        max_len = config["binance_square"].get("max_content_length", 900)
        passed, filter_result, tweet_data = tweet_filter.filter_tweet(tweet, target_user_id, max_content_length=max_len)

        if not passed:
            if filter_result != "dedup":
                tweet_data["filter_result"] = filter_result
                tweet_data["status"] = "skipped"
                db.save_tweet(tweet_data)
                stats["skipped_count"] += 1
            continue

        stats["passed_filter"] += 1
        tweets_to_publish.append(tweet_data)

    # Step 6: Publish to Binance Square
    if not halt_today:
        api_endpoint = config["binance_square"]["api_endpoint"]
        delay = config["binance_square"]["inter_request_delay_seconds"]

        for tweet_data in tweets_to_publish:
            # Save as pending first
            db.save_tweet(tweet_data)

            success, result = await publisher.publish_to_square(
                tweet_data["content_clean"], api_endpoint, delay
            )

            if success:
                db.update_tweet_status(
                    tweet_data["tweet_id"],
                    status="published",
                    published_at=datetime.now(UTC8).isoformat(),
                    square_post_id=result.get("square_post_id", ""),
                    square_post_url=result.get("square_post_url", ""),
                )
                stats["published_count"] += 1
            else:
                if result.get("skip_permanent"):
                    db.update_tweet_status(
                        tweet_data["tweet_id"],
                        status="skipped",
                        filter_result="sensitive_content",
                        error_code=result.get("error_code", ""),
                        error_msg=result.get("error_msg", ""),
                    )
                    notifier.send_alert(
                        f"Tweet {tweet_data['tweet_id']} rejected by Square (sensitive content). Skipped.",
                        "WARNING"
                    )
                    stats["skipped_count"] += 1
                elif result.get("halt_today"):
                    db.set_sync_state("halt_publishing_today", "1")
                    halt_today = True
                    notifier.send_alert(
                        "Binance Square daily limit reached. Publishing paused until midnight.",
                        "WARNING"
                    )
                    # Save remaining as pending
                    break
                elif result.get("halt_permanent"):
                    notifier.send_alert(
                        f"Binance Square API key error {result.get('error_code')}. Publishing halted.",
                        "CRITICAL"
                    )
                    break
                else:
                    db.update_tweet_status(
                        tweet_data["tweet_id"],
                        status="failed",
                        error_code=result.get("error_code", ""),
                        error_msg=result.get("error_msg", ""),
                    )
                    stats["failed_count"] += 1

            await asyncio.sleep(delay)
    else:
        # Halted -- save tweets as pending for next day
        for tweet_data in tweets_to_publish:
            db.save_tweet(tweet_data)
        logger.info(f"Publishing halted today, {len(tweets_to_publish)} tweets saved as pending")

    # Step 7: Update cursor
    if highest_tweet_id:
        db.set_sync_state("last_tweet_id", highest_tweet_id)

    # Step 8: Write run log
    duration = (datetime.now(UTC8) - run_start).total_seconds()
    stats["duration_seconds"] = duration
    stats["errors"] = errors
    db.save_run_log(stats)
    db.set_sync_state("last_run_at", datetime.now(UTC8).isoformat())

    logger.info(
        f"Cycle complete in {duration:.1f}s: "
        f"fetched={stats['fetched_count']}, passed={stats['passed_filter']}, "
        f"published={stats['published_count']}, failed={stats['failed_count']}, "
        f"skipped={stats['skipped_count']}"
    )


def daily_digest():
    """Send daily digest via Discord."""
    stats = db.get_daily_stats()
    notifier.send_daily_digest(stats)
    logger.info("Daily digest sent")


def midnight_reset():
    """Reset daily counters at midnight UTC+8."""
    today = datetime.now(UTC8).strftime("%Y-%m-%d")
    db.set_sync_state("halt_publishing_today", "0")
    db.set_sync_state("daily_publish_count", "0")
    db.set_sync_state("daily_count_date", today)
    logger.info(f"Daily counters reset for {today}")
