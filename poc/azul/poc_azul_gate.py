"""
Azul POC - Gate 3 origens (espaçado 90s) via CDP/Chrome real + API direta.
Critério por run: >=3 valores de pontos, <5 min.
"""

import asyncio
import json
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
RESULTS_JSON = REPORTS / "azul_gate_results.json"
DEBUG_PORT = 9227
URL = "https://azulpelomundo.voeazul.com.br/"

POINTS_RE = None  # importado do flow
sys.path.insert(0, str(Path(__file__).resolve().parent))


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def shot_and_dump_local(page, reports: Path, name: str):
    page_screenshot = asyncio.get_event_loop().create_task(
        page.screenshot(path=str(reports / f"azul_{name}.png"), full_page=True))
    return page_screenshot


async def run_once(origin: str, label: str) -> dict:
    """Reaproveita o fluxo validado: origem/destino/datas/buscar."""
    import poc_azul_flow as flow  # regexes e helpers

    started = time.monotonic()
    result = {"label": label, "origin": origin, "status": "UNKNOWN",
              "points": [], "execution_time": None,
              "timestamp": datetime.now().isoformat()}

    chrome_exe = next(
        (c for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                     r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
         if Path(c).exists()), None)
    profile_dir = tempfile.mkdtemp(prefix="azul_gate_")
    proc = subprocess.Popen([
        chrome_exe, f"--remote-debugging-port={flow.DEBUG_PORT}",
        f"--user-data-dir={profile_dir}", "--no-first-run",
        "--no-default-browser-check", "--window-size=1920,1080", "about:blank"])
    time.sleep(4)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(
            f"http://localhost:{flow.DEBUG_PORT}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})
        try:
            await page.goto(flow.URL, timeout=60_000)
            try:
                await page.wait_for_load_state("networkidle", timeout=20_000)
            except Exception:
                pass
            await asyncio.sleep(4)
            await flow.dismiss_overlays(page)

            # widget é SPA lazy: esperar de verdade; reload 1x se não vier
            for attempt in range(2):
                for _ in range(15):
                    if await page.locator(
                            "#autocompleteFlightOrigin").first.is_visible():
                        break
                    await asyncio.sleep(2)
                else:
                    if attempt == 0:
                        log("    [WARN] widget não veio; reload...")
                        await page.reload(timeout=60_000)
                        await asyncio.sleep(4)
                        await flow.dismiss_overlays(page)
                        continue
                    raise RuntimeError("widget de busca não renderizou")
                break

            await flow.fill_airport(page, "autocompleteFlightOrigin",
                                    origin, "origin")
            await flow.fill_airport(page, "autocompleteFlightDestination",
                                    "BKK", "dest")

            # datas: partida por placeholder; retorno = input de data VAZIO
            # (ambos compartilham placeholder 'Selecione a data' — .first
            #  rematchava a partida e sobrescrevia o valor)
            dep_el = page.locator("input[placeholder='DD/MM/YYYY']").first
            await dep_el.click()
            await asyncio.sleep(0.5)
            await page.keyboard.press("Control+A")
            await page.keyboard.type(flow.DEP_BR, delay=50)
            await asyncio.sleep(1)
            log(f"    data partida: {flow.DEP_BR}")

            # foco auto-avançou p/ retorno? senão, clica no date input vazio
            focused = await page.evaluate(
                "() => { const e = document.activeElement; return e && "
                "e.tagName === 'INPUT' && !e.value ? 'empty_date' : 'other'; }")
            if focused != "empty_date":
                target = await page.evaluate("""() => {
                    const isDate = e => e.offsetParent && e.tagName === 'INPUT'
                        && (/^\\d{2}\\/\\d{2}\\/\\d{4}$/.test(e.value)
                            || /data|DD\\/MM/i.test(e.placeholder));
                    const dates = [...document.querySelectorAll('input')]
                        .filter(isDate);
                    const empty = dates.find(e => !e.value);
                    if (!empty) return null;
                    const r = empty.getBoundingClientRect();
                    return {x: r.x + r.width / 2, y: r.y + r.height / 2};
                }""")
                if target:
                    await page.mouse.click(target["x"], target["y"])
                    await asyncio.sleep(0.6)
            await page.keyboard.type(flow.RET_BR, delay=50)
            await asyncio.sleep(1)
            log(f"    data retorno: {flow.RET_BR}")

            await page.screenshot(
                path=str(REPORTS / "azul_gate_pre_search.png"), full_page=True)

            btn = page.locator("#btnSearchTickets").first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                log("    busca submetida")
            try:
                await page.wait_for_load_state("networkidle", timeout=45_000)
            except Exception:
                pass
            await asyncio.sleep(15)

            text = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            lower = text.lower()
            result["points"] = sorted({
                int(m.replace(".", "")) for m in
                flow.POINTS_RE.findall(text)
                if int(m.replace(".", "")) >= 1000})
            result["url"] = page.url[:180]

            if any(m in lower for m in flow.BLOCK_MARKERS):
                result["status"] = "BLOCKED"
            elif len(result["points"]) >= 3:
                result["status"] = "RESULTS"
            elif any(m in lower for m in ("nenhum", "não encontramos",
                                          "não há voos", "não há mais",
                                          "infelizmente",
                                          "voos disponíveis")):
                result["status"] = "NO_RESULTS"
            else:
                result["status"] = "UNKNOWN_PAGE"

            await page.screenshot(
                path=str(REPORTS / f"azul_gate_{label}_{origin}.png"),
                full_page=True)
        except Exception as exc:
            result["status"] = "ERROR"
            result["error"] = str(exc)[:300]
            log(f"  [ERROR] {exc}")
        finally:
            result["execution_time"] = round(time.monotonic() - started, 1)
            await browser.close()
            try:
                proc.terminate()
            except Exception:
                pass

    log(f"  {result['status']} | pontos: {result['points'][:5]} | "
        f"{result['execution_time']}s")
    return result


async def main():
    results = []
    for i, origin in enumerate(("GRU", "CGH", "VCP")):
        if i:
            await asyncio.sleep(90)  # espaçamento conservador
        log(f"run {i+1}/3: {origin}→BKK")
        r = await run_once(origin, f"gate_r{i+1}")
        results.append(r)
        existing = json.loads(RESULTS_JSON.read_text(encoding="utf-8")) \
            if RESULTS_JSON.exists() else []
        RESULTS_JSON.write_text(
            json.dumps(existing + [r], ensure_ascii=False, indent=2),
            encoding="utf-8")

    ok = [r["status"] == "RESULTS" and len(r["points"]) >= 3 for r in results]
    print("\n" + "=" * 70)
    print(f"GATE AZUL: {sum(ok)}/{len(results)} runs com >=3 valores de pontos")
    for r in results:
        mark = "✓" if r["status"] == "RESULTS" else "✗"
        print(f"  {mark} {r['origin']}: {r['status']} "
              f"({len(r['points'])} pontos, {r['execution_time']}s)")


if __name__ == "__main__":
    asyncio.run(main())
