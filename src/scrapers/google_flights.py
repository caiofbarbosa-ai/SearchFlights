"""Google Flights scraper (Fase 6) — arquitetura validada na POC 2026-09-02:
URL direta `q=` com locale fixado; extração por body text (resultados vivem
em <li class="pIav2d">, não role=listitem); classificação de estados ANTES
da extração (preços de sugestões não são resultados)."""

import asyncio
import logging
import random
import re
from datetime import date
from urllib.parse import quote

# Patchright (Playwright com vazamentos de CDP corrigidos): o Google detecta
# Playwright padrão e serve tarifas DEGRADADAS (só a 1ª onda — 8.216 vs
# 6.839 real, evidência 2026-09-03). Patchright recebe as ondas completas.
from patchright.async_api import async_playwright

from src.config import settings
from src.models import FlightQuote, Status

log = logging.getLogger("flight_monitor.scrapers.google")

PRICE_RE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)")
PRICE_FLOOR_BRL = 100

# Companhias relevantes GRU/CGH/VCP → BKK (+ domésticas para conexões)
AIRLINE_RE = re.compile(
    r"(Qatar Airways|Malaysia Airlines|LATAM|Emirates|Etihad Airways|Etihad|"
    r"Turkish Airlines|SWISS|KLM|Air France|Lufthansa|Ethiopian Airlines|"
    r"Ethiopian|Japan Airlines|British Airways|Iberia|American Airlines|"
    r"United Airlines|United|Delta Air Lines|Delta|ITA Airways|"
    r"TAP Air Portugal|Air Canada|Korean Air|All Nippon Airways|"
    r"Singapore Airlines|Cathay Pacific|Austrian Airlines|Finnair|"
    r"Copa Airlines|Avianca|GOL|Azul Linhas Aéreas|Azul|Royal Air Maroc|"
    r"Air Cairo|Saudia|Oman Air)",
    re.IGNORECASE)

# candidatos a cartão: contêm preço, horário e "ida e volta"; dedup por
# contenção em Python (o container geral também casa por includes)
CARD_JS = """() => {
    const els = [...document.querySelectorAll('li, div')].filter(e =>
        e.offsetParent && e.innerText && e.innerText.includes('ida e volta')
        && /R\\$/.test(e.innerText) && /\\d{1,2}:\\d{2}/.test(e.innerText));
    return els.sort((a, b) => a.innerText.length - b.innerText.length)
        .slice(0, 60).map(e => e.innerText);
}"""

BLOCK_MARKERS = ["unusual traffic", "tráfego incomum", "/sorry/",
                 "confirm you're human"]
NOT_OPEN_MARKERS = ["muito distante", "data de voo solicitada",
                    "prices are not available", "não estão disponíveis"]
NO_RESULTS_MARKERS = ["nenhum voo para sua pesquisa",
                      "não há nenhum voo"]


def build_q_url(origin: str, destination: str, departure: date,
                return_date: date) -> str:
    q = (f"Flights from {origin} to {destination} "
         f"on {departure.isoformat()} through {return_date.isoformat()}")
    return ("https://www.google.com/travel/flights"
            f"?q={quote(q)}&hl=pt-BR&gl=BR&curr=BRL")


def _parse_prices(text: str) -> list[int]:
    out = set()
    for match in PRICE_RE.findall(text):
        value = int(round(float(match.replace(".", "").replace(",", "."))))
        if value >= PRICE_FLOOR_BRL:
            out.add(value)
    return sorted(out)


