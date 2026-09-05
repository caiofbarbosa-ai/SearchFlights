"""Azul scraper (Fase 8) — arquitetura validada na POC 2026-09-02:
Chrome real + CDP no portal azulpelomundo.voeazul.com.br (guest);
datas por placeholder DD/MM/YYYY (partida) + input vazio (volta);
códigos de aeroporto casados ENTRE PARÊNTESES; extração pontos /
pontos + R$."""

import asyncio
import random
import re

from src.config import settings
from src.models import FlightQuote, Status
from src.scrapers.chrome_cdp import RealChrome


async def _dismiss_overlays_local(page):
    for text in ("Aceitar todos", "Aceitar", "Accept All", "OK", "Entendi"):
        try:
            btn = page.locator(f"button:has-text('{text}')").first
            if await btn.is_visible(timeout=500):
                await btn.click()
                await asyncio.sleep(0.4)
        except Exception:
            continue

PORTAL = "https://azulpelomundo.voeazul.com.br/"
POINTS_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+)\s*pontos", re.IGNORECASE)
COMBO_RE = re.compile(
    r"(\d{1,3}(?:\.\d{3})+)\s*pontos\s*\+\s*R\$\s?([\d.,]+)", re.IGNORECASE)


def random_sleep(lo: float = 0.4, hi: float = 0.9):
    return asyncio.sleep(random.uniform(lo, hi))


async def _fill_airport(page, input_id: str, code: str) -> bool:
    el = page.locator(f"#{input_id}").first
    if not await el.is_visible():
        return False
    await el.click()
    await random_sleep()
    await page.keyboard.type(code, delay=90)
    await asyncio.sleep(2)
    li = page.locator(
        "li, [role='option'], [class*='autocomplete'] li").filter(
        has_text=re.compile(r"\(" + code + r"\)")).first
    try:
        if await li.is_visible(timeout=3000):
            await li.click()
        else:
            await page.keyboard.press("Enter")
    except Exception:
        await page.keyboard.press("Enter")
    await asyncio.sleep(1)
    return True


async def _fill_dates(page) -> None:
    dep = page.locator("input[placeholder='DD/MM/YYYY']").first
    await dep.click()
    await asyncio.sleep(0.5)
    await page.keyboard.press("Control+A")
    await page.keyboard.type(
        settings.departure_date.strftime("%d/%m/%Y"), delay=50)
    await asyncio.sleep(1)
    log_dep = settings.departure_date.strftime("%d/%m/%Y")

    # retorno: input de data VAZIO (ambos compartilham o placeholder)
    focused_empty = await page.evaluate(
        "() => { const e = document.activeElement; return e && "
        "e.tagName === 'INPUT' && !e.value; }")
    if not focused_empty:
        target = await page.evaluate("""() => {
            const isDate = e => e.offsetParent && e.tagName === 'INPUT'
                && (/^\\d{2}\\/\\d{2}\\/\\d{4}$/.test(e.value)
                    || /data|DD\\/MM/i.test(e.placeholder));
            const empty = [...document.querySelectorAll('input')]
                .filter(isDate).find(e => !e.value);
            if (!empty) return null;
            const r = empty.getBoundingClientRect();
            return {x: r.x + r.width / 2, y: r.y + r.height / 2};
        }""")
        if target:
            await page.mouse.click(target["x"], target["y"])
            await asyncio.sleep(0.6)
    await page.keyboard.type(
        settings.return_date.strftime("%d/%m/%Y"), delay=50)
    await asyncio.sleep(1)
    return log_dep


