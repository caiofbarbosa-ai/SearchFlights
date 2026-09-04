"""Probe de distribuição: 6 cargas consecutivas da MESMA busca.
A tarifa barata (~6.839) aparece em algumas cargas? (variância por request)"""

import asyncio
import sys
from datetime import date

sys.path.insert(0, ".")
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.scrapers.google_flights import build_q_url

D, R = date(2027, 7, 21), date(2027, 7, 28)


def log(m):
    print(m, flush=True)


async def load_floor(page):
    await page.goto(build_q_url("GRU", "BKK", D, R), timeout=90_000)
    floor = None
    for _ in range(20):  # 30s rastreando com poll rápido
        await asyncio.sleep(0.7)
        try:
            text = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
        except Exception:
            continue
        import re
        for m in re.findall(r"R\$\s?(\d{1,3}(?:\.\d{3})*)", text):
            v = int(m.replace(".", ""))
            if v >= 100 and (floor is None or v < floor):
                floor = v
                log(f"    novo piso: R$ {v:,}".replace(",", "."))
    return floor


async def main():
    floors = []
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

        for i in range(1, 7):
            log(f"carga {i}/6 ...")
            f = await load_floor(page)
            floors.append(f)
            log(f"  -> piso da carga {i}: R$ {f:,}".replace(",", ".")
                if f else "  -> sem preços")
            await asyncio.sleep(3)

    baratos = [f for f in floors if f and f <= 7500]
    print("\n" + "=" * 60)
    print(f"pisos por carga: {floors}")
    if baratos:
        print(f"✅ tarifa barata apareceu em {len(baratos)}/6 cargas "
              f"-> correção: N cargas por origem, guardar o MÍNIMO")
    else:
        print("❌ tarifa barata NUNCA apareceu em 6 cargas automatizadas")
    await context.close()
    await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
