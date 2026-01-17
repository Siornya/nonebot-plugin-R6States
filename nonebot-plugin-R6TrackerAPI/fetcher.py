from playwright.async_api import async_playwright
import random
import asyncio

async def fetch_overview(player_id: str) -> str:
    """
    获取Overview数据，由于页面中Matches部分最后加载，所以等待显示All Matches以后保存
    :param player_id:玩家id
    :return:完整html文本
    """
    url = f"https://r6.tracker.network/r6siege/profile/ubi/{player_id}/overview"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"
        )

        await page.goto(url, timeout=60_000)
        await page.wait_for_selector("text=All Matches", timeout=30_000)

        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(300, 700))
            await asyncio.sleep(random.uniform(0.5, 1.2))

        html = await page.content()

        await browser.close()
        return html