"""
Smiles POC - Diagnóstico v2: por que a busca de disponibilidade nunca dispara?
Tráfego completo (sem filtro), erros de console/JS, status >= 400.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


async def visible(page, sel: str):
    locs = page.locator(sel)
    n = await locs.count()
    for i in range(n):
        if await locs.nth(i).is_visible():
            return locs.nth(i)
    return None


async def dismiss_overlays(page):
    for text in ("Rejeitar Tudo", "Aceitar todos Cookies", "Outro dia",
                 "Reject All", "Accept All Cookies"):
        try:
            btn = page.locator(f"button:has-text('{text}')").first
            if await btn.is_visible(timeout=600):
                await btn.click()
                await asyncio.sleep(0.4)
        except Exception:
            continue
    await page.evaluate("""() => document.querySelectorAll(
        '#popupOverlay, .popup-overlay, [class*="popup-overlay" i]')
        .forEach(e => e.remove())""")


async def main():
    events = []

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
            interesting = (
                resp.status >= 400
                or "apigw" in url
                or "members" in url
                or "smiles.com.br/mfe-apps" in url and "check-env" not in url
            )
            if not interesting:
                return
            try:
                body = await resp.text() if resp.status != 204 else ""
            except Exception:
                body = "<binary>"
            entry = {"t": datetime.now().isoformat(), "status": resp.status,
                     "url": url[:250], "len": len(body),
                     "body_head": body[:400] if len(body) < 5000 else body[:400]}
            events.append(entry)
            log(f"<< {resp.status} {len(body)}b {url[:120]}")
            if resp.status >= 400 and body:
                log(f"   body: {body[:200]}")

        def on_request(req):
            url = req.url
            if "apigw" in url or "members" in url:
                pd = (req.post_data or "")[:200]
                log(f">> {req.method} {url[:120]}")
                if pd:
                    log(f"   body: {pd}")

        page.on("console", lambda m: log(f"CONSOLE-{m.type}: {m.text[:150]}")
                if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: log(f"PAGEERROR: {str(e)[:200]}"))
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

        # fluxo do form (validado)
        el = await visible(page, "input[id*='flightOrigin']")
        await el.click()
        await asyncio.sleep(0.6)
        await page.keyboard.type("GRU", delay=80)
        await asyncio.sleep(1.8)
        await page.locator(
            "ul.dropdown-menu li, .autocomplete-search li").filter(
            has_text="GRU").first.click()
        el = await visible(page, "input[id*='flightDestination']")
        await el.click()
        await asyncio.sleep(0.6)
        await page.keyboard.type("BKK", delay=80)
        await asyncio.sleep(1.8)
        await page.locator(
            "ul.dropdown-menu li, .autocomplete-search li").filter(
            has_text="BKK").first.click()
        log("aeroportos ok")

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
            await asyncio.sleep(0.5)
        await page.evaluate("""() => {
            const pick = d => {
                const t = [...document.querySelectorAll('td.CalendarDay')]
                    .find(td => new RegExp('\\\\s' + d + ' de dezembro de 2026')
                        .test(td.getAttribute('aria-label') || '') && td.offsetParent);
                if (t) t.click();
            };
            pick(8);
        }""")
        await asyncio.sleep(1)
        await page.evaluate("""() => {
            const pick = d => {
                const t = [...document.querySelectorAll('td.CalendarDay')]
                    .find(td => new RegExp('\\\\s' + d + ' de dezembro de 2026')
                        .test(td.getAttribute('aria-label') || '') && td.offsetParent);
                if (t) t.click();
            };
            pick(16);
        }""")
        log("datas ok")

        btn = await visible(page, 'button:has-text("Buscar voos")')
        await btn.click()
        log("busca submetida; observando tráfego por 6 min...")

        for i in range(120):
            await asyncio.sleep(3)
            if i % 20 == 0:
                log(f"... {i*3}s (URL: {page.url[:70]})")

        await page.screenshot(path=str(REPORTS / "smiles_diag2_final.png"),
                              full_page=True)
        (REPORTS / "smiles_diag2_events.json").write_text(
            json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"fim; eventos capturados: {len(events)}")

        await asyncio.sleep(3)
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
