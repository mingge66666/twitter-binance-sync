import re
from loguru import logger


URL_PATTERN = re.compile(r'https?://\S+')


def process_tweet(raw_text, max_length=900):
    """Strip URLs, normalize whitespace, truncate if needed."""
    # Step 1: Strip URLs
    text = URL_PATTERN.sub('', raw_text)

    # Step 2: Normalize whitespace
    # Replace multiple spaces with single space
    text = re.sub(r'[^\S\n]+', ' ', text)
    # Replace 3+ consecutive newlines with 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip leading/trailing whitespace
    text = text.strip()

    # Step 3: Truncate if exceeds max length
    if len(text) > max_length:
        truncated = text[:max_length]
        # Cut at last complete word
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        text = truncated.rstrip() + "..."
        logger.warning(f"Tweet truncated from {len(raw_text)} to {len(text)} chars")

    return text
