#!/usr/bin/env python3
"""
项目脚手架：从模板生成一个可部署的 twitter-binance-sync 项目。

用法:
    python init_project.py --twitter-username your_handle --output-dir ~/my-sync-project
"""

import argparse
import os
import shutil
import sys


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "templates")

PLACEHOLDER_MAP = {
    "{{TWITTER_USERNAME}}": None,  # filled at runtime
}

# Files that need placeholder replacement
TEMPLATED_FILES = [
    "config.yaml",
]

# Files to rename after copying
RENAME_MAP = {
    "config.yaml.template": "config.yaml",
    ".env.template": ".env",
}


def copy_templates(template_dir, output_dir):
    """Copy template directory to output, renaming template files."""
    if os.path.exists(output_dir):
        print(f"[ERROR] Output directory already exists: {output_dir}")
        print("        Remove it first or choose a different path.")
        sys.exit(1)

    shutil.copytree(template_dir, output_dir)

    # Rename template files
    for old_name, new_name in RENAME_MAP.items():
        old_path = os.path.join(output_dir, old_name)
        new_path = os.path.join(output_dir, new_name)
        if os.path.exists(old_path):
            os.rename(old_path, new_path)

    # Remove example cookie file (user needs to provide their own)
    example_cookie = os.path.join(output_dir, "cookies", "twitter.json.example")
    if os.path.exists(example_cookie):
        # Keep as reference, user will add their own twitter.json
        pass

    # Create required directories
    for d in ["db", "logs", "tmp"]:
        os.makedirs(os.path.join(output_dir, d), exist_ok=True)


def replace_placeholders(output_dir, replacements):
    """Replace placeholders in templated files."""
    for filename in TEMPLATED_FILES:
        filepath = os.path.join(output_dir, filename)
        if not os.path.exists(filepath):
            continue

        with open(filepath, "r") as f:
            content = f.read()

        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        with open(filepath, "w") as f:
            f.write(content)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a twitter-binance-sync project from templates"
    )
    parser.add_argument(
        "--twitter-username",
        required=True,
        help="Target Twitter username (without @)"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for the generated project"
    )
    args = parser.parse_args()

    username = args.twitter_username.lstrip("@")
    output_dir = os.path.expanduser(args.output_dir)
    template_dir = os.path.abspath(TEMPLATE_DIR)

    if not os.path.exists(template_dir):
        print(f"[ERROR] Template directory not found: {template_dir}")
        sys.exit(1)

    print(f"[1/3] Copying templates to {output_dir}")
    copy_templates(template_dir, output_dir)

    print(f"[2/3] Replacing placeholders (username: {username})")
    replacements = {
        "{{TWITTER_USERNAME}}": username,
    }
    replace_placeholders(output_dir, replacements)

    print("[3/3] Done!")
    print()
    print("Next steps:")
    print(f"  cd {output_dir}")
    print("  1. Edit .env  -- fill in BINANCE_SQUARE_API_KEY, DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID")
    print("  2. Copy your Cookie-Editor export to cookies/twitter.json")
    print("  3. docker compose up -d --build")
    print("  4. docker exec twitter-sync python main.py --test")


if __name__ == "__main__":
    main()