async def _search_origin(page, origin: str) -> FlightQuote:
    url = build_q_url(origin, settings.destination,
                      settings.departure_date, settings.return_date)
    for attempt in range(2):  # 1 retry: goto pode estourar sob carga paralela
        try:
            await page.goto(url, timeout=90_000)
            break
        except Exception:
            if attempt == 0:
                await asyncio.sleep(10)
                continue
            raise
    await page.wait_for_load_state("domcontentloaded", timeout=30_000)

    # A TARIFA CARREGA EM ONDAS (evidência do usuário, 2026-09-03:
    # 8.239 -> 7.505 -> 6.839). Janela fixa de ~90s rastreando o MÍNIMO —
    # extrair na primeira onda infla o preço e perde as ondas seguintes.
    body = ""
    floor = None
    for i in range(30):  # janela fixa ~90s
        await asyncio.sleep(3)
        try:
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
        except Exception:
            continue
        prices = _parse_prices(body)
        if not prices:
            continue
        if floor is None or prices[0] < floor:
            if floor is not None:
                log.info("[%s] onda mais barata: R$ %s -> R$ %s",
                         origin, f"{floor:,}", f"{prices[0]:,}")
            floor = prices[0]

    lower = body.lower()
    prices = _parse_prices(body)
    # rota fina (ex.: VCP→BKK) pode ter 1-2 opções: ≥1 preço + shell de
    # resultados renderizado = SUCCESS (exigir 3+ classificava errado)
    results_shell = ("principais voos" in lower or "a partir de" in lower
                     or "menores preços" in lower)
    status = Status.UNKNOWN_ERROR
    if any(m in lower for m in BLOCK_MARKERS) or "/sorry/" in page.url:
        status = Status.BLOCKED
    elif prices and results_shell:
        status = Status.SUCCESS
    elif any(m in lower for m in NO_RESULTS_MARKERS):
        status = Status.NO_AVAILABILITY
    elif any(m in lower for m in NOT_OPEN_MARKERS):
        status = Status.CALENDAR_NOT_OPEN
    elif not prices:
        status = Status.PARSER_ERROR

    quote = FlightQuote(
        source="google", origin=origin, destination=settings.destination,
        departure_date=settings.departure_date,
        return_date=settings.return_date,
        status=status, passengers=settings.adults,
    )
    if status == Status.SUCCESS:
        per_passenger = floor if floor is not None else prices[0]
        # spec: total para 2 adultos (Google exibe por passageiro)
        quote.cash_price_brl = float(per_passenger * settings.adults)
        quote.price_is_per_passenger = False

        # companhia(s) do cartão do voo mais barato: enumera candidatos,
        # deduplica por contenção e escolhe o de menor preço
        try:
            texts = await page.evaluate(CARD_JS) or []
            texts.sort(key=len)
            cards: list[str] = []
            for t in texts:
                if not any(t in acc for acc in cards):
                    cards.append(t)
            best = None  # (preço, companhias)
            for card in cards[:20]:
                p_card = sorted(_parse_prices(card))
                if not p_card:
                    continue
                names: list[str] = []
                seen_names: set[str] = set()
                for m in AIRLINE_RE.finditer(card.replace("\n", " ")):
                    key = m.group(1).lower()
                    if key not in seen_names:
                        seen_names.add(key)
                        names.append(m.group(1))
                if best is None or p_card[0] < best[0]:
                    best = (p_card[0], ", ".join(names)[:120] or None)
            if best and best[1]:
                quote.airline = best[1]
        except Exception:
            pass  # companhia é best-effort; preço é o dado crítico
    quote.raw_sample = {
        "min_per_passenger_brl": floor,
        "distinct_prices": prices[:10],
        "url": url,
    }
    return quote


async def scrape() -> list[FlightQuote]:
    """Consulta todas as origens com rate limiting (6.16) e contexto único (6.18)."""
    quotes: list[FlightQuote] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",  # Chrome real do sistema (não o embutido)
            headless=False,  #headed: baseline validado nas POCs
            args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="pt-BR",
            timezone_id="America/Sao_Paulo")
        page = await context.new_page()

        for i, origin in enumerate(settings.origins):
            if i:
                await asyncio.sleep(random.uniform(5, 10))
            try:
                quotes.append(await _search_origin(page, origin.strip()))
            except Exception as exc:
                import traceback
                tb = traceback.format_exc()[:1500]
                log.error("[%s] exceção: %s | traceback: %s",
                          origin, str(exc)[:200], tb[:600])
                quotes.append(FlightQuote(
                    source="google", origin=origin.strip(),
                    destination=settings.destination,
                    departure_date=settings.departure_date,
                    return_date=settings.return_date,
                    status=Status.UNKNOWN_ERROR,
                    passengers=settings.adults,
                    raw_sample={"error": str(exc)[:300],
                                "traceback": tb}))
        await context.close()
        await browser.close()
    return quotes
