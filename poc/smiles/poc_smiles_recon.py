"""
Smiles POC - Validação 2026-09-02 (aprendizados da POC Google Flights)
v4 — URL DIRETA de resultados (equivalente do `q=` do Google):
  /mfe/emissao-passagem/?adults=2&originAirport=GRU&destinationAirport=BKK
  &departureDate=<epoch_ms meia-noite BRT>&returnDate=<epoch_ms>&tripType=1...
Descobertas das iterações 1-3:
  - Form: clique na sugestão <li> (NUNCA Enter), datas readonly via calendário
  - Overlays: cookies (pt/en), popup promo, prompt de login — dispensáveis
  - Resultados demoram (spinner "Aguarde enquanto buscamos"): polling longo
  - Fluxo de resultado em 2 etapas: escolher ida -> escolher volta

Uso:
  python poc/smiles/poc_smiles_recon.py direct [--origins GRU,CGH,VCP] [--headless]
  python poc/smiles/poc_smiles_recon.py gate [--origins GRU,CGH,VCP] [--headless]
"""

import argparse
import asyncio
import json
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ORIGINS = ["GRU", "CGH", "VCP"]
DESTINATION = "BKK"
DEP_DATE = (2026, 12, 8)   # datas de controle (janela aberta)
RET_DATE = (2026, 12, 16)
ADULTS = 2                 # spec: 2 adultos

REPORTS = Path(__file__).resolve().parents[1] / "reports"
RESULTS_JSON = REPORTS / "smiles_validation_results_2026-09-02.json"

MILES_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+)\s*(?:milhas|pontos)", re.IGNORECASE)
BRL_RE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)")

BLOCK_MARKERS = ["acesso negado", "access denied", "unusual traffic", "/sorry/"]
LOADING_MARKERS = ["aguarde enquanto buscamos", "buscando voos"]
NO_RESULTS_MARKERS = ["não encontramos", "nao encontramos", "nenhum voo",
                      "não há voos", "nao ha voos", "infelizmente",
                      "não há mais", "esgot", "sem disponibilidade",
                      "não há milhas"]


def epoch_ms_brt(y: int, m: int, d: int) -> int:
    """Meia-noite de Brasília (UTC-3) em epoch ms — formato do Smiles."""
    tz = timezone(timedelta(hours=-3))
    return int(datetime(y, m, d, tzinfo=tz).timestamp() * 1000)


def build_direct_url(origin: str) -> str:
    """URL direta de resultados (padrão descoberto no recon v3)."""
    params = {
        "adults": ADULTS, "cabin": "ALL", "children": 0,
        "departureDate": epoch_ms_brt(*DEP_DATE), "infants": 0,
        "isElegible": "false", "isFlexibleDateChecked": "false",
        "returnDate": epoch_ms_brt(*RET_DATE), "searchType": "congenere",
        "segments": 1, "tripType": 1,
        "originAirport": origin, "originCity": "", "originCountry": "",
        "originAirportIsAny": "false",
        "destinationAirport": DESTINATION, "destinCity": "", "destinCountry": "",
        "destinAirportIsAny": "false",
        "novo-resultado-voos": "true",
    }
    return f"https://www.smiles.com.br/mfe/emissao-passagem/?{urlencode(params)}"


class NetworkManifest:
    def __init__(self):
        self.entries: list[dict] = []

    async def on_response(self, response):
        try:
            ctype = (response.headers or {}).get("content-type", "")
            if response.status != 200 or "gstatic" in response.url:
                return
            if not ("json" in ctype or any(
                    k in response.url.lower()
                    for k in ("search", "flight", "miles", "award",
                              "avail", "offer", "booking", "emissao"))):
                return
            body = await response.text()
            self.entries.append({
                "url": response.url[:400],
                "status": response.status,
                "content_type": ctype[:100],
                "bytes": len(body),
                "snippet": body[:1500] if ("json" in ctype and len(body) > 500
                                           and any(k in body[:3000].lower() for k in
                                                   ("milhas", "miles", "flight",
                                                    "segment", "price"))) else "",
                "time": datetime.now().isoformat(),
            })
        except Exception:
            pass


