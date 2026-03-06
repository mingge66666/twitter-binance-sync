#!/usr/bin/env python3
"""
配置完整性校验：检查 .env、config.yaml、cookies、Docker 是否就绪。
内置在生成的项目中，无需额外依赖（纯标准库）。

用法:
    python3 validate_config.py
    python3 validate_config.py --project-dir /path/to/project
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from urllib.parse import unquote


def check_file_exists(path, label):
    if os.path.exists(path):
        print(f"  [OK] {label}: {path}")
        return True
    else:
        print(f"  [FAIL] {label}: {path} -- NOT FOUND")
        return False


def validate_env(project_dir):
    """Check .env file for required variables."""
    print("\n== .env ==")
    env_path = os.path.join(project_dir, ".env")
    if not check_file_exists(env_path, ".env"):
        return False

    ok = True
    required_vars = {
        "BINANCE_SQUARE_API_KEY": None,
    }
    optional_vars = {
        "DISCORD_BOT_TOKEN": None,
        "DISCORD_CHANNEL_ID": None,
    }

    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key in required_vars:
                    required_vars[key] = value
                if key in optional_vars:
                    optional_vars[key] = value

    for var, value in required_vars.items():
        if value:
            masked = value[:4] + "..." + value[-4:] if len(value) > 12 else "***"
            print(f"  [OK] {var} = {masked}")
        else:
            print(f"  [FAIL] {var} -- empty or missing (required)")
            ok = False

    for var, value in optional_vars.items():
        if value:
            masked = value[:4] + "..." + value[-4:] if len(value) > 12 else "***"
            print(f"  [OK] {var} = {masked}")
        else:
            print(f"  [WARN] {var} -- empty (Discord notifications will be disabled)")

    return ok


def validate_config(project_dir):
    """Check config.yaml for valid structure (no PyYAML dependency)."""
    print("\n== config.yaml ==")
    config_path = os.path.join(project_dir, "config.yaml")
    if not check_file_exists(config_path, "config.yaml"):
        return False

    ok = True
    with open(config_path, "r") as f:
        content = f.read()

    # Check for unreplaced placeholders
    if "{{" in content:
        placeholders = re.findall(r'\{\{[^}]+\}\}', content)
        print(f"  [FAIL] Unreplaced placeholders found: {', '.join(placeholders)}")
        print("         Run init_project.py or manually replace them in config.yaml")
        ok = False
    else:
        print("  [OK] No unreplaced placeholders")

    # Check username is set
    username_match = re.search(r'username:\s*["\']?([^"\'\n]+)', content)
    if username_match:
        username = username_match.group(1).strip()
        print(f"  [OK] twitter.username = {username}")
    else:
        print("  [FAIL] twitter.username not found")
        ok = False

    # Check required sections exist
    for section in ["binance_square", "scheduler", "limits", "logging"]:
        if re.search(rf'^{section}:', content, re.MULTILINE):
            print(f"  [OK] section '{section}' present")
        else:
            print(f"  [FAIL] section '{section}' missing")
            ok = False

    return ok


def validate_cookies(project_dir):
    """Check cookies file for required cookies."""
    print("\n== cookies ==")
    cookies_path = os.path.join(project_dir, "cookies", "twitter.json")
    if not check_file_exists(cookies_path, "cookies/twitter.json"):
        print("         Export cookies from x.com using Cookie-Editor browser extension,")
        print("         then save the JSON to cookies/twitter.json")
        return False

    ok = True
    with open(cookies_path, "r") as f:
        cookies = json.load(f)

    if not isinstance(cookies, list):
        print("  [FAIL] cookies file is not a JSON array")
        print("         Paste the ENTIRE Cookie-Editor export (a JSON array), not just individual cookies")
        return False

    print(f"  [OK] {len(cookies)} cookies loaded")

    # Check required cookies
    cookie_map = {c["name"]: c for c in cookies}
    required = ["auth_token", "ct0", "twid"]
    for name in required:
        if name in cookie_map:
            print(f"  [OK] cookie '{name}' present")
        else:
            print(f"  [FAIL] cookie '{name}' missing -- required for Twitter auth")
            ok = False

    # Check for placeholder values in all required cookies
    for name in required:
        if name in cookie_map and "YOUR_" in cookie_map[name].get("value", ""):
            print(f"  [FAIL] cookie '{name}' still has placeholder value")
            print(f"         Replace with real values from Cookie-Editor export")
            ok = False

    # Extract user ID from twid
    if "twid" in cookie_map:
        decoded = unquote(cookie_map["twid"]["value"])
        if decoded.startswith("u="):
            user_id = decoded[2:]
            print(f"  [OK] browsing user ID (from twid): {user_id}")
        else:
            print(f"  [WARN] twid cookie has unexpected format: {cookie_map['twid']['value']}")

    # Check cookie expiration
    now_ts = time.time()
    for name in required:
        if name in cookie_map:
            exp = cookie_map[name].get("expirationDate")
            if exp and exp < now_ts:
                print(f"  [FAIL] cookie '{name}' is expired (expired at {exp})")
                print("         Re-export cookies from x.com using Cookie-Editor")
                ok = False

    # Warn if cookies are from twitter.com instead of x.com
    domains = {c.get("domain", "") for c in cookies}
    if any("twitter.com" in d for d in domains) and not any("x.com" in d for d in domains):
        print("  [WARN] Cookies appear to be from twitter.com domain, not x.com")
        print("         Make sure to export cookies while on x.com (not twitter.com)")

    return ok


def validate_docker(project_dir):
    """Check Docker files and Docker installation."""
    print("\n== Docker ==")
    ok = True
    ok &= check_file_exists(os.path.join(project_dir, "Dockerfile"), "Dockerfile")
    ok &= check_file_exists(os.path.join(project_dir, "docker-compose.yml"), "docker-compose.yml")
    ok &= check_file_exists(os.path.join(project_dir, "requirements.txt"), "requirements.txt")

    # Check Docker is installed
    try:
        result = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"  [OK] {result.stdout.strip()}")
        else:
            print("  [FAIL] Docker is installed but returned an error")
            ok = False
    except FileNotFoundError:
        print("  [FAIL] Docker is not installed")
        print("         Install Docker: curl -fsSL https://get.docker.com | sh")
        ok = False
    except subprocess.TimeoutExpired:
        print("  [WARN] Docker version check timed out")

    # Check docker compose is available
    try:
        result = subprocess.run(
            ["docker", "compose", "version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"  [OK] {result.stdout.strip()}")
        else:
            print("  [FAIL] 'docker compose' plugin not available")
            print("         Upgrade Docker or install the compose plugin")
            ok = False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  [WARN] Could not verify docker compose")

    return ok


def main():
    parser = argparse.ArgumentParser(description="Validate twitter-binance-sync project configuration")
    parser.add_argument("--project-dir", default=".", help="Path to the project directory (default: current dir)")
    args = parser.parse_args()

    project_dir = os.path.expanduser(args.project_dir)
    if not os.path.isdir(project_dir):
        print(f"[ERROR] Directory not found: {project_dir}")
        sys.exit(1)

    print(f"Validating project at: {project_dir}")

    results = {
        ".env": validate_env(project_dir),
        "config.yaml": validate_config(project_dir),
        "cookies": validate_cookies(project_dir),
        "docker": validate_docker(project_dir),
    }

    print("\n== Summary ==")
    all_ok = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_ok = False

    if all_ok:
        print("\nAll checks passed! Ready to deploy:")
        print("  docker compose up -d --build")
    else:
        print("\nSome checks failed. Fix the issues above before deploying.")
        sys.exit(1)


if __name__ == "__main__":
    main()
