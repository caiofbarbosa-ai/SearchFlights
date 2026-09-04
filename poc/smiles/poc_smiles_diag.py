"""
Smiles POC - Diagnóstico da busca pendente (iteração 5)
Perguntas a responder:
  1. Onde está o toggle "Só milhas" e qual URL ele produz?
  2. A API de disponibilidade é chamada? Responde? Com o quê?
  3. Quanto tempo a busca de award GRU→BKK realmente leva?
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORTS = Path(__file__).resolve().parents[1] / "reports"

API_PATTERNS = ("search", "flight", "miles", "award", "avail", "offer",
                "emissao", "booking", "inventory", "shopping")


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


async def dismiss_overlays(page):
    for text in ("Rejeitar Tudo", "Aceitar todos Cookies", "Outro dia",
                 "Reject All", "Accept All Cookies"):
        try:
            btn = page.locator(f"button:has-text('{text}')").first
            if await btn.is_visible(timeout=800):
                await btn.click()
                await asyncio.sleep(0.5)
        except Exception:
            continue
    await page.evaluate("""() => document.querySelectorAll(
        '#popupOverlay, .popup-overlay, [class*="popup-overlay" i]')
        .forEach(e => e.remove())""")


async def visible(page, sel: str):
    locs = page.locator(sel)
    n = await locs.count()
    for i in range(n):
        if await locs.nth(i).is_visible():
            return locs.nth(i)
    return None


async def main():
    api_hits = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"))
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        async def on_response(resp):
            url = resp.url
            if not any(k in url.lower() for k in API_PATTERNS):
                return
            if "smiler.com.br" in url and "css" in url:
                return
            try:
                body = await resp.text() if resp.status == 200 else ""
            except Exception:
                body = "<stream/binary>"
            api_hits.append({"url": url, "status": resp.status, "len": len(body)})
            log(f"API <- {resp.status} {len(body)}b {url[:130]}")
            if body and len(body) > 200 and any(
                    k in body[:4000].lower() for k in ("milhas", "miles",
                                                       "flight", "segment")):
                snippet = body[:600].replace("\n", " ")
                log(f"    DATA: {snippet}")
                (REPORTS / "smiles_diag_api_payload.json").write_text(
                    body, encoding="utf-8")

        async def on_request(req):
            url = req.url
            if not any(k in url.lower() for k in API_PATTERNS):
                return
            if req.method == "POST":
                pd = (req.post_data or "")[:300]
                log(f"API -> POST {url[:120]}")
                log(f"       body: {pd}")

        page.on("response", on_response)
        page.on("request", on_request)

        log("carregando home...")
        await page.goto("https://www.smiles.com.br/", timeout=60_000)
        try:
            await page.wait_for_load_state("networkidle", timeout=25_000)
        except Exception:
            pass
        await asyncio.sleep(3)
        await dismiss_overlays(page)

        # 1. probe do toggle "Só milhas"
        toggles = await page.evaluate("""() => {
            const out = [];
            for (const el of document.querySelectorAll(
                    'input[type=checkbox], [role=switch], label, span, div')) {
                const t = (el.innerText || el.textContent ||
                           el.labels?.[0]?.innerText || '').trim();
                if (t.startsWith('Só milhas') || t.includes('Somente milhas')) {
                    out.push({tag: el.tagName, type: el.type || '',
                              id: el.id, cls: (el.className || '').toString()
                                  .slice(0, 80), text: t.slice(0, 40),
                              visible: !!el.offsetParent});
                }
            }
            return out.slice(0, 8);
        }""")
        log(f"toggle candidates: {json.dumps(toggles, ensure_ascii=False)}")
        tog = await visible(page, "text=Só milhas")
        if tog:
            await tog.click()
            log("toggle 'Só milhas' clicado")
        else:
            # tentativa via JS: primeiro checkbox com label contendo 'milhas'
            clicked = await page.evaluate("""() => {
                for (const inp of document.querySelectorAll(
                        'input[type=checkbox], [role=switch]')) {
                    const txt = (inp.labels?.[0]?.innerText ||
                                 inp.closest('label')?.innerText ||
                                 inp.parentElement?.innerText || '');
                    if (txt.toLowerCase().includes('milhas') &&
                        inp.offsetParent) {
                        inp.click(); return txt.trim().slice(0, 40);
                    }
                }
                return null;
            }""")
            log(f"toggle via JS: {clicked}")

        await asyncio.sleep(1)

        # 2. fluxo do form (padrão v3 validado)
        el = await visible(page, "input[id*='flightOrigin']")
        await el.click()
        await asyncio.sleep(0.6)
        await page.keyboard.type("GRU", delay=80)
        await asyncio.sleep(1.8)
        li = page.locator(
            "ul.dropdown-menu li, .autocomplete-search li").filter(
            has_text="GRU").first
        await li.click()
        log("origem ok")
        el = await visible(page, "input[id*='flightDestination']")
        await el.click()
        await asyncio.sleep(0.6)
        await page.keyboard.type("BKK", delay=80)
        await asyncio.sleep(1.8)
        li = page.locator(
            "ul.dropdown-menu li, .autocomplete-search li").filter(
            has_text="BKK").first
        await li.click()
        log("destino ok")

        dep = await visible(page, "input[id='startDateId']")
        await dep.click()
        await asyncio.sleep(1.5)
        for _ in range(6):
            found = await page.evaluate(
                """() => [...document.querySelectorAll('td.CalendarDay')]
                    .some(td => (td.getAttribute('aria-label') || '')
                        .includes('dezembro de 2026') && td.offsetParent)""")
            if found:
                break
            arrow = await visible(page, ".calendar-navigation.button-right")
            if not arrow:
                break
            await arrow.click()
            await asyncio.sleep(0.6)
        await page.evaluate("""() => {
            const tds = [...document.querySelectorAll('td.CalendarDay')];
            const t = tds.find(td =>
                /\\s8 de dezembro de 2026/.test(td.getAttribute('aria-label')||'')
                && td.offsetParent);
            if (t) t.click();
        }""")
        await asyncio.sleep(1)
        await page.evaluate("""() => {
            const tds = [...document.querySelectorAll('td.CalendarDay')];
            const t = tds.find(td =>
                /\\s16 de dezembro de 2026/.test(td.getAttribute('aria-label')||'')
                && td.offsetParent);
            if (t) t.click();
        }""")
        log("datas ok")
        vals = await page.evaluate("""() => ({
            o: document.querySelector("input[id*='flightOrigin']")?.value,
            d: document.querySelector("input[id*='flightDestination']")?.value,
            dep: document.querySelector('#startDateId')?.value,
            ret: document.querySelector('#endDateId')?.value})""")
        log(f"campos: {vals}")

        # 3. buscar e observar a URL + APIs em tempo real
        btn = await visible(page, 'button:has-text("Buscar voos")')
        await btn.click()
        log(f"busca submetida; URL inicial: {page.url[:150]}")
        await asyncio.sleep(6)
        log(f"URL pós-busca: {page.url}")
        (REPORTS / "smiles_diag_result_url.txt").write_text(
            page.url, encoding="utf-8")

        # 4. observar por até 8 min
        for i in range(160):
            await asyncio.sleep(3)
            text = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            miles = len(set(re.findall(
                r"(\d{1,3}(?:\.\d{3})+)\s*milhas", text)))
            if i % 10 == 0:
                log(f"... {i*3}s | spinner={'aguarde' in text.lower()} "
                    f"| milhas distintas={miles} | url={page.url[:80]}")
            if miles > 0 or (i > 10 and "aguarde" not in text.lower()):
                log(f"estado mudou em ~{i*3}s: spinner="
                    f"{'aguarde' in text.lower()}, milhas={miles}")
                break

        await page.screenshot(path=str(REPORTS / "smiles_diag_final.png"),
                              full_page=True)
        (REPORTS / "smiles_diag_final.html").write_text(
            await page.content(), encoding="utf-8")
        log(f"final URL: {page.url[:150]}")
        log(f"total de chamadas API vistas: {len(api_hits)}")
        (REPORTS / "smiles_diag_api_hits.json").write_text(
            json.dumps(api_hits, ensure_ascii=False, indent=2),
            encoding="utf-8")

        await asyncio.sleep(3)
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