async def shot_and_dump(page, name: str) -> dict:
    await page.screenshot(path=str(REPORTS / f"smiles_{name}.png"), full_page=True)
    (REPORTS / f"smiles_{name}.html").write_text(
        await page.content(), encoding="utf-8")
    return {"screenshot": f"smiles_{name}.png", "html": f"smiles_{name}.html"}


async def dismiss_overlays(page) -> list[str]:
    dismissed = []
    for text in ("Rejeitar Tudo", "Aceitar todos Cookies", "Outro dia",
                 "Reject All", "Accept All Cookies", "Entendi", "Continuar"):
        try:
            btn = page.locator(f"button:has-text('{text}')").first
            if await btn.is_visible(timeout=800):
                await btn.click()
                dismissed.append(text)
                await asyncio.sleep(random.uniform(0.4, 0.8))
        except Exception:
            continue
    # prompt de login "Acesse ou crie sua conta" tem × de fechar
    for sel in ("[aria-label='Fechar']", "[aria-label='Close']",
                "button[class*='close' i]"):
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=500):
                await btn.click()
                dismissed.append(f"close:{sel}")
                await asyncio.sleep(0.4)
                break
        except Exception:
            continue
    removed = await page.evaluate("""() => {
        const sels = ['#popupOverlay', '.popup-overlay',
                      '[class*="popup-overlay" i]'];
        let n = 0;
        for (const s of sels) document.querySelectorAll(s)
            .forEach(e => { e.remove(); n++; });
        return n;
    }""")
    if removed:
        dismissed.append(f"js-removed:{removed}")
    return dismissed


async def all_frames_text(page) -> str:
    """Texto agregado de todos os frames (o MFE pode renderizar em iframe)."""
    parts = []
    for frame in page.frames:
        try:
            parts.append(await frame.evaluate(
                "() => document.body ? document.body.innerText : ''"))
        except Exception:
            continue
    return "\n".join(parts)


async def wait_results(page, timeout_s: int = 150) -> tuple[bool, str]:
    """Poll até dados aparecerem (milhas/preços) ou timeout/erro."""
    while timeout_s > 0:
        text = await all_frames_text(page)
        lower = text.lower()
        if len(set(MILES_RE.findall(text))) >= 3 or \
                len(set(BRL_RE.findall(text))) >= 3:
            return True, text
        if any(m in lower for m in NO_RESULTS_MARKERS) and \
                not any(m in lower for m in LOADING_MARKERS):
            return True, text  # estado sem-voos é resposta válida
        await asyncio.sleep(3)
        timeout_s -= 3
    return False, ""


