"""
Azul POC - Recon via CDP em Chrome real (padrão que destravou o Smiles)
Detectar: página de bloqueio ("comportamento incomum") vs portal renderizado;
inventário de widget de resgate/interline; links do programa Fidelidade.
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
DEBUG_PORT = 9225

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

TARGETS = [
    ("pelomundo", "https://azulpelomundo.voeazul.com.br/"),
    ("voeazul", "https://www.voeazul.com.br/br/pt/home"),
]

BLOCK_MARKERS = ["comportamento incomum", "acesso foi limitado",
                 "unusual traffic", "access denied"]


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


async def main():
    chrome_exe = next((c for c in CHROME_CANDIDATES if Path(c).exists()), None)
    if not chrome_exe:
        log("[FAIL] Chrome não encontrado")
        return 1

    profile_dir = tempfile.mkdtemp(prefix="azul_cdp_")
    log(f"lançando Chrome real (perfil temp) na porta {DEBUG_PORT}")
    proc = subprocess.Popen([
        chrome_exe, f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={profile_dir}", "--no-first-run",
        "--no-default-browser-check", "--window-size=1920,1080", "about:blank"])
    time.sleep(4)

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(
            f"http://localhost:{DEBUG_PORT}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})

        for name, url in TARGETS:
            r = {"target": name, "url": url, "status": "UNKNOWN"}
            log(f"--- {name}: {url}")
            try:
                await page.goto(url, timeout=60_000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=20_000)
                except Exception:
                    pass
                await asyncio.sleep(4)

                text = await page.evaluate(
                    "() => document.body ? document.body.innerText : ''")
                lower = text.lower()

                if any(m in lower for m in BLOCK_MARKERS):
                    r["status"] = "BLOCKED"
                    log(f"    BLOQUEADO: {[m for m in BLOCK_MARKERS if m in lower]}")
                else:
                    # cookies/consent
                    for t in ("Aceitar todos", "Aceitar", "Accept All",
                              "OK, continuar"):
                        try:
                            btn = page.locator(f"button:has-text('{t}')").first
                            if await btn.is_visible(timeout=600):
                                await btn.click()
                                await asyncio.sleep(0.6)
                        except Exception:
                            continue

                    await page.screenshot(
                        path=str(REPORTS / f"azul_cdp_{name}.png"),
                        full_page=True)
                    (REPORTS / f"azul_cdp_{name}.html").write_text(
                        await page.content(), encoding="utf-8")

                    inv = await page.eval_on_selector_all(
                        "input, button, [role='tab'], [role='button']",
                        """els => els.filter(e => e.offsetParent).slice(0, 40)
                            .map(e => ({tag: e.tagName,
                                        text: (e.innerText || e.placeholder ||
                                               e.ariaLabel || '')
                                           .trim().slice(0, 40),
                                        id: e.id}))""")
                    r["inventory"] = inv
                    log(f"    URL: {page.url[:100]}")
                    log(f"    elementos visíveis: {len(inv)}")
                    for e in inv[:25]:
                        print(f"      {e['tag']} {e['text']!r} id={e['id']!r}")

                    links = await page.eval_on_selector_all(
                        "a[href]",
                        """els => els.filter(e =>
                                /milhas|fidelidade|resgat|pelo.?mundo|interline|parceir/i
                                .test(e.href + ' ' + (e.innerText || '')))
                            .slice(0, 15)
                            .map(e => ({text: (e.innerText || '').trim()
                                .slice(0, 50), href: e.href.slice(0, 130)}))""")
                    r["miles_links"] = links
                    for l in links:
                        print(f"      link {l['text']!r} -> {l['href']}")

                    has_search = any(
                        "orig" in (e.get("text") or "").lower()
                        or e.get("id", "").lower().startswith(("orig", "dest"))
                        for e in inv)
                    r["status"] = "SEARCH_FORM" if has_search else "PORTAL_OK"
            except Exception as exc:
                r["status"] = "ERROR"
                r["error"] = str(exc)[:300]
                log(f"    [ERROR] {exc}")
            results.append(r)

        await browser.close()

    try:
        proc.terminate()
    except Exception:
        pass

    print("\nRESUMO:")
    for r in results:
        print(f"  {r['target']}: {r['status']}")
    (REPORTS / "azul_cdp_recon_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    asyncio.run(main())
