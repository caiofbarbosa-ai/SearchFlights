"""
Smiles POC - Experimento patchright (2026-09-02)
Patchright = fork do Playwright com vazamentos de CDP corrigidos.
Hipótese: o sensor Akamai aceita o browser patchright e o XHR de busca passa.

Sucesso = >=3 valores de milhas/preço no body em até 4 min.
"""

import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path

from patchright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORTS = Path(__file__).resolve().parents[1] / "reports"
URL = ("https://www.smiles.com.br/mfe/emissao-passagem/?adults=1&cabin=ALL"
       "&children=0&departureDate=1796698800000&infants=0&isElegible=false"
       "&isFlexibleDateChecked=false&returnDate=1797433200000"
       "&searchType=congenere&segments=1&tripType=1&originAirport=GRU"
       "&originCity=&originCountry=&originAirportIsAny=false"
       "&destinationAirport=BKK&destinCity=&destinCountry="
       "&destinAirportIsAny=false&novo-resultado-voos=true")

MILES_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+)\s*(?:milhas|pontos)", re.IGNORECASE)
BRL_RE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)")


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome", headless=False,
            args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="pt-BR",
            timezone_id="America/Sao_Paulo")
        page = await context.new_page()

        def on_response(resp):
            if "flightsearch" in resp.url or "airlines/search" in resp.url:
                log(f"<< XHR busca: {resp.status} {len(resp.headers)} headers "
                    f"{resp.url[:110]}")

        page.on("response", on_response)

        log("navegando (patchright, guest) para URL direta...")
        await page.goto(URL, timeout=90_000)
        for text in ("Reject All", "Aceitar todos Cookies", "Rejeitar Tudo",
                     "Outro dia"):
            try:
                btn = page.locator(f"button:has-text('{text}')").first
                if await btn.is_visible(timeout=800):
                    await btn.click()
                    await asyncio.sleep(0.5)
            except Exception:
                continue

        status = "UNKNOWN"
        miles, brl = [], []
        for i in range(100):
            await asyncio.sleep(3)
            text = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            miles = sorted({int(m.replace(".", "")) for m in MILES_RE.findall(text)
                            if int(m.replace(".", "")) >= 1000})
            brl = sorted({int(float(b.replace(".", "").replace(",", ".")))
                          for b in BRL_RE.findall(text)
                          if float(b.replace(".", "").replace(",", ".")) >= 30})
            if i % 10 == 0:
                log(f"... {i*3}s spinner={'aguarde' in text.lower()} "
                    f"milhas={len(miles)} brl={len(brl)}")
            if len(miles) >= 3 or len(brl) >= 3:
                status = "RESULTS"
                log(f"RESULTADOS em ~{i*3}s! milhas: {miles[:8]} | BRL: {brl[:6]}")
                break
            if i > 25 and "aguarde" not in text.lower():
                status = "NO_SPINNER_NO_RESULTS"
                break

        await page.screenshot(path=str(REPORTS / "smiles_patchright_guest.png"),
                              full_page=True)
        (REPORTS / "smiles_patchright_guest.html").write_text(
            await page.content(), encoding="utf-8")
        log(f"STATUS: {status}")
        await asyncio.sleep(2)
        await context.close()
        await browser.close()
        return 0 if status == "RESULTS" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
