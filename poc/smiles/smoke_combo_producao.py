"""Smoke do fluxo de PRODUÇÃO do combo: chama _capture_money_combo direto
(pós-fix 10/09: seletor do Combinar por ancestralidade + input[type=range] +
set do slider via native setter). Sem lógica duplicada — o que vale aqui é
exatamente o código que roda no ciclo diário.

Rodar da raiz:  python poc/smiles/smoke_combo_producao.py
"""

import asyncio
import sys
from datetime import datetime

sys.path.insert(0, ".")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from src.scrapers.chrome_cdp import RealChrome
from src.scrapers.smiles import MILES_RE, _capture_money_combo, build_url


def log(m):
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


async def main():
    async with RealChrome(port=9306, driver="playwright") as chrome:
        page = await chrome.page()
        log("abrindo busca (config de produção: jul/27, GRU, 1 adulto)...")
        await page.goto(build_url("GRU"), timeout=90_000)
        for text in ("Rejeitar todos", "Rejeitar Tudo",
                     "Aceitar todos Cookies", "Outro dia"):
            try:
                btn = page.locator(f"button:has-text('{text}')").first
                if await btn.is_visible(timeout=800):
                    await btn.click()
                    await asyncio.sleep(0.5)
            except Exception:
                continue
        ok = False
        for _ in range(60):
            await asyncio.sleep(3)
            try:
                body = await page.evaluate(
                    "() => document.body ? document.body.innerText : ''") \
                    or ""
            except Exception:
                continue
            if "aguarde" not in body.lower() and body.strip() and \
                    [m for m in MILES_RE.findall(body)
                     if int(m.replace(".", "")) >= 1000]:
                ok = True
                break
        log(f"página renderizada: {ok}")

        combo = await _capture_money_combo(page)
        log(f"RESULTADO _capture_money_combo: {combo}")
        if combo:
            log(f"formato Telegram: 🎫 GRU: {combo[0]:,} milhas + "
                f"R$ {combo[1]:.0f} (combo ≤210k)".replace(",", "."))


if __name__ == "__main__":
    asyncio.run(main())
