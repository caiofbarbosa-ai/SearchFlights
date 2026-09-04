"""Probe: o voo de 6.839 aparece no primeiro render e é REMOVIDO segundos
depois na sessão automatizada. Correção: capturar payloads de REDE desde o
início (imune à remoção do DOM) + DOM polling rápido (0,5s)."""

import asyncio
import re
import sys
from datetime import date

sys.path.insert(0, ".")
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.scrapers.google_flights import build_q_url

D, R = date(2027, 7, 21), date(2027, 7, 28)
PRICE_RE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)")


def log(m):
    print(m, flush=True)


def parse(text: str):
    out = sorted({int(round(float(m.replace(".", "").replace(",", "."))))
                  for m in PRICE_RE.findall(text)
                  if float(m.replace(".", "").replace(",", ".")) >= 100})
    return out


async def main():
    captured = []  # (url, body)
    dom_min = None

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

        async def on_response(resp):
            try:
                if resp.status != 200:
                    return
                body = await resp.text()
                if "BKK" in body and PRICE_RE.search(body):
                    captured.append((resp.url[:150], body))
            except Exception:
                pass

        page.on("response", on_response)

        # DOM polling RÁPIDO em paralelo com a navegação (0,5s desde o início)
        async def dom_poller():
            nonlocal dom_min
            while True:
                await asyncio.sleep(0.5)
                try:
                    text = await page.evaluate(
                        "() => document.body ? document.body.innerText : ''")
                except Exception:
                    continue
                prices = parse(text)
                if prices:
                    if dom_min is None or prices[0] < dom_min:
                        dom_min = prices[0]
                        log(f"    DOM novo piso: R$ {dom_min:,}"
                            .replace(",", "."))

        poller = asyncio.create_task(dom_poller())

        log("navegando (captura de rede + DOM 0,5s)...")
        await page.goto(build_q_url("GRU", "BKK", D, R), timeout=90_000)
        await asyncio.sleep(60)
        poller.cancel()

    log(f"\npiso visto no DOM: R$ {dom_min:,}".replace(",", ".")
        if dom_min else "DOM nunca mostrou preço")
    log(f"respostas capturadas com preços: {len(captured)}")

    global_min = None
    where = None
    for url, body in captured:
        for v in parse(body):
            if global_min is None or v < global_min:
                global_min, where = v, url
    log(f"piso nas respostas de REDE: "
        f"R$ {global_min:,}".replace(",", ".") if global_min
        else "nenhum preço em payloads")
    if where:
        log(f"  veio de: {where}")

    if global_min and global_min <= 7000:
        log("✅ CONFIRMADO: a tarifa de ~6.839 ESTÁ nos payloads de rede — "
            "a remoção é só no DOM. Correção = extrair da rede (S2).")
    # salva evidência
    import pathlib
    pathlib.Path("poc/reports/captura_rede").mkdir(parents=True,
                                                   exist_ok=True)
    for i, (url, body) in enumerate(captured[:6]):
        (pathlib.Path("poc/reports/captura_rede") / f"payload_{i}.txt") \
            .write_text(f"URL: {url}\n\n{body[:50000]}", encoding="utf-8")
    log("payloads salvos em poc/reports/captura_rede/")


if __name__ == "__main__":
    asyncio.run(main())
