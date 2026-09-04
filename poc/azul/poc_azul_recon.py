"""
Azul POC - Recon (2026-09-02, metodologia validada no Google Flights/Smiles)
Inventário dos portais candidatos ANTES de qualquer interação:
  A) voeazul.com.br (widget de busca tem modo resgate?)
  B) azulfidelidade.com.br (portal do programa; interline/parceiros?)
Evidência por step: screenshot + HTML + inventário + manifest de rede.
"""

import asyncio
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORTS = Path(__file__).resolve().parents[1] / "reports"
RESULTS_JSON = REPORTS / "azul_recon_results.json"

TARGETS = [
    ("voeazul", "https://www.voeazul.com.br/br/pt/home"),
    ("fidelidade", "https://www.azulfidelidade.com.br/"),
]

LOGIN_MARKERS = ["entrar", "login", "faça seu login", "acessar conta"]
MILES_LINK_RE = None  # links filtrados em JS abaixo


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


async def dismiss_overlays(page) -> list[str]:
    dismissed = []
    for text in ("Aceitar todos", "Aceitar todos os cookies", "Aceitar",
                 "Accept All", "Reject All", "Rejeitar todos", "OK",
                 "Entendi", "Continuar", "Concordo"):
        try:
            btn = page.locator(f"button:has-text('{text}')").first
            if await btn.is_visible(timeout=600):
                await btn.click()
                dismissed.append(text)
                await asyncio.sleep(random.uniform(0.4, 0.8))
        except Exception:
            continue
    removed = await page.evaluate("""() => {
        const sels = ['#popupOverlay', '.popup-overlay',
                      '[class*="popup-overlay" i]', '[id*="cookie-banner" i]'];
        let n = 0;
        for (const s of sels) document.querySelectorAll(s)
            .forEach(e => { e.remove(); n++; });
        return n;
    }""")
    if removed:
        dismissed.append(f"js-removed:{removed}")
    return dismissed


async def inventory(page) -> dict:
    inputs = await page.eval_on_selector_all(
        "input, select, textarea",
        """els => els.slice(0, 40).map(e => ({
            tag: e.tagName, type: e.type, name: e.name, id: e.id,
            placeholder: e.placeholder, ariaLabel: e.ariaLabel,
            visible: !!e.offsetParent
        }))""")
    buttons = await page.eval_on_selector_all(
        "button, [role='button'], [role='tab']",
        """els => els.slice(0, 50).map(e => ({
            text: (e.innerText || '').trim().slice(0, 50),
            id: e.id, visible: !!e.offsetParent
        }))""")
    links = await page.eval_on_selector_all(
        "a[href]",
        """els => els.filter(e => /milhas|fidelidade|resgat|pelo.?mundo|interline|parceir/i
            .test(e.href + ' ' + (e.innerText || '')))
          .slice(0, 20)
          .map(e => ({text: (e.innerText || '').trim().slice(0, 50),
                      href: e.href.slice(0, 120)}))""")
    return {"inputs": inputs, "buttons": buttons, "miles_links": links}


class NetworkManifest:
    def __init__(self):
        self.entries: list[dict] = []

    async def on_response(self, response):
        try:
            ctype = (response.headers or {}).get("content-type", "")
            if response.status != 200:
                return
            if not ("json" in ctype or any(
                    k in response.url.lower()
                    for k in ("search", "flight", "miles", "award", "avail",
                              "redeem", "interline", "graphql", "api"))):
                return
            if any(h in response.url for h in ("gstatic", "fonts")):
                return
            body = await response.text()
            self.entries.append({
                "url": response.url[:300], "status": response.status,
                "content_type": ctype[:80], "bytes": len(body),
                "snippet": body[:400] if "json" in ctype and len(body) > 300 else "",
                "time": datetime.now().isoformat(),
            })
        except Exception:
            pass


async def recon_target(page, name: str, url: str, manifest: NetworkManifest) -> dict:
    result = {"target": name, "url": url, "final_url": None,
              "status": "UNKNOWN", "inventory": {}, "steps": []}
    log(f"--- {name}: {url}")
    try:
        await page.goto(url, timeout=60_000)
        try:
            await page.wait_for_load_state("networkidle", timeout=20_000)
        except Exception:
            pass
        await asyncio.sleep(4)

        dismissed = await dismiss_overlays(page)
        log(f"    overlays: {dismissed}")

        await page.screenshot(path=str(REPORTS / f"azul_recon_{name}.png"),
                              full_page=True)
        (REPORTS / f"azul_recon_{name}.html").write_text(
            await page.content(), encoding="utf-8")
        result["steps"].append({"step": "home", "url": page.url,
                                "screenshot": f"azul_recon_{name}.png"})

        result["inventory"] = await inventory(page)
        inv = result["inventory"]
        log(f"    URL: {page.url[:100]}")
        log(f"    inputs visíveis: {sum(1 for i in inv['inputs'] if i['visible'])}"
            f" | botões: {sum(1 for b in inv['buttons'] if b['visible'])}")
        for i in inv["inputs"]:
            if i["visible"] and (i.get("placeholder") or i.get("ariaLabel")):
                print(f"      input ph={i.get('placeholder')!r} "
                      f"aria={i.get('ariaLabel')!r} id={i.get('id')!r}")
        for b in inv["buttons"]:
            if b["visible"] and b["text"]:
                print(f"      button {b['text']!r}")
        for l in inv["miles_links"][:10]:
            print(f"      link {l['text']!r} -> {l['href']}")

        result["final_url"] = page.url
        body = (await page.evaluate(
            "() => document.body ? document.body.innerText : ''")).lower()
        has_search = any(i["visible"] for i in inv["inputs"]
                         if "orig" in (i.get("placeholder") or "").lower()
                         or "destino" in (i.get("placeholder") or "").lower())
        if has_search:
            result["status"] = "SEARCH_FORM"
        elif any(m in body for m in LOGIN_MARKERS) and len(body) < 3000:
            result["status"] = "LOGIN_WALL"
        else:
            result["status"] = "PORTAL_OK_SEM_FORM"
    except Exception as exc:
        result["status"] = "ERROR"
        result["error"] = str(exc)[:300]
        log(f"    [ERROR] {exc}")
    return result


async def main():
    started = time.monotonic()
    REPORTS.mkdir(parents=True, exist_ok=True)
    manifest = NetworkManifest()

    print("=" * 70)
    print("AZUL POC — RECON (voeazul + azulfidelidade)")
    print("=" * 70)

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome", headless=False,
            args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="pt-BR",
            timezone_id="America/Sao_Paulo")
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        page.on("response", manifest.on_response)

        for name, url in TARGETS:
            r = await recon_target(page, name, url, manifest)
            results.append(r)
            await asyncio.sleep(random.uniform(3, 6))

        await context.close()
        await browser.close()

    RESULTS_JSON.write_text(
        json.dumps({"targets": results,
                    "network": manifest.entries,
                    "execution_time": round(time.monotonic() - started, 1)},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nRESUMO:")
    for r in results:
        print(f"  {r['target']}: {r['status']} (final: {r.get('final_url', '')[:80]})")
    print(f"  entradas de rede capturadas: {len(manifest.entries)}")


if __name__ == "__main__":
    asyncio.run(main())
