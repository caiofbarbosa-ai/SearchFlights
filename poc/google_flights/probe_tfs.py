"""Probe decisivo: a URL canônica tfs (a que o próprio Google usa) reproduz
o preço que o usuário vê (R$ 6.839 1 adulto / R$ 13.677 total 2 adultos)
em vez do R$ 8.216 da query textual q=?"""

import asyncio
import re
import sys
from base64 import urlsafe_b64decode, urlsafe_b64encode

sys.path.insert(0, ".")
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.scrapers.google_flights import _parse_prices

USER_TFS = ("CBwQAhoeEgoyMDI3LTA3LTIxagcIARIDR1JVcgcIARIDQktLGh4SCjIwMjctMDct"
            "MjhqBwgBEgNCS0tyBwgBEgNHUlVAAUgBcAGCAQsI____________AZgBAQ")


def log(m):
    print(m, flush=True)


def show_template_bytes():
    raw = urlsafe_b64decode(USER_TFS + "=" * (-len(USER_TFS) % 4))
    dates = re.findall(rb"\d{4}-\d{2}-\d{2}", raw)
    codes = re.findall(rb"(?:GRU|BKK|CGH|VCP)", raw)
    log(f"protobuf decodificado: {len(raw)} bytes | datas: {dates} | "
        f"aeroportos: {codes}")


def tfs_for(dep: str, ret: str) -> str:
    """Templateia as datas no protobuf (mesmo comprimento) e re-encoda."""
    raw = urlsafe_b64decode(USER_TFS + "=" * (-len(USER_TFS) % 4))
    raw = raw.replace(b"2027-07-21", dep.encode()).replace(
        b"2027-07-28", ret.encode())
    return urlsafe_b64encode(raw).decode().rstrip("=")


async def probe(p, label: str, tfs: str):
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
    url = (f"https://www.google.com/travel/flights/search?tfs={tfs}"
           f"&hl=pt-BR&gl=BR")
    await page.goto(url, timeout=90_000)
    body = ""
    for _ in range(15):
        await asyncio.sleep(3)
        body = await page.evaluate(
            "() => document.body ? document.body.innerText : ''")
        if len(_parse_prices(body)) >= 3:
            break
    prices = _parse_prices(body)
    log(f"{label}: piso = R$ {prices[0] if prices else '—'} | "
        f"distintas: {prices[:6]}")
    await context.close()
    await browser.close()


async def main():
    show_template_bytes()
    templated = tfs_for("2026-07-21", "2026-07-28")
    log(f"template 2026 preserva tamanho: {len(tfs_for('2027-07-21', '2027-07-28')) == len(USER_TFS)}")
    async with async_playwright() as p:
        await probe(p, "tfs do usuário (datas 21-28/07/2027)", USER_TFS)


if __name__ == "__main__":
    asyncio.run(main())
