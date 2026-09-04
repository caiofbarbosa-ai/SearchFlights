"""
Smiles POC - Probe de DOM (iteração 3 do recon)
Objetivo: fatos, não hipóteses. Clica nos campos REAIS visíveis e documenta
o que acontece (dropdown, sugestões, calendário, readonly, iframes).
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


async def dismiss_overlays(page):
    for text in ("Rejeitar Tudo", "Aceitar todos Cookies", "Outro dia"):
        try:
            btn = page.locator(f"button:has-text('{text}')").first
            if await btn.is_visible(timeout=800):
                await btn.click()
                await asyncio.sleep(0.6)
                print(f"  overlay fechado via botão: {text!r}")
        except Exception:
            continue
    await page.evaluate("""() => document.querySelectorAll(
        '#popupOverlay, .popup-overlay, [class*="popup-overlay" i]')
        .forEach(e => e.remove())""")


async def probe_inputs(page, label: str):
    infos = await page.eval_on_selector_all(
        "input[id*='flightOrigin'], input[id*='flightDestination'], "
        "input[id='startDateId'], input[id='endDateId']",
        """els => els.map(e => ({
            id: e.id, visible: !!e.offsetParent,
            readonly: e.readOnly, disabled: e.disabled,
            value: e.value, placeholder: e.placeholder,
            rect: (r => ({x: Math.round(r.x), y: Math.round(r.y),
                          w: Math.round(r.width), h: Math.round(r.height)}))
                        (e.getBoundingClientRect()),
        }))""")
    print(f"  [{label}] campos do widget:")
    for i in infos:
        print(f"    {i['id']:<28} vis={i['visible']} ro={i['readonly']} "
              f"dis={i['disabled']} val={i['value']!r} rect={i['rect']}")
    return infos


async def visible_locator(page, sel: str):
    """Retorna locator do 1º elemento visível que casa o seletor."""
    locs = page.locator(sel)
    n = await locs.count()
    for i in range(n):
        if await locs.nth(i).is_visible():
            return locs.nth(i), i
    return None, None


async def main():
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

        print(f"[{datetime.now():%H:%M:%S}] carregando home...")
        await page.goto("https://www.smiles.com.br/", timeout=60_000)
        try:
            await page.wait_for_load_state("networkidle", timeout=25_000)
        except Exception:
            pass
        await asyncio.sleep(3)
        await dismiss_overlays(page)
        print(f"  iframes na página: {len(page.frames) - 1}")

        await probe_inputs(page, "antes")

        # ---- PROBE 1: campo origem VISÍVEL ----
        el, idx = await visible_locator(page, "input[id*='flightOrigin']")
        print(f"\n  clicando origem visível (índice {idx})...")
        if el:
            await el.click()
            await asyncio.sleep(1.5)
            await probe_inputs(page, "pós-clique origem")
            await page.screenshot(
                path=str(REPORTS / "smiles_probe_1_origin_open.png"))
            # dropdown/sugestões que apareceram?
            panels = await page.eval_on_selector_all(
                "[role='listbox'], [role='dialog'], ul[class*='dropdown'], "
                "div[class*='autocomplete'], div[class*='suggestion']",
                """els => els.filter(e => e.offsetParent).slice(0, 5).map(e => ({
                    tag: e.tagName, role: e.getAttribute('role'),
                    cls: (e.className || '').toString().slice(0, 80),
                    items: Array.from(e.querySelectorAll('li')).slice(0, 8)
                        .map(li => (li.innerText || '').trim().slice(0, 60)
                            .replace(/\\n/g, ' | '))
                }))""")
            print(f"  painéis abertos pós-clique: {json.dumps(panels, ensure_ascii=False, indent=2)[:1500]}")

            await page.keyboard.type("GRU", delay=90)
            await asyncio.sleep(2)
            await page.screenshot(
                path=str(REPORTS / "smiles_probe_2_typed.png"))
            sugg = await page.eval_on_selector_all(
                "li, [role='option']",
                """els => els.filter(e => e.offsetParent && e.innerText)
                    .slice(0, 12).map(e => (e.innerText || '')
                        .trim().slice(0, 70).replace(/\\n/g, ' | '))""")
            print(f"  opções visíveis pós digitar GRU: {json.dumps(sugg, ensure_ascii=False)}")
            await probe_inputs(page, "pós-digitar")
        else:
            print("  [FAIL] nenhum input de origem visível!")

        # ---- PROBE 2: campo data VISÍVEL ----
        el, idx = await visible_locator(page, "input[id='startDateId']")
        print(f"\n  clicando data Ida visível (índice {idx})...")
        if el:
            await el.click()
            await asyncio.sleep(1.5)
            await page.screenshot(
                path=str(REPORTS / "smiles_probe_3_calendar.png"))
            cal = await page.eval_on_selector_all(
                "[class*='calendar'], [class*='datepicker'], [class*='Calendar']",
                """els => els.filter(e => e.offsetParent).slice(0, 3).map(e => ({
                    cls: (e.className || '').toString().slice(0, 100),
                    text: (e.innerText || '').slice(0, 200).replace(/\\n/g, ' | ')
                }))""")
            print(f"  calendário aberto: {json.dumps(cal, ensure_ascii=False, indent=2)[:1200]}")

        print(f"\n[{datetime.now():%H:%M:%S}] probe concluído")
        await asyncio.sleep(3)
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
