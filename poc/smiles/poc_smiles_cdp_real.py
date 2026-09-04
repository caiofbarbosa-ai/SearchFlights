"""
Smiles POC - Experimento CDP-attach (caminho A)
Lança um Chrome REAL (perfil próprio, não o do usuário) com --remote-debugging-port,
conecta via CDP (connect_over_cdp) e navega na URL direta.
Se o Akamai aceitar (como aceitou a janela anônima humana), o caminho A é viável.
"""

import asyncio
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORTS = Path(__file__).resolve().parents[1] / "reports"
DEBUG_PORT = 9223
URL = ("https://www.smiles.com.br/mfe/emissao-passagem/?adults=1&cabin=ALL"
       "&children=0&departureDate=1796698800000&infants=0&isElegible=false"
       "&isFlexibleDateChecked=false&returnDate=1797433200000"
       "&searchType=congenere&segments=1&tripType=1&originAirport=GRU"
       "&originCity=&originCountry=&originAirportIsAny=false"
       "&destinationAirport=BKK&destinCity=&destinCountry="
       "&destinAirportIsAny=false&novo-resultado-voos=true")

MILES_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+)\s*(?:milhas|pontos)", re.IGNORECASE)
BRL_RE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)")

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


async def main():
    chrome_exe = next((c for c in CHROME_CANDIDATES if Path(c).exists()), None)
    if not chrome_exe:
        log("[FAIL] Chrome não encontrado")
        return 1

    profile_dir = tempfile.mkdtemp(prefix="smiles_cdp_")
    log(f"lançando Chrome real (perfil temp: {profile_dir[:40]}...)")
    proc = subprocess.Popen([
        chrome_exe,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run", "--no-default-browser-check",
        "--window-size=1920,1080", "about:blank",
    ])
    time.sleep(4)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(
                f"http://localhost:{DEBUG_PORT}")
        except Exception as e:
            log(f"[FAIL] CDP connect: {e}")
            proc.kill()
            return 1
        log("CDP conectado ao Chrome real")

        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})

        log("navegando para URL direta (dentro do Chrome real)...")
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
        for i in range(100):
            await asyncio.sleep(3)
            try:
                text = await page.evaluate(
                    "() => document.body ? document.body.innerText : ''")
            except Exception:
                continue  # contexto destruído por navegação — tenta no próximo poll
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

        await page.screenshot(path=str(REPORTS / "smiles_cdp_real.png"),
                              full_page=True)
        (REPORTS / "smiles_cdp_real.html").write_text(
            await page.content(), encoding="utf-8")
        log(f"STATUS: {status}")

        await browser.close()  # desconecta CDP (Chrome continua)
        try:
            proc.terminate()
        except Exception:
            pass
        return 0 if status == "RESULTS" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
