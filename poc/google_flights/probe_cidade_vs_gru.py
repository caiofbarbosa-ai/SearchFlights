"""Probe: cidade (São Paulo) vs aeroporto específico (GRU) — explicar o
R$ 13.677 do usuário vs R$ 16.432 do scraper (8.216/pax)."""

import asyncio
import sys

sys.path.insert(0, ".")
from datetime import date

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.scrapers.google_flights import build_q_url, _parse_prices

D, R = date(2027, 7, 21), date(2027, 7, 28)


async def probe(p, label: str, origin: str):
    browser = await p.chromium.launch(
        headless=False, args=["--disable-blink-features=AutomationControlled"])
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080}, locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"))
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)
    url = build_q_url(origin, "BKK", D, R)
    await page.goto(url, timeout=90_000)
    body = ""
    for _ in range(15):
        await asyncio.sleep(3)
        body = await page.evaluate(
            "() => document.body ? document.body.innerText : ''")
        if len(_parse_prices(body)) >= 3:
            break
    prices = _parse_prices(body)
    print(f"{label}: min por pessoa = R$ {prices[0] if prices else '—'} | "
          f"total 2 adultos = R$ {prices[0]*2 if prices else '—'} | "
          f"distintas: {prices[:6]}")
    await context.close()
    await browser.close()


async def main():
    async with async_playwright() as p:
        await probe(p, "GRU (aeroporto específico)", "GRU")
        await asyncio.sleep(8)
        await probe(p, "São Paulo (cidade)", "São Paulo")


if __name__ == "__main__":
    asyncio.run(main())
