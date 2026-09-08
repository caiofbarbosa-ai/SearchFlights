"""Probe neutro: log completo de rede durante busca Smiles julho/2027.
Sem hipóteses: captura TODAS as requisições e respostas (URL, status,
tamanho) + o estado da página, para ver o que de fato acontece."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, ".")
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.scrapers.smiles import build_url

REPORTS = Path("poc/reports").resolve()


def log(m):
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


async def main():
    net = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome", headless=False,
            args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="pt-BR",
            timezone_id="America/Sao_Paulo")
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        async def on_response(resp):
            url = resp.url
            try:
                body = None
                interesting = any(k in url.lower() for k in (
                    "avail", "search", "flight", "smiles", "miles",
                    "offer", "emissao"))
                size = None
                if interesting:
                    try:
                        body = await resp.text()
                        size = len(body)
                    except Exception:
                        size = -1
                net.append({"t": datetime.now().strftime("%H:%M:%S"),
                            "status": resp.status, "url": url[:200],
                            "size": size})
                if interesting and size and size > 0:
                    log(f"  NET {resp.status} {size}b {url[:130]}")
            except Exception:
                pass

        page.on("response", on_response)

        log("abrindo URL de julho/2027 (2 adultos)...")
        await page.goto(build_url("GRU"), timeout=90_000)
        log("goto retornou")

        # observa 4 min: estado da página a cada 10s
        import re
        for i in range(24):
            await asyncio.sleep(10)
            try:
                body = await page.evaluate(
                    "() => document.body ? document.body.innerText : ''")
            except Exception:
                body = ""
            miles = sorted({int(m.replace(".", "")) for m in re.findall(
                r"(\d{1,3}(?:\.\d{3})+)\s*milhas", body)
                if int(m.replace(".", "")) >= 1000})
            aguarde = "aguarde" in body.lower()
            sem_voos = "não há voos" in body.lower() or \
                "nenhum" in body.lower()
            log(f"[{i*10+10}s] aguarde={aguarde} semVoos={sem_voos} "
                f"milhasVisíveis={len(miles)} {miles[:4]}")

        await page.screenshot(path=str(REPORTS / "july_neutral_final.png"),
                              full_page=True)
        (REPORTS / "july_neutral_body.txt").write_text(
            await page.evaluate(
                "() => document.body ? document.body.innerText : ''"),
            encoding="utf-8")
        import json
        (REPORTS / "july_neutral_net.json").write_text(
            json.dumps(net, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"total de chamadas registradas: {len(net)}")
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
