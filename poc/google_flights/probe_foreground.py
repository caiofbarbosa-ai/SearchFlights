"""Probe: janela em PRIMEIRO PLANO + flags anti-throttling.
Hipótese: o Chrome estrangula os timers JS de janelas ao fundo, atrasando
as ondas de tarifa (usuário viu as ondas; automação não)."""

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
            args=[
                "--disable-blink-features=AutomationControlled",
                # impede o Chrome de estrangular timers/JS em janela ao fundo:
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ])
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/151.0.0.0 Safari/537.36"))
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        await page.bring_to_front()

        await page.goto(build_q_url("GRU", "BKK", D, R), timeout=90_000)
        await page.bring_to_front()
        # sinal de engajamento: leve scroll
        await page.evaluate("window.scrollTo(0, 120)")
        await asyncio.sleep(1)
        await page.evaluate("window.scrollTo(0, 0)")

        body = ""
        floor = None
        for i in range(30):  # janela ~90s
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
                    f"R$ {floor:,}".replace(",", ".") if floor
                    else f"... {i*3}s sem preços")

        log(f"RESULTADO (foreground + anti-throttle): piso = "
            f"R$ {floor:,}".replace(",", ".") if floor
            else "sem preços")
        log(f"esperado (usuário): R$ 6.839")
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
