import httpx
from playwright.async_api import async_playwright
import random
import asyncio

from .config_mannger import get_apikey


async def fetch_player_data(player_id: str,
                            chat_id: str,
                            platform: str = "uplay") -> dict:
    url = "https://api.r6data.eu/api/stats"

    params = {
        "type": "operatorStats",
        "nameOnPlatform": player_id,
        "platformType": platform,
    }

    api_key = get_apikey(chat_id)

    if not api_key:
        return {"error": "未设置 API Key，请使用 /R6DAPI"}
    headers = {"api-key": api_key,
               "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    except httpx.HTTPError as e:
        return {"error": str(e)}


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
        await page.wait_for_selector("text=All Matches, text=No matches found for the selected filters.",
                                     timeout=30_000)

        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(300, 700))
            await asyncio.sleep(random.uniform(0.5, 1.2))

        html = await page.content()

        await browser.close()
        return html
