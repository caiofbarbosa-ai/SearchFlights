"""Probe: patchright (CDP-leaks corrigidos) + Chrome real recebe o piso
de 6.839 que o Google esconde das sessões Playwright?"""

import asyncio
import sys

sys.path.insert(0, ".")
from datetime import date

from patchright.async_api import async_playwright

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
            timezone_id="America/Sao_Paulo")
        page = await context.new_page()

        await page.goto(build_q_url("GRU", "BKK", D, R), timeout=90_000)
        body = ""
        floor = None
        for i in range(20):  # ~60s
            await asyncio.sleep(3)
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            prices = _parse_prices(body)
            if not prices:
                continue
            if floor is None or prices[0] < floor:
                if floor is not None:
                    log(f"    ONDA: R$ {floor:,} -> R$ {prices[0]:,}"
                        .replace(",", "."))
                floor = prices[0]
            if i % 5 == 0:
                log(f"... {i*3}s piso: "
                    + (f"R$ {floor:,}".replace(",", ".") if floor
                       else "sem preços"))

        log(f"RESULTADO patchright: piso = "
            + (f"R$ {floor:,}".replace(",", ".") if floor else "sem preços"))
        log("✅ 6.839 visto" if floor and floor <= 7000
            else "❌ patchright também recebeu o conjunto degradado")
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
