"""Sessão visual colaborativa: navegador aberto no Smiles (datas de controle)
com monitoramento em tempo real. O usuário pode interagir à vontade (clicar
Combinar, mover o slider) e o script lê/reporta cada mudança de estado."""

import asyncio
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, ".")
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.scrapers.chrome_cdp import RealChrome
from src.scrapers.smiles import build_url

D, R = date(2026, 12, 8), date(2026, 12, 16)
REPORTS = Path("poc/reports").resolve()
HOLD_S = 300  # janela aberta p/ inspeção


def log(m):
    print(m, flush=True)


async def main():
    async with RealChrome(port=9309) as chrome:
        page = await chrome.page()
        await Stealth().apply_stealth_async(page)

        log("abrindo resultados (datas de controle, dez/2026)...")
        # BUG 09/09: build_url() sem args caía nas datas de PRODUÇÃO
        # (jul/27, que nunca renderiza) — o "combo não renderiza em
        # automação" era isso. Passa as datas de controle definidas acima.
        await page.goto(build_url(departure_date=D, return_date=R),
                        timeout=90_000)
        for text in ("Rejeitar todos", "Aceitar todos Cookies", "Outro dia"):
            try:
                btn = page.locator(f"button:has-text('{text}')").first
                if await btn.is_visible(timeout=800):
                    await btn.click()
                    await asyncio.sleep(0.5)
            except Exception:
                continue

        # aguarda resultados
        for _ in range(40):
            await asyncio.sleep(3)
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            if "milhas" in body.lower() and "aguarde" not in body.lower():
                break
        log("resultados renderizados — janela ABERTA para inspeção")

        # abre o painel de tarifas do card mais barato via JS
        clicked = await page.evaluate("""() => {
            const btns = [...document.querySelectorAll('button')]
                .filter(b => b.offsetParent &&
                    (b.innerText || '').trim() === 'Selecionar tarifa');
            if (!btns.length) return false;
            btns[0].click();
            return true;
        }""")
        log(f"Selecionar tarifa clicado: {clicked}")
        await asyncio.sleep(3)
        await page.screenshot(path=str(REPORTS / "visual_1_painel.png"))

        # estado inicial do painel
        diag = await page.evaluate("""() => {
            const vis = e => {
                const r = e.getBoundingClientRect();
                return r.width > 0 && r.height > 0;
            };
            return [...document.querySelectorAll('div, section')]
                .filter(e => vis(e) && (e.innerText || '')
                    .includes('Combina'))
                .map(e => (e.innerText || '').slice(0, 120)
                    .replace(/\\n/g, ' | '));
        }""")
        log(f"elementos com 'Combina': {len(diag)}")
        for d in diag[:6]:
            print(f"   | {d[:110]}")

        # MONITORAMENTO colaborativo: 5 min lendo mudanças
        prev = ""
        for i in range(60):
            await asyncio.sleep(5)
            try:
                body = await page.evaluate(
                    "() => document.body ? document.body.innerText : ''")
            except Exception:
                continue
            miles = sorted({int(m.replace(".", "")) for m in re.findall(
                r"(\d{1,3}(?:\.\d{3})+)\s*milhas", body)
                if int(m.replace(".", "")) >= 1000})
            combos = [b for b in ([], )]  # placeholder
            marca = f"milhas visíveis: {miles[:6]}"
            if marca != prev:
                log(f"[{(i+1)*5}s] {marca}")
                prev = marca
            await page.screenshot(
                path=str(REPORTS / "visual_monitorando.png")) \
                if i % 6 == 0 else None

        await page.screenshot(path=str(REPORTS / "visual_final.png"),
                              full_page=True)
        body = await page.evaluate(
            "() => document.body ? document.body.innerText : ''")
        (REPORTS / "visual_final_body.txt").write_text(
            body, encoding="utf-8")
        log(f"evidência salva: visual_final.png + visual_final_body.txt")
        log("encerrando — navegador permanece aberto por 10s")
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
