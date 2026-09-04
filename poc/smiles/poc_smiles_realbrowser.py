"""
Smiles POC - Experimento discriminante (2026-09-02)
Hipótese A: guest não busca (membro obrigatório) -> M1 login
Hipótese B: bot-fingerprint bloqueia o XHR de disponibilidade no Chromium
            embutido; browser REAL (chrome/msedge do sistema) destrava -> M2/stealth

Teste: URL direta GUEST em canal de browser real + telemetria do XHR.
"""

import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

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


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


async def main():
    async with async_playwright() as p:
        # browser real do sistema: fingerprint genuíno (TLS, client hints)
        browser = None
        for channel in ("chrome", "msedge"):
            try:
                browser = await p.chromium.launch(
                    channel=channel, headless=False,
                    args=["--disable-blink-features=AutomationControlled"])
                log(f"browser real: {channel}")
                break
            except Exception as e:
                log(f"canal {channel} indisponível: {str(e)[:80]}")
        if not browser:
            log("[FAIL] nenhum browser de sistema disponível")
            return

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="pt-BR",
            timezone_id="America/Sao_Paulo")
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        log(f"UA: {await page.evaluate('navigator.userAgent')}")

        def on_response(resp):
            u = resp.url
            if "flightsearch" in u or "members" in u:
                log(f"<< {resp.status} {u[:130]}")

        page.on("response", on_response)
        page.on("console", lambda m: log(f"CONSOLE-err: {m.text[:160]}")
                if m.type == "error" and ("CORS" in m.text
                                          or "flightsearch" in m.text) else None)

        log("navegando (guest) para URL direta...")
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

        # observação de até 4 min
        result_status = "UNKNOWN"
        for i in range(80):
            await asyncio.sleep(3)
            text = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            miles = sorted({int(m.replace(".", "")) for m in MILES_RE.findall(text)
                            if int(m.replace(".", "")) >= 1000})
            if i % 10 == 0:
                log(f"... {i*3}s spinner={'aguarde' in text.lower()} "
                    f"milhas={len(miles)}")
            if len(miles) >= 3:
                result_status = "RESULTS"
                log(f"RESULTADOS em ~{i*3}s! milhas distintas: "
                    f"{miles[:8]}")
                break
            if i > 20 and "aguarde" not in text.lower():
                result_status = "PAGE_CHANGED_NO_SPINNER"
                log(f"spinner sumiu em ~{i*3}s sem resultados — ver screenshot")
                break

        await page.screenshot(path=str(REPORTS / "smiles_realbrowser_guest.png"),
                              full_page=True)
        (REPORTS / "smiles_realbrowser_guest.html").write_text(
            await page.content(), encoding="utf-8")
        log(f"STATUS: {result_status}")
        log(f"URL final: {page.url[:110]}")

        await asyncio.sleep(3)
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
