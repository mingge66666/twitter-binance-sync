import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from loguru import logger
def load_cookies(path: str):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for c in raw:
        item = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".x.com"),
            "path": c.get("path", "/"),
        }
        if c.get("expirationDate"):
            item["expires"] = c["expirationDate"]
        if c.get("httpOnly"):
            item["httpOnly"] = True
        if c.get("secure"):
            item["secure"] = True
        ss = (c.get("sameSite") or "").lower()
        if ss in ("no_restriction", "none"):
            item["sameSite"] = "None"
        elif ss == "lax":
            item["sameSite"] = "Lax"
        elif ss == "strict":
            item["sameSite"] = "Strict"
        out.append(item)
    return out
async def post_to_x(text: str, cookies_path: str) -> bool:
    """使用自己的 Cookie 在 X 发帖（纯文字）。"""
    if not text or not text.strip():
        return False
    if not Path(cookies_path).exists():
        logger.warning(f"未找到自己的 X Cookie 文件: {cookies_path}")
        return False

    t = text.strip()
    if len(t) > 280:
        t = t[:277] + "..."

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        await context.add_cookies(load_cookies(cookies_path))
        page = await context.new_page()
        try:
            await page.goto(
                "https://x.com/compose/post",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await asyncio.sleep(4)

            editor = page.locator(
                '[data-testid="tweetTextarea_0"], div[role="textbox"]'
            ).first
            await editor.wait_for(state="visible", timeout=20000)
            await editor.click()
            await editor.fill(t)
            await asyncio.sleep(1.5)

            btn = page.locator(
                '[data-testid="tweetButton"], [data-testid="tweetButtonInline"]'
            ).first
            await btn.click()
            await asyncio.sleep(5)
            logger.info("已发布到自己的 X 账号")
            return True
        except Exception as e:
            logger.error(f"发布到自己的 X 失败: {e}")
            return False
        finally:
            await browser.close()


