"""Probe: Chrome REAL (channel=chrome) recebe as ondas de tarifa que o
Chromium embutido do Playwright não recebe? Janela 90s rastreando o piso."""

import asyncio
import sys

sys.path.insert(0, ".")
from datetime import date

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.scrapers.google_flights import build_q_url, _parse_prices

D, R = date(2027, 7, 21), date(2027, 7, 28)


def log(m):
    print(m, flush=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome", headless=False,
            args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/151.0.0.0 Safari/537.36"))
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        await page.goto(build_q_url("GRU", "BKK", D, R), timeout=90_000)
        body = ""
        floor = None
        for i in range(30):  # janela fixa ~90s
            await asyncio.sleep(3)
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            prices = _parse_prices(body)
            if not prices:
                continue
            if floor is None or prices[0] < floor:
                if floor is not None:
                    log(f"    onda mais barata: R$ {floor:,} -> "
                        f"R$ {prices[0]:,}".replace(",", "."))
                floor = prices[0]
            if i % 5 == 0:
                log(f"... {i*3}s piso corrente: "
                    f"R$ {floor:,}".replace(",", ".") if floor
                    else f"... {i*3}s sem preços ainda")

        log(f"RESULTADO Chrome real: piso = R$ {floor:,}".replace(",", ".")
            if floor else "RESULTADO: sem preços")
        log(f"esperado (usuário, anônimo): R$ 6.839")
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
