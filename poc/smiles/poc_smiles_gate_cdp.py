"""
Smiles POC - Gate via CDP em Chrome real (2026-09-02)
Arquitetura validada no experimento cdp_real: Akamai aceita o Chrome real.

Fases:
  1. Pre-check 2027 (datas-alvo) — classifica RESULTS/CALENDAR_NOT_OPEN
  2. Gate: 3 runs por origem (GRU, CGH, VCP) em datas de controle
Critério por run: >=3 cartões de voo com milhas por passageiro, <5 min.
"""

import asyncio
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORTS = Path(__file__).resolve().parents[1] / "reports"
RESULTS_JSON = REPORTS / "smiles_gate_cdp_results.json"
DEBUG_PORT = 9224

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

MILES_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+)\s*milhas por passageiro")
CARD_JS = """() => {
    const els = [...document.querySelectorAll('*')].filter(e =>
        e.children.length === 0 &&
        /milhas por passageiro/.test(e.innerText || ''));
    const cards = els.map(el => {
        let c = el;
        for (let i = 0; i < 4 && c.parentElement; i++) c = c.parentElement;
        return (c.innerText || '').replace(/\\s*\\n+\\s*/g, ' | ').slice(0, 300);
    });
    return [...new Set(cards)];
}"""


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def build_url(origin: str, dep_ms: int, ret_ms: int, adults: int = 2) -> str:
    return (
        "https://www.smiles.com.br/mfe/emissao-passagem/?"
        f"adults={adults}&cabin=ALL&children=0&departureDate={dep_ms}"
        f"&infants=0&isElegible=false&isFlexibleDateChecked=false"
        f"&returnDate={ret_ms}&searchType=congenere&segments=1&tripType=1"
        f"&originAirport={origin}&originCity=&originCountry="
        f"&originAirportIsAny=false&destinationAirport=BKK&destinCity="
        f"&destinCountry=&destinAirportIsAny=false&novo-resultado-voos=true")


def epoch_ms_brt(y, m, d):
    """Meia-noite BRT (UTC-3) — tzinfo-aware; naive.timestamp() já aplica o
    fuso local da máquina e a subtração extra deslocava a data (bug corrigido)."""
    return int(datetime(y, m, d, tzinfo=timezone(timedelta(hours=-3)))
               .timestamp() * 1000)


