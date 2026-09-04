"""Probe: ajustar passageiros (1 -> 2 adultos) na página de resultados
do Google Flights e verificar se o piso vira o total de 2 adultos (13.677)."""

import asyncio
import re
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
            headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"))
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        await page.goto(build_q_url("GRU", "BKK", D, R), timeout=90_000)
        body = ""
        for _ in range(15):
            await asyncio.sleep(3)
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            if len(_parse_prices(body)) >= 3:
                break
        log(f"piso 1 adulto: {_parse_prices(body)[:4]}")

        # abre o seletor de passageiros (botão da barra de config do resultado)
        clicked = False
        for sel in ('button:has-text("adulto")', 'button:has-text("Adulto")',
                    '[aria-label*="passageiro" i]', '[aria-label*="Passageiro" i]'):
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    clicked = True
                    log(f"seletor aberto via {sel}")
                    break
            except Exception:
                continue
        if not clicked:
            log("[FAIL] seletor de passageiros não encontrado")
            await page.screenshot(path="poc/reports/passageiros_fail.png")
            return

        await asyncio.sleep(1.5)
        await page.screenshot(path="poc/reports/passageiros_dialog.png")

        # aumenta adultos +1 (aria-label ou botão '+')
        increased = False
        for sel in ('[aria-label*="umentar" i][aria-label*="adulto" i]',
                    '[aria-label*="Aumentar" i]',
                    'button:has-text("+")'):
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    increased = True
                    log(f"adulto +1 via {sel}")
                    break
            except Exception:
                continue
        await asyncio.sleep(1)
        await page.screenshot(path="poc/reports/passageiros_2adultos.png")

        # fecha o diálogo
        for sel in ('button:has-text("Concluir")', 'button:has-text("OK")',
                    'button:has-text("Fechar")', '[aria-label*="Conclu" i]'):
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    log(f"diálogo fechado via {sel}")
                    break
            except Exception:
                continue
        await asyncio.sleep(10)  # re-busca automática após mudança

        body = ""
        for _ in range(12):
            await asyncio.sleep(3)
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            prices = _parse_prices(body)
            if any(p_ >= 13000 for p_ in prices):  # total 2 adultos é >13k
                break
        prices = _parse_prices(body)
        log(f"pós-ajuste, preços distintos: {prices[:8]}")
        total_2 = [x for x in prices if x >= 13000]
        log(f"esperado: ~13.677 total (2 adultos) -> "
            f"{'✅ CONFIRMADO' if total_2 and min(total_2) <= 13700 else 'verificar'}")
        await page.screenshot(path="poc/reports/passageiros_resultado.png",
                              full_page=True)
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
