"""
Azul POC - Fluxo de busca guest no portal Pelo Mundo (iteração 2)
Preenche GRU→BKK, descobre campos de data/botão na interação, submete e
captura: URL de resultados, API de disponibilidade, pontos/pontos+dinheiro.
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
from urllib.parse import urlencode

from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORTS = Path(__file__).resolve().parents[1] / "reports"
DEBUG_PORT = 9226
URL = "https://azulpelomundo.voeazul.com.br/"

DEP = (2026, 12, 8)
RET = (2026, 12, 16)
DEP_BR = "08/12/2026"
RET_BR = "16/12/2026"

POINTS_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+)\s*pontos", re.IGNORECASE)
BRL_RE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)")

BLOCK_MARKERS = ["comportamento incomum", "acesso foi limitado"]


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


async def shot_and_dump(page, name: str):
    await page.screenshot(path=str(REPORTS / f"azul_{name}.png"), full_page=True)
    (REPORTS / f"azul_{name}.html").write_text(
        await page.content(), encoding="utf-8")


async def dismiss_overlays(page):
    for t in ("Aceitar todos", "Aceitar", "Accept All", "OK", "Entendi"):
        try:
            btn = page.locator(f"button:has-text('{t}')").first
            if await btn.is_visible(timeout=600):
                await btn.click()
                await asyncio.sleep(0.5)
        except Exception:
            continue


async def fill_airport(page, sel: str, code: str, step: str) -> bool:
    el = page.locator(f"#{sel}").first
    if not await el.is_visible():
        log(f"    [FAIL] {sel} invisível")
        return False
    await el.click()
    await asyncio.sleep(random_sleep())
    await page.keyboard.type(code, delay=90)
    await asyncio.sleep(2)
    # casar o CÓDIGO entre parênteses — has_text simples casa substrings
    # (ex.: 'CGH' casava 'McGhee Tyson (TYS)')
    import re as _re
    li = page.locator(
        "li, [role='option'], .autocomplete-item, [class*='autocomplete'] li"
    ).filter(has_text=_re.compile(r"\(" + code + r"\)")).first
    try:
        if await li.is_visible(timeout=3000):
            await li.click()
            await asyncio.sleep(1)
            val = await el.input_value()
            log(f"    {code}: sugestão clicada; campo={val!r}")
            return code.lower() in (val or "").lower() or bool(val)
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)
        val = await el.input_value()
        log(f"    {code}: Enter; campo={val!r}")
        return bool(val)
    except Exception as e:
        log(f"    [WARN] {code}: {str(e)[:80]}")
        return False


def random_sleep():
    import random
    return random.uniform(0.4, 0.9)


async def main():
    chrome_exe = next(
        (c for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                     r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
         if Path(c).exists()), None)
    if not chrome_exe:
        log("[FAIL] Chrome não encontrado")
        return 1

    profile_dir = tempfile.mkdtemp(prefix="azul_flow_")
    proc = subprocess.Popen([
        chrome_exe, f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={profile_dir}", "--no-first-run",
        "--no-default-browser-check", "--window-size=1920,1080", "about:blank"])
    time.sleep(4)

    api_hits = []

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(
            f"http://localhost:{DEBUG_PORT}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})

        async def on_response(resp):
            u = resp.url
            if any(k in u.lower() for k in ("search", "flight", "avail",
                                            "redeem", "award", "interline")) \
                    and "json" in (resp.headers or {}).get("content-type", ""):
                try:
                    body = await resp.text()
                except Exception:
                    body = ""
                api_hits.append({"url": u[:250], "status": resp.status,
                                 "bytes": len(body)})
                log(f"<< API {resp.status} {len(body)}b {u[:120]}")
                if len(body) > 1000:
                    (REPORTS / "azul_flow_api_payload.json").write_text(
                        body, encoding="utf-8")

        page.on("response", on_response)

        status = "UNKNOWN"
        try:
            await page.goto(URL, timeout=60_000)
            try:
                await page.wait_for_load_state("networkidle", timeout=20_000)
            except Exception:
                pass
            await asyncio.sleep(4)
            await dismiss_overlays(page)
            await shot_and_dump(page, "flow_0_home")

            ok_o = await fill_airport(page, "autocompleteFlightOrigin",
                                      "GRU", "origin")
            ok_d = await fill_airport(page, "autocompleteFlightDestination",
                                      "BKK", "dest")
            await shot_and_dump(page, "flow_1_airports")

            # inventário pós-preenchimento: datas/buscar aparecem?
            inputs = await page.eval_on_selector_all(
                "input, button",
                """els => els.filter(e => e.offsetParent).slice(0, 40)
                    .map(e => ({tag: e.tagName, type: e.type || '',
                                text: (e.innerText || e.placeholder || '')
                                    .trim().slice(0, 40), id: e.id}))""")
            log("    visíveis após aeroportos:")
            for e in inputs:
                print(f"      {e['tag']} {e['text']!r} id={e['id']!r} "
                      f"type={e['type']!r}")

            # datas: tentar inputs visíveis com placeholder/name de data
            date_filled = []
            for key in ("date", "ida", "volta", "departure", "return", "data"):
                for e in inputs:
                    if e["tag"] == "INPUT" and key in (
                            e.get("text", "").lower() + e.get("id", "").lower()
                            + e.get("type", "")):
                        try:
                            el = page.locator(f"#{e['id']}").first \
                                if e["id"] else \
                                page.get_by_placeholder(e["text"]).first
                            await el.click()
                            await asyncio.sleep(1)
                            val = (DEP_BR if "ida" in key or "depart" in key
                                   or "data" in key else RET_BR)
                            await page.keyboard.type(val, delay=60)
                            await asyncio.sleep(0.8)
                            date_filled.append((e["id"], val))
                        except Exception:
                            continue
            log(f"    datas digitadas: {date_filled}")
            await shot_and_dump(page, "flow_2_dates")

            # busca
            for t in ("Buscar voos", "Buscar", "Pesquisar", "Encontrar voos"):
                btn = page.locator(f"button:has-text('{t}')").first
                try:
                    if await btn.is_visible(timeout=1500):
                        await btn.click()
                        log(f"    busca submetida via {t!r}")
                        break
                except Exception:
                    continue
            try:
                await page.wait_for_load_state("networkidle", timeout=45_000)
            except Exception:
                pass
            await asyncio.sleep(15)

            await dismiss_overlays(page)
            await shot_and_dump(page, "flow_3_results")
            text = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            (REPORTS / "azul_flow_results_text.txt").write_text(
                text, encoding="utf-8")

            lower = text.lower()
            pontos = sorted({int(m.replace(".", "")) for m in
                             POINTS_RE.findall(text)
                             if int(m.replace(".", "")) >= 1000})
            brl = sorted({int(float(b.replace(".", "").replace(",", ".")))
                          for b in BRL_RE.findall(text)
                          if float(b.replace(".", "").replace(",", ".")) >= 30})
            log(f"    URL final: {page.url[:140]}")
            log(f"    pontos distintos: {pontos[:8]} | BRL distintos: {brl[:6]}")

            if any(m in lower for m in BLOCK_MARKERS):
                status = "BLOCKED"
            elif len(pontos) >= 3 or len(brl) >= 3:
                status = "RESULTS"
                has_partner = any(a in lower for a in
                                  ("qatar", "emirates", "turkish", "united",
                                   "ethiopian", "air canada", "lufthansa",
                                   "etihad", "korean", "all nippon"))
                log(f"    menções de parceiras: {has_partner}")
                log(f"    'pontos + dinheiro' presente: "
                    f"{'pontos + dinheiro' in lower or 'pontos e dinheiro' in lower}")
            elif "nenhum" in lower or "não encontramos" in lower:
                status = "NO_RESULTS"
            else:
                status = "UNKNOWN_PAGE"

        except Exception as exc:
            status = "ERROR"
            log(f"  [ERROR] {exc}")

        log(f"STATUS: {status}")
        log(f"chamadas API capturadas: {len(api_hits)}")

        await browser.close()

    try:
        proc.terminate()
    except Exception:
        pass
    (REPORTS / "azul_flow_api_hits.json").write_text(
        json.dumps(api_hits, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if status == "RESULTS" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
