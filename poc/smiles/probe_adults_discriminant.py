"""Experimento discriminante (change smiles-1-adulto) — REVISO 09/09:
hipótese do DRIVER (levantada pelo usuário, que apontou viés na teoria de
bloqueio). Cronologia: os 2 únicos renders da história (09-02, 05-09) foram
com playwright VANILLA connect_over_cdp; o commit 68ac0e9 (05-09 18:53)
trocou Smiles p/ patchright e desde então NENHUM render. Patchright nunca
renderizou neste site; vanilla 2/2.

Driver sob teste: PROBE_DRIVER (default "playwright" = vanilla).
Runs (driver_test):
  A2: jul/27, GRU, 2 adultos (config de produção EXATA de hoje)
  A1: jul/27, GRU, 1 adulto
Matriz:
  A2✅                  → DRIVER_FIX_FULL: produção = reverter driver, sem
                         mudança de adultos/telegram/classificador
  A2❌ A1✅             → DRIVER_FIX + ADULTS: driver certo E 1 adulto
                         (plano original com validação D1b de 3 manhãs)
  A2❌ A1❌             → VANILLA_FAILS: pivot p/ saídas alternativas
                         (CDP no Chrome do usuário, login, endpoint calendário)

Evidência: screenshot + body + milhas por run em poc/reports/, JSON
consolidado em smiles_adults_discriminant.json.
Rodar da raiz:  PROBE_DRIVER=playwright python poc/smiles/probe_adults_discriminant.py
"""

import asyncio
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, ".")

from src.config import settings
from src.scrapers.chrome_cdp import RealChrome
from src.scrapers.smiles import (MILES_RE, NO_RESULTS_MARKERS,
                                 build_url, looks_like_results_shell)

REPORTS = Path("poc/reports").resolve()
OUT_JSON = REPORTS / "smiles_adults_discriminant.json"
SPACING_S = settings.smiles_origin_spacing_s
OBSERVE_S = 180  # mesmo timeout de produção
DRIVER = os.getenv("PROBE_DRIVER", "playwright")

DEZ_DEP, DEZ_RET = date(2026, 12, 8), date(2026, 12, 16)  # controle POC

RUNS = [
    {"label": "A2_jul27_2adultos", "dep": settings.departure_date,
     "ret": settings.return_date, "adults": 2},
    {"label": "A1_jul27_1adulto", "dep": settings.departure_date,
     "ret": settings.return_date, "adults": 1},
]

# validação D1b (manhãs de confirmação): PROBE_ONLY=A1 roda 1 busca (~5 min)
_only = os.getenv("PROBE_ONLY", "").strip().upper()
if _only:
    RUNS = [r for r in RUNS if r["label"].startswith(_only)]


def log(m):
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


# console Windows (cp1252) não codifica setas/acentos — força UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


async def dismiss_cookies(page):
    # banner carrega async — espera ativa + retry (run A de 09/09 seguiu com
    # o banner aberto por 181s; nos renders saudáveis ele é dispensado)
    for _ in range(10):
        clicked = False
        for text in ("Rejeitar todos", "Rejeitar Tudo",
                     "Aceitar todos Cookies", "Outro dia", "Reject All",
                     "Accept All Cookies"):
            try:
                btn = page.locator(f"button:has-text('{text}')").first
                if await btn.is_visible(timeout=800):
                    await btn.click()
                    clicked = True
                    await asyncio.sleep(0.5)
            except Exception:
                continue
        if not clicked:
            break
        await asyncio.sleep(1)


