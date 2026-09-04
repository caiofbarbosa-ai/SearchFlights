"""Probe decisivo: query textual COM "for 2 passengers" vs sem.
Hipótese: o nº de passageiros na query muda as tarifas exibidas
(13.677 total c/ 2 adultos vs 8.216/pax c/ 1 adulto)."""

import asyncio
import re
import sys

sys.path.insert(0, ".")
from datetime import date
from urllib.parse import quote

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

D, R = date(2027, 7, 21), date(2027, 7, 28)
PRICE_RE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)")


def parse(text):
    out = sorted({int(round(float(m.replace(".", "").replace(",", "."))))
                  for m in PRICE_RE.findall(text)
                  if float(m.replace(".", "").replace(",", ".")) >= 100})
    return out


async def probe(p, label: str, q: str):
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
    url = (f"https://www.google.com/travel/flights?q={quote(q)}"
           f"&hl=pt-BR&gl=BR&curr=BRL")
    await page.goto(url, timeout=90_000)
    body = ""
    for _ in range(15):
        await asyncio.sleep(3)
        body = await page.evaluate(
            "() => document.body ? document.body.innerText : ''")
        if len(parse(body)) >= 3:
            break
    prices = parse(body)
    print(f"{label}: min = R$ {prices[0] if prices else '—'} | "
          f"distintas: {prices[:6]}")
    # contexto da menor ocorrência (é preço do dia-alvo ou de outra data?)
    if prices:
        first = prices[0]
        m = re.search(rf"R\$\s?{first:,}".replace(",", "."), body)
        if m:
            s = max(0, m.start() - 90)
            print(f"   contexto: ...{body[s:m.end()+60]}...".replace("\n", " | "))
    await context.close()
    await browser.close()


async def main():
    async with async_playwright() as p:
        await probe(
            p, "1 adulto (atual)",
            f"Flights from São Paulo to BKK on {D} through {R}")
        await asyncio.sleep(8)
        await probe(
            p, "2 passageiros (novo)",
            f"Flights from São Paulo to BKK for 2 passengers on {D} "
            f"through {R}")


if __name__ == "__main__":
    asyncio.run(main())
