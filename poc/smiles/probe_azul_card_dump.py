"""Dump do texto EXATO de um card da Azul (com escapes visíveis) para
calibrar o regex do combo (212.000 pontos + R$ 810,00)."""

import asyncio
import sys
from datetime import date

sys.path.insert(0, ".")
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.scrapers.chrome_cdp import RealChrome
from src.scrapers.azul import (PORTAL, _dismiss_overlays_local,
                               _fill_airport, _fill_dates)
from src.config import settings


def log(m):
    print(m, flush=True)


async def main():
    async with RealChrome(port=9309) as chrome:
        page = await chrome.page()
        await Stealth().apply_stealth_async(page)

        await page.goto(PORTAL, timeout=90_000)
        try:
            await page.wait_for_load_state("networkidle", timeout=20_000)
        except Exception:
            pass
        await asyncio.sleep(4)
        for attempt in range(2):
            try:
                await page.locator("#autocompleteFlightOrigin").first \
                    .wait_for(state="visible", timeout=40_000)
                break
            except Exception:
                if attempt == 0:
                    await page.reload(timeout=60_000)
                    await asyncio.sleep(4)
                    continue
                raise
        for text in ("Aceitar todos", "Aceitar", "Accept All", "OK"):
            try:
                btn = page.locator(f"button:has-text('{text}')").first
                if await btn.is_visible(timeout=500):
                    await btn.click()
                    await asyncio.sleep(0.4)
            except Exception:
                continue

        await _fill_airport(page, "autocompleteFlightOrigin", "GRU")
        await _fill_airport(page, "autocompleteFlightDestination", "BKK")
        await _fill_dates(page)
        btn = page.locator("#btnSearchTickets").first
        if await btn.is_visible(timeout=3000):
            await btn.click()
        try:
            await page.wait_for_load_state("networkidle", timeout=45_000)
        except Exception:
            pass
        body = ""
        for _ in range(20):
            await asyncio.sleep(3)
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            if "selecione o voo" in body.lower():
                break

        # dump: o MENOR ancestral de cada "Mais detalhes" que contenha
        # "milhas" (o texto do card), com repr() para ver escapes
        texts = await page.evaluate("""() => {
            const btns = [...document.querySelectorAll('button')]
                .filter(b => b.offsetParent &&
                    (b.innerText || '').trim() === 'Mais detalhes');
            const out = [];
            const seen = [];
            for (const b of btns) {
                let el = b;
                for (let i = 0; i < 6 && el; i++) {
                    el = el.parentElement;
                    if (!el) break;
                    const t = el.innerText || '';
                    if (t.includes('milhas') && t.includes('GRU')) {
                        if (!seen.some(s => t.includes(s))) {
                            seen.push(t);
                            out.push(t);
                        }
                        break;
                    }
                }
            }
            return out;
        }""")
        log(f"cards capturados: {len(texts)}")
        for i, t in enumerate(texts[:3]):
            print(f"--- card {i+1} (repr, {len(t)} chars) ---")
            print(repr(t)[:800])
        (REPORTS / "azul_cards_repr.txt").write_text(
            "\n\n=====\n\n".join(repr(t) for t in texts),
            encoding="utf-8")
        log("salvo em poc/reports/azul_cards_repr.txt")
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