async def run_once(origin: str, dep: tuple, ret: tuple, label: str) -> dict:
    started = time.monotonic()
    dep_ms = epoch_ms_brt(*dep)
    ret_ms = epoch_ms_brt(*ret)
    result = {
        "label": label, "origin": origin, "departure": f"{dep[2]:02d}/{dep[1]:02d}/{dep[0]}",
        "status": "UNKNOWN", "miles_values": [], "cards": [],
        "execution_time": None, "timestamp": datetime.now().isoformat(),
    }

    chrome_exe = next((c for c in CHROME_CANDIDATES
                       if Path(c).exists()), None)
    if not chrome_exe:
        result["status"] = "NO_CHROME"
        return result

    profile_dir = tempfile.mkdtemp(prefix="smiles_gate_")
    proc = subprocess.Popen([
        chrome_exe, f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={profile_dir}", "--no-first-run",
        "--no-default-browser-check", "--window-size=1920,1080", "about:blank"])
    time.sleep(4)

    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.connect_over_cdp(
                f"http://localhost:{DEBUG_PORT}")
            context = browser.contexts[0]
            page = (context.pages[0] if context.pages
                    else await context.new_page())
            await page.set_viewport_size({"width": 1920, "height": 1080})

            log(f"{label}: {origin}→BKK {dep[2]:02d}/{dep[1]:02d}→"
                f"{ret[2]:02d}/{ret[1]:02d} (2 adultos)")
            await page.goto(build_url(origin, dep_ms, ret_ms), timeout=90_000)
            for text in ("Reject All", "Aceitar todos Cookies", "Rejeitar Tudo",
                         "Outro dia"):
                try:
                    btn = page.locator(f"button:has-text('{text}')").first
                    if await btn.is_visible(timeout=600):
                        await btn.click()
                        await asyncio.sleep(0.4)
                except Exception:
                    continue

            for i in range(100):
                await asyncio.sleep(3)
                try:
                    text = await page.evaluate(
                        "() => document.body ? document.body.innerText : ''")
                    if "milhas por passageiro" in text:
                        cards = await page.evaluate(CARD_JS)
                        if len(cards) >= 3:
                            break
                except Exception:
                    continue  # navegação em curso

            text = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            result["miles_values"] = sorted({
                int(m.replace(".", "")) for m in MILES_RE.findall(text)})
            result["cards"] = (await page.evaluate(CARD_JS))[:6]
            result["page_text_head"] = text[:300]

            lower = text.lower()
            if len(result["miles_values"]) >= 3:
                result["status"] = "RESULTS"
            elif any(m in lower for m in ("não encontramos", "nenhum voo",
                                          "infelizmente", "esgot",
                                          "sem disponibilidade")):
                result["status"] = "NO_RESULTS"
            elif "aguarde" in lower:
                result["status"] = "STILL_LOADING"
            else:
                result["status"] = "UNKNOWN_PAGE"

            await page.screenshot(
                path=str(REPORTS / f"smiles_gate_{label}_{origin}.png"),
                full_page=True)
        except Exception as exc:
            result["status"] = "ERROR"
            result["error"] = str(exc)[:300]
            log(f"  [ERROR] {exc}")
        finally:
            result["execution_time"] = round(time.monotonic() - started, 1)
            if browser:
                await browser.close()
            try:
                proc.terminate()
            except Exception:
                pass

    log(f"  {result['status']} | milhas: {result['miles_values'][:5]} | "
        f"{result['execution_time']}s")
    return result


def save(entry: dict):
    existing = json.loads(RESULTS_JSON.read_text(encoding="utf-8")) \
        if RESULTS_JSON.exists() else []
    RESULTS_JSON.write_text(
        json.dumps(existing + [entry], ensure_ascii=False, indent=2),
        encoding="utf-8")


async def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    log("=" * 70)
    log("SMILES GATE via CDP (Chrome real) — pré-check 2027 + 3x3 controle")
    log("=" * 70)

    # 1. Pré-check datas-alvo 2027 (janela fechada = spinner eterno; timeout curto)
    pre = await run_once("GRU", (2027, 7, 28), (2027, 8, 5), "pre2027")
    if pre["status"] == "STILL_LOADING":
        pre["status"] = "CALENDAR_NOT_OPEN"  # Smiles não fecha o spinner fora da janela
    save(pre)
    await asyncio.sleep(15)

    # 2. Gate 3x3 em datas de controle
    control_dep, control_ret = (2026, 12, 8), (2026, 12, 16)
    results = []
    for origin in ("GRU", "CGH", "VCP"):
        for run in (1, 2, 3):
            r = await run_once(origin, control_dep, control_ret,
                               f"gate_r{run}")
            results.append(r)
            save(r)
            await asyncio.sleep(20)  # intervalo maior entre buscas

    ok = [r["status"] == "RESULTS" and len(r["miles_values"]) >= 3
          and (r["execution_time"] or 999) < 300 for r in results]
    print("\n" + "=" * 70)
    print(f"PRÉ-CHECK 2027: {pre['status']}")
    print(f"GATE SMILES: {sum(ok)}/{len(results)} runs com >=3 award prices")
    for r in results:
        mark = "✓" if (r["status"] == "RESULTS"
                       and len(r["miles_values"]) >= 3) else "✗"
        print(f"  {mark} {r['origin']} {r['label']}: {r['status']} "
              f"({len(r['miles_values'])} milhas, {r['execution_time']}s)")


if __name__ == "__main__":
    asyncio.run(main())
