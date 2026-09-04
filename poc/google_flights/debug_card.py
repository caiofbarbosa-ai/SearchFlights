"""Debug: por que CARD_JS não encontra o cartão do voo mais barato."""

import asyncio
import sys

sys.path.insert(0, ".")
from datetime import date

from playwright.async_api import async_playwright

from src.scrapers.google_flights import CARD_JS, build_q_url, _parse_prices

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
        for _ in range(20):
            await asyncio.sleep(3)
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            prices = _parse_prices(body)
            if prices:
                if floor is None or prices[0] < floor:
                    floor = prices[0]
                if len(prices) >= 3 and floor and floor < 7000:
                    break
        label = f"R$ {floor:,}".replace(",", ".")
        log(f"piso: {floor} | label de busca: {label!r}")

        # 1. o label existe no body?
        log(f"label no body: {label in body}")

        # 2. quantos li/div contêm o label?
        n = await page.evaluate(
            """(label) => [...document.querySelectorAll('li, div')]
                .filter(e => e.offsetParent && e.innerText &&
                    e.innerText.includes(label)).length""", label)
        log(f"elementos com o label: {n}")

        # 3. CARD_JS em si
        try:
            card = await page.evaluate(CARD_JS, label)
            log(f"CARD_JS retorno: {repr(card)[:400]}")
        except Exception as e:
            log(f"CARD_JS ERRO: {e}")

        # 4. alternativa: menores com horário, sem exigir offsetParent
        alt = await page.evaluate(
            """(label) => {
                const timeRe = /\\d{1,2}:\\d{2}/;
                const els = [...document.querySelectorAll('li, div')]
                    .filter(e => e.innerText && e.innerText.includes(label)
                        && timeRe.test(e.innerText));
                return els.length;
            }""", label)
        log(f"alternativa (sem offsetParent): {alt}")

        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