async def direct_run(origin: str, label: str, headless: bool) -> dict:
    started = time.monotonic()
    manifest = NetworkManifest()
    result = {
        "mode": f"direct_{label}", "origin": origin, "destination": DESTINATION,
        "status": "UNKNOWN", "steps": [], "final_url": None,
        "miles_found": 0, "brl_found": 0, "miles_values": [],
        "brl_values": [], "samples": [], "execution_time": None,
        "timestamp": datetime.now().isoformat(), "error": None,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"))
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        page.on("response", manifest.on_response)

        try:
            url = build_direct_url(origin)
            print(f"\n[{datetime.now():%H:%M:%S}] {label}: {origin}→{DESTINATION} "
                  f"{DEP_DATE}→{RET_DATE} ({ADULTS} adultos)")
            print(f"    URL: {url[:130]}...")
            await page.goto(url, timeout=90_000)
            await dismiss_overlays(page)

            ok, text = await wait_results(page, timeout_s=150)
            await dismiss_overlays(page)
            result["steps"].append(
                {"step": "results", "url": page.url,
                 **await shot_and_dump(page, f"direct_{label}_{origin}")})

            lower = text.lower()
            miles = sorted({int(m.replace(".", "")) for m in MILES_RE.findall(text)
                            if int(m.replace(".", "")) >= 1000})
            brl = sorted({int(float(b.replace(".", "").replace(",", ".")))
                          for b in BRL_RE.findall(text)
                          if float(b.replace(".", "").replace(",", ".")) >= 30})
            result["miles_values"] = miles
            result["brl_values"] = brl
            result["miles_found"] = len(miles)
            result["brl_found"] = len(brl)

            # amostras: contexto em torno de menções de milhas (evidência legível)
            samples = []
            for m in MILES_RE.finditer(text):
                s = max(0, m.start() - 100)
                samples.append(text[s:m.end() + 100].replace("\n", " | "))
                if len(samples) >= 5:
                    break
            result["samples"] = samples

            result["final_url"] = page.url
            if any(m in page.url.lower() for m in ("/login",)) or \
                    any(m in lower for m in BLOCK_MARKERS):
                result["status"] = "BLOCKED"
            elif len(miles) >= 3 or len(brl) >= 3:
                result["status"] = "RESULTS"
            elif any(m in lower for m in NO_RESULTS_MARKERS):
                result["status"] = "NO_RESULTS"
            elif any(m in lower for m in LOADING_MARKERS):
                result["status"] = "STILL_LOADING"
            else:
                result["status"] = "UNKNOWN_PAGE"

        except Exception as exc:
            result["status"] = "ERROR"
            result["error"] = str(exc)[:400]
            print(f"  [ERROR] {exc}")
        finally:
            result["network_manifest"] = manifest.entries
            result["execution_time"] = round(time.monotonic() - started, 1)
            await context.close()
            await browser.close()

    print(f"    STATUS: {result['status']} | milhas: {result['miles_found']} "
          f"({result['miles_values'][:4]}) | BRL: {result['brl_found']} | "
          f"{result['execution_time']}s")
    if result["samples"]:
        print(f"    amostra: {result['samples'][0][:160]}")
    return result


def save_results(entry: dict):
    existing = json.loads(RESULTS_JSON.read_text(encoding="utf-8")) \
        if RESULTS_JSON.exists() else []
    RESULTS_JSON.write_text(
        json.dumps(existing + [entry], ensure_ascii=False, indent=2),
        encoding="utf-8")


async def mode_direct(origins: list[str], headless: bool) -> int:
    entries = []
    for i, origin in enumerate(origins):
        if i:
            await asyncio.sleep(random.uniform(6, 10))
        entry = await direct_run(origin, "e1", headless)
        entries.append(entry)
        save_results(entry)
    ok = sum(1 for e in entries if e["status"] == "RESULTS")
    print("\n" + "=" * 70)
    print(f"DIRECT: {ok}/{len(entries)} origens com dados extraídos")
    manifest_path = REPORTS / "smiles_direct_network_manifest.json"
    all_entries = [x for e in entries for x in e["network_manifest"]]
    manifest_path.write_text(
        json.dumps(all_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  manifest: {manifest_path.name} ({len(all_entries)} entradas)")
    return 0 if ok == len(entries) else 1


async def mode_gate(origins: list[str], headless: bool) -> int:
    results = []
    for origin in origins:
        for run in range(1, 4):
            r = await direct_run(origin, f"gate_r{run}", headless)
            results.append(r)
            save_results(r)
            await asyncio.sleep(random.uniform(6, 10))
    ok = [r["status"] == "RESULTS" and r["miles_found"] >= 3
          and (r["execution_time"] or 999) < 300 for r in results]
    print("\n" + "=" * 70)
    print(f"GATE SMILES: {sum(ok)}/{len(results)} runs com >=3 valores extraídos")
    for r in results:
        mark = "✓" if r["status"] == "RESULTS" and r["miles_found"] >= 3 else "✗"
        print(f"  {mark} {r['label_' if False else 'mode']}/{r['origin']}: "
              f"{r['status']} ({r['miles_found']} milhas, {r['brl_found']} BRL, "
              f"{r['execution_time']}s)")
    return 0 if all(ok) else 1


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["direct", "gate"], default="direct",
                        nargs="?")
    parser.add_argument("--origins", default=",".join(ORIGINS))
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print(f"SMILES POC — modo {args.mode.upper()} (URL direta, adults={ADULTS})")
    print("=" * 70)

    origins = args.origins.split(",")
    if args.mode == "direct":
        sys.exit(await mode_direct(origins, args.headless))
    else:
        sys.exit(await mode_gate(origins, args.headless))


if __name__ == "__main__":
    asyncio.run(main())