async def _search_origin(page, origin: str) -> FlightQuote:
    quote = FlightQuote(
        source="azul", origin=origin, destination=settings.destination,
        departure_date=settings.departure_date,
        return_date=settings.return_date, passengers=settings.adults,
        status=Status.UNKNOWN_ERROR)

    for attempt in range(2):  # goto 90s + 1 retry (SPA lenta/rede)
        try:
            await page.goto(PORTAL, timeout=90_000)
            break
        except Exception:
            if attempt == 0:
                await asyncio.sleep(10)
                continue
            quote.status = Status.TIMEOUT
            return quote
    try:
        await page.wait_for_load_state("networkidle", timeout=20_000)
    except Exception:
        pass
    await asyncio.sleep(4)

    # widget é SPA lazy: espera de verdade (wait_for; is_visible não espera)
    for attempt in range(2):
        try:
            await page.locator("#autocompleteFlightOrigin").first \
                .wait_for(state="visible", timeout=40_000)
            break
        except Exception:
            if attempt == 0:
                print(f"    [WARN] widget não veio; reload...")
                await page.reload(timeout=60_000)
                await asyncio.sleep(4)
                await _dismiss_overlays_local(page)
                continue
            quote.status = Status.PARSER_ERROR
            return quote

    for text in ("Aceitar todos", "Aceitar", "Accept All", "OK"):
        try:
            btn = page.locator(f"button:has-text('{text}')").first
            if await btn.is_visible(timeout=500):
                await btn.click()
                await asyncio.sleep(0.4)
        except Exception:
            continue

    if not await _fill_airport(page, "autocompleteFlightOrigin", origin):
        quote.status = Status.PARSER_ERROR
        return quote
    if not await _fill_airport(page, "autocompleteFlightDestination",
                               settings.destination):
        quote.status = Status.PARSER_ERROR
        return quote

    await _fill_dates(page)

    # passageiros: +1 adulto (default 1 -> settings.adults)
    for _ in range(max(0, settings.adults - 1)):
        try:
            plus = page.locator("#btn-add-passenger-counterAdult").first
            if await plus.is_visible(timeout=1500):
                await plus.click()
                await asyncio.sleep(0.4)
        except Exception:
            break

    btn = page.locator("#btnSearchTickets").first
    if await btn.is_visible(timeout=3000):
        await btn.click()
    try:
        await page.wait_for_load_state("networkidle", timeout=45_000)
    except Exception:
        pass

    body = ""
    for _ in range(20):  # poll 60s
        await asyncio.sleep(3)
        try:
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
        except Exception:
            continue
        if len(POINTS_RE.findall(body)) >= 1 and "selecione o voo" in \
                body.lower():
            break

    lower = body.lower()
    points = sorted({int(m.replace(".", "")) for m in POINTS_RE.findall(body)
                     if int(m.replace(".", "")) >= 1000})
    combos = [(int(p.replace(".", "")),
               float(c.replace(".", "").replace(",", ".")))
              for p, c in COMBO_RE.findall(body)]
    combos = [c for c in combos if c[0] >= 1000]

    if any(m in lower for m in ("comportamento incomum", "acesso foi limitado")):
        quote.status = Status.BLOCKED
    elif "não há voos disponíveis" in lower or "nenhum" in lower:
        quote.status = Status.NO_AVAILABILITY
    elif points:
        quote.status = Status.SUCCESS
        quote.miles = points[0]  # 8.7 menor só-pontos
        # 8.8 híbrido: maior combinação de pontos sob 120k
        valid = [c for c in combos if c[0] <= settings.hybrid_max_miles]
        if valid:
            quote.hybrid_miles, quote.cash_component_brl = max(
                valid, key=lambda c: c[0])
        quote.raw_sample = {"distinct_points": points[:10],
                            "combos": combos[:8]}
    else:
        quote.status = Status.PARSER_ERROR
    return quote


async def scrape() -> list[FlightQuote]:
    quotes: list[FlightQuote] = []
    async with RealChrome(port=9302) as chrome:
        page = await chrome.page()
        for origin in settings.origins:
            origin = origin.strip()
            try:
                quotes.append(await _search_origin(page, origin))
            except Exception as exc:
                quotes.append(FlightQuote(
                    source="azul", origin=origin,
                    destination=settings.destination,
                    departure_date=settings.departure_date,
                    return_date=settings.return_date,
                    passengers=settings.adults,
                    status=Status.UNKNOWN_ERROR,
                    raw_sample={"error": str(exc)[:300]}))
            await random_sleep(3, 6)
    return quotes
