#!/usr/bin/env python3
"""
运行状态检查：检查 Docker 容器、最近运行记录、游标位置。

用法:
    python health_check.py --project-dir ~/my-sync-project
    python health_check.py --project-dir ~/my-sync-project --container-name twitter-sync
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone, timedelta

UTC8 = timezone(timedelta(hours=8))


def check_container(container_name):
    """Check Docker container status."""
    print(f"\n== Docker Container: {container_name} ==")
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            status = result.stdout.strip()
            if status == "running":
                print(f"  [OK] Container status: {status}")

                # Get uptime
                result2 = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.StartedAt}}", container_name],
                    capture_output=True, text=True, timeout=10
                )
                if result2.returncode == 0:
                    started = result2.stdout.strip()
                    print(f"  [OK] Started at: {started}")

                return True
            else:
                print(f"  [WARN] Container status: {status}")
                return False
        else:
            print(f"  [FAIL] Container not found: {container_name}")
            return False
    except FileNotFoundError:
        print("  [SKIP] Docker not installed or not in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("  [FAIL] Docker command timed out")
        return False


def check_database(project_dir):
    """Check database for recent activity."""
    print("\n== Database ==")
    db_path = os.path.join(project_dir, "db", "state.sqlite")
    if not os.path.exists(db_path):
        print(f"  [WARN] Database not found: {db_path}")
        print("         (Normal if service hasn't run yet)")
        return True

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Last run
    row = conn.execute(
        "SELECT value FROM sync_state WHERE key = 'last_run_at'"
    ).fetchone()
    if row:
        last_run = row["value"]
        print(f"  [OK] Last run: {last_run}")

        # Check if last run was recent (within 2 hours)
        try:
            last_dt = datetime.fromisoformat(last_run)
            age_minutes = (datetime.now(UTC8) - last_dt).total_seconds() / 60
            if age_minutes < 120:
                print(f"  [OK] Last run was {age_minutes:.0f} minutes ago")
            else:
                hours = age_minutes / 60
                print(f"  [WARN] Last run was {hours:.1f} hours ago")
        except ValueError:
            pass
    else:
        print("  [INFO] No runs recorded yet")

    # Cursor position
    row = conn.execute(
        "SELECT value FROM sync_state WHERE key = 'last_tweet_id'"
    ).fetchone()
    if row:
        print(f"  [OK] Cursor (last_tweet_id): {row['value']}")
    else:
        print("  [INFO] No cursor set yet")

    # Halt status
    row = conn.execute(
        "SELECT value FROM sync_state WHERE key = 'halt_publishing_today'"
    ).fetchone()
    if row and row["value"] == "1":
        print("  [WARN] Publishing is HALTED today (daily limit reached)")
    else:
        print("  [OK] Publishing is active")

    # Today's stats
    today = datetime.now(UTC8).strftime("%Y-%m-%d")
    stats = {}
    for status in ["published", "failed", "dead", "skipped", "pending"]:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM tweets WHERE status = ? AND fetched_at LIKE ?",
            (status, f"{today}%")
        ).fetchone()
        stats[status] = row["cnt"] if row else 0

    print(f"\n  Today's stats ({today}):")
    print(f"    Published: {stats['published']}")
    print(f"    Pending:   {stats['pending']}")
    print(f"    Failed:    {stats['failed']}")
    print(f"    Dead:      {stats['dead']}")
    print(f"    Skipped:   {stats['skipped']}")

    # Recent run logs
    rows = conn.execute(
        "SELECT * FROM run_logs ORDER BY id DESC LIMIT 3"
    ).fetchall()
    if rows:
        print("\n  Recent runs:")
        for r in rows:
            print(
                f"    {r['run_at']} | "
                f"fetched={r['fetched_count']} passed={r['passed_filter']} "
                f"published={r['published_count']} failed={r['failed_count']} "
                f"({r['duration_seconds']:.1f}s)"
            )

    # Failed tweets in retry queue
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM tweets WHERE status = 'failed'"
    ).fetchone()
    retry_count = row["cnt"] if row else 0
    if retry_count > 0:
        print(f"\n  [INFO] {retry_count} tweets in retry queue")

    conn.close()
    return True


def check_logs(project_dir):
    """Check for recent log activity."""
    print("\n== Logs ==")
    log_path = os.path.join(project_dir, "logs", "sync.log")
    if not os.path.exists(log_path):
        print(f"  [INFO] Log file not found: {log_path}")
        return True

    size = os.path.getsize(log_path)
    print(f"  [OK] Log file size: {size / 1024:.1f} KB")

    # Read last 5 lines
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            last_lines = lines[-5:] if len(lines) >= 5 else lines
            print("  Last log entries:")
            for line in last_lines:
                print(f"    {line.rstrip()}")
    except Exception as e:
        print(f"  [WARN] Could not read log: {e}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Check twitter-binance-sync service health")
    parser.add_argument("--project-dir", required=True, help="Path to the project directory")
    parser.add_argument("--container-name", default="twitter-sync", help="Docker container name")
    args = parser.parse_args()

    project_dir = os.path.expanduser(args.project_dir)
    if not os.path.isdir(project_dir):
        print(f"[ERROR] Directory not found: {project_dir}")
        sys.exit(1)

    print(f"Health check for: {project_dir}")

    check_container(args.container_name)
    check_database(project_dir)
    check_logs(project_dir)

    print("\n== Done ==")


if __name__ == "__main__":
    main()
