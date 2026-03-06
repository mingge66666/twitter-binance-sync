import sqlite3
import json
from datetime import datetime, timezone, timedelta
from loguru import logger

UTC8 = timezone(timedelta(hours=8))


def get_connection(db_path="./db/state.sqlite"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path="./db/state.sqlite"):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tweets (
            tweet_id TEXT PRIMARY KEY,
            content_raw TEXT,
            content_clean TEXT,
            has_images INTEGER DEFAULT 0,
            has_video INTEGER DEFAULT 0,
            tweet_type TEXT,
            filter_result TEXT,
            fetched_at TEXT,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            published_at TEXT,
            square_post_id TEXT,
            square_post_url TEXT,
            error_code TEXT,
            error_msg TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT,
            fetched_count INTEGER DEFAULT 0,
            passed_filter INTEGER DEFAULT 0,
            published_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            retried_count INTEGER DEFAULT 0,
            skipped_count INTEGER DEFAULT 0,
            duration_seconds REAL,
            error_summary TEXT
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized")


def get_sync_state(key, db_path="./db/state.sqlite"):
    conn = get_connection(db_path)
    row = conn.execute("SELECT value FROM sync_state WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def set_sync_state(key, value, db_path="./db/state.sqlite"):
    now = datetime.now(UTC8).isoformat()
    conn = get_connection(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES (?, ?, ?)",
        (key, str(value), now)
    )
    conn.commit()
    conn.close()


def tweet_exists(tweet_id, db_path="./db/state.sqlite"):
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT status FROM tweets WHERE tweet_id = ?", (tweet_id,)
    ).fetchone()
    conn.close()
    if row and row["status"] in ("published", "skipped"):
        return True
    return False


def get_tweet_status(tweet_id, db_path="./db/state.sqlite"):
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT status, retry_count FROM tweets WHERE tweet_id = ?", (tweet_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_tweet(tweet_data, db_path="./db/state.sqlite"):
    now = datetime.now(UTC8).isoformat()
    conn = get_connection(db_path)
    conn.execute("""
        INSERT OR IGNORE INTO tweets
        (tweet_id, content_raw, content_clean, has_images, has_video,
         tweet_type, filter_result, fetched_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tweet_data["tweet_id"],
        tweet_data.get("content_raw", ""),
        tweet_data.get("content_clean", ""),
        tweet_data.get("has_images", 0),
        tweet_data.get("has_video", 0),
        tweet_data.get("tweet_type", "original"),
        tweet_data.get("filter_result", "pending"),
        now,
        tweet_data.get("status", "pending"),
    ))
    conn.commit()
    conn.close()


_ALLOWED_COLUMNS = {
    "status", "published_at", "square_post_id", "square_post_url",
    "retry_count", "error_code", "error_msg", "filter_result",
}


def update_tweet_status(tweet_id, db_path="./db/state.sqlite", **kwargs):
    conn = get_connection(db_path)
    sets = []
    vals = []
    for k, v in kwargs.items():
        if k not in _ALLOWED_COLUMNS:
            raise ValueError(f"Invalid column name: {k}")
        sets.append(f"{k} = ?")
        vals.append(v)
    vals.append(tweet_id)
    conn.execute(
        f"UPDATE tweets SET {', '.join(sets)} WHERE tweet_id = ?", vals
    )
    conn.commit()
    conn.close()


def get_failed_tweets(max_retries=3, db_path="./db/state.sqlite"):
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM tweets WHERE status = 'failed' AND retry_count < ?",
        (max_retries,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_run_log(log_data, db_path="./db/state.sqlite"):
    conn = get_connection(db_path)
    conn.execute("""
        INSERT INTO run_logs
        (run_at, fetched_count, passed_filter, published_count,
         failed_count, retried_count, skipped_count, duration_seconds, error_summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_data.get("run_at", datetime.now(UTC8).isoformat()),
        log_data.get("fetched_count", 0),
        log_data.get("passed_filter", 0),
        log_data.get("published_count", 0),
        log_data.get("failed_count", 0),
        log_data.get("retried_count", 0),
        log_data.get("skipped_count", 0),
        log_data.get("duration_seconds", 0),
        json.dumps(log_data.get("errors", []), ensure_ascii=False),
    ))
    conn.commit()
    conn.close()


def get_daily_stats(date_str=None, db_path="./db/state.sqlite"):
    if date_str is None:
        date_str = datetime.now(UTC8).strftime("%Y-%m-%d")

    conn = get_connection(db_path)

    stats = {}
    for status in ["published", "failed", "dead", "skipped"]:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM tweets WHERE status = ? AND fetched_at LIKE ?",
            (status, f"{date_str}%")
        ).fetchone()
        stats[status] = row["cnt"] if row else 0

    # Filtered count (all drop_* filter results)
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM tweets WHERE filter_result LIKE 'drop_%' AND fetched_at LIKE ?",
        (f"{date_str}%",)
    ).fetchone()
    stats["filtered"] = row["cnt"] if row else 0

    # Retried
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM tweets WHERE retry_count > 0 AND fetched_at LIKE ?",
        (f"{date_str}%",)
    ).fetchone()
    stats["retried"] = row["cnt"] if row else 0

    # Run logs
    rows = conn.execute(
        "SELECT * FROM run_logs WHERE run_at LIKE ?", (f"{date_str}%",)
    ).fetchall()
    stats["cycles"] = len(rows)
    if rows:
        durations = [r["duration_seconds"] for r in rows if r["duration_seconds"]]
        stats["avg_duration"] = round(sum(durations) / len(durations), 1) if durations else 0
    else:
        stats["avg_duration"] = 0

    conn.close()
    return stats
