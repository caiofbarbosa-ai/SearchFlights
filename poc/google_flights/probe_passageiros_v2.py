"""Probe v2: +1 adulto via JS (menor row 'Adultos' -> botão '+'), depois
'Concluído'; valida que o piso vira o TOTAL de 2 adultos (~13.677)."""

import asyncio
import sys

sys.path.insert(0, ".")
from datetime import date

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.scrapers.google_flights import build_q_url, _parse_prices

D, R = date(2027, 7, 21), date(2027, 7, 28)

PLUS_JS = """() => {
    const rows = [...document.querySelectorAll('div, li, td')]
        .filter(e => e.offsetParent && e.innerText &&
            e.innerText.trim().startsWith('Adultos'))
        .sort((a, b) => a.innerText.length - b.innerText.length);
    for (const row of rows) {
        const btns = [...row.querySelectorAll('button')];
        const plus = btns.find(b =>
            (b.innerText || '').trim() === '+' ||
            (b.getAttribute('aria-label') || '').toLowerCase()
                .includes('aumentar'));
        if (plus) { plus.click(); return 'clicked'; }
    }
    return 'not_found';
}"""


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

        # abre o painel de passageiros
        for sel in ('[aria-label*="passageiro" i]', 'button:has-text("adulto")'):
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    break
            except Exception:
                continue
        await asyncio.sleep(1.5)

        r = await page.evaluate(PLUS_JS)
        log(f"+1 adulto: {r}")
        await asyncio.sleep(1)
        await page.screenshot(path="poc/reports/passageiros_v2_2adultos.png")

        done = page.locator("button:has-text('Concluído')").first
        try:
            if await done.is_visible(timeout=2500):
                await done.click()
                log("Concluído clicado")
        except Exception:
            await page.keyboard.press("Escape")
        await asyncio.sleep(12)  # re-busca automática

        body = await page.evaluate(
            "() => document.body ? document.body.innerText : ''")
        prices = _parse_prices(body)
        log(f"pós-ajuste (2 adultos): {prices[:8]}")
        totals = [x for x in prices if x >= 12000]
        if totals and min(totals) <= 14000:
            log(f"✅ CONFIRMADO: piso total 2 adultos = R$ {min(totals):,} "
                f"(esperado ~13.677)".replace(",", "."))
        else:
            log("⚠️ piso esperado não apareceu — ver screenshot")
        await page.screenshot(path="poc/reports/passageiros_v2_resultado.png",
                              full_page=True)
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