async def observe(page, run):
    """Poll do body a cada 3s ate RENDERED/NO_RESULTS ou esgotar OBSERVE_S."""
    start = asyncio.get_event_loop().time()
    body = ""
    for _ in range(OBSERVE_S // 3):
        await asyncio.sleep(3)
        try:
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
        except Exception:
            continue  # navegação em curso
        low = body.lower()
        miles = sorted({int(m.replace(".", "")) for m in MILES_RE.findall(body)
                        if int(m.replace(".", "")) >= 1000})
        elapsed = int(asyncio.get_event_loop().time() - start)
        if miles and "aguarde" not in low:
            log(f"  [{run['label']}] RENDERIZOU em {elapsed}s — "
                f"{len(miles)} valores, min={miles[0]}")
            return "RENDERED", elapsed, miles, body
        if any(m in low for m in NO_RESULTS_MARKERS) and "aguarde" not in low:
            log(f"  [{run['label']}] SEM RESULTADOS em {elapsed}s "
                f"(respondeu, não girou)")
            return "NO_RESULTS", elapsed, miles, body
        if elapsed % 30 < 3:
            log(f"  [{run['label']}] {elapsed}s: aguarde="
                f"{'aguarde' in low}, milhas={len(miles)}")
    low = body.lower()
    miles = sorted({int(m.replace(".", "")) for m in MILES_RE.findall(body)
                    if int(m.replace(".", "")) >= 1000})
    if "aguarde" in low:
        return "SPINNER", OBSERVE_S, miles, body
    if looks_like_results_shell(low) and not miles:
        return "EMPTY_SHELL", OBSERVE_S, miles, body
    return "UNKNOWN", OBSERVE_S, miles, body


async def run_one(page, run):
    url = build_url("GRU", departure_date=run["dep"], return_date=run["ret"],
                    adults=run["adults"])
    log(f"run {run['label']}: dep={run['dep']} ret={run['ret']} "
        f"adults={run['adults']}")
    entry = {"label": run["label"], "dep": str(run["dep"]),
             "ret": str(run["ret"]), "adults": run["adults"],
             "url_params": url.split("?")[1][:120]}
    try:
        await page.goto(url, timeout=90_000)
        await dismiss_cookies(page)
        status, elapsed, miles, body = await observe(page, run)
        shot = REPORTS / f"smiles_adults_discr_{run['label']}.png"
        try:
            await page.screenshot(path=str(shot), full_page=True)
        except Exception:
            pass
        entry.update({
            "status": status, "first_state_s": elapsed,
            "distinct_miles": miles[:10], "n_miles_values": len(miles),
            "body_head": body[:600].replace("\n", " | "),
            "screenshot": shot.name,
        })
    except Exception as exc:
        entry.update({"status": "ERROR", "error": str(exc)[:300]})
        log(f"  [{run['label']}] ERRO: {str(exc)[:150]}")
    entry["ts"] = datetime.now().isoformat(timespec="seconds")
    return entry


def decide(runs):
    ok = {r["label"].split("_")[0]: r["status"] == "RENDERED" for r in runs}
    a2, a1 = ok.get("A2", False), ok.get("A1", False)
    if a2:
        return "DRIVER_FIX_FULL", ("2 adultos renderiza com o driver certo — "
               "produção = reverter driver p/ playwright; sem mudança de "
               "adultos (validar 3 manhãs, D1b)")
    if a1:
        return ("DRIVER_FIX_PLUS_ADULTS", "driver vanilla E 1 adulto "
                "necessários — plano original (1 adulto em produção) com "
                "validação D1b de 3 manhãs")
    return ("VANILLA_FAILS", "nem vanilla renderizou — pivot p/ saídas "
            "alternativas: CDP no Chrome do usuário, login real, endpoint "
            "calendário")


def save(results, outcome=None, msg=None):
    doc = {"generated_at": datetime.now().isoformat(timespec="seconds"),
           "spacing_s": SPACING_S, "driver": DRIVER, "runs": results,
           "outcome": outcome, "action": msg}
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                        encoding="utf-8")


async def main():
    results = []
    log(f"driver sob teste: {DRIVER}")
    async with RealChrome(port=9305, driver=DRIVER) as chrome:
        page = await chrome.page()
        for i, run in enumerate(RUNS):
            if i:
                log(f"aguardando {SPACING_S}s (rate-limit Akamai)...")
                await asyncio.sleep(SPACING_S)
            results.append(await run_one(page, run))
            save(results)  # incremental: kill/perda não descarta runs prontas
    outcome, msg = decide(results)
    save(results, outcome, msg)
    log(f"JSON: {OUT_JSON}")
    log(f"resultado: " + " / ".join(f"{r['label']}={r['status']}"
                                    for r in results))
    log(f"DESFECHO: {outcome} — {msg}")


if __name__ == "__main__":
    asyncio.run(main())
