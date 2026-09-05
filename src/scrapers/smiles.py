"""Smiles scraper (Fase 7) — arquitetura validada na POC 2026-09-02:
Chrome real + CDP (Akamai nega Playwright embutido); URL direta
`/mfe/emissao-passagem/?...` (epoch ms meia-noite BRT); extração por
"milhas por passageiro"; rate-limit: 1 busca/origem/dia."""

import asyncio
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.config import settings
from src.models import FlightQuote, Status
from src.scrapers.chrome_cdp import RealChrome

REPORTS = Path(__file__).resolve().parents[2] / "poc" / "reports"

MILES_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+)\s*milhas", re.IGNORECASE)
# ATENÇÃO: o texto renderizado é "milhas por VIAGANTE" (não "por passageiro")
# — exigir o literal antigo fazia a extração nunca casar (bug 04/09)

# cartões de voo: contêm "milhas" + botão "Mais detalhes" (isola o cartão
# da faixa de datas e do cabeçalho)
CARDS_JS = """() => {
    const els = [...document.querySelectorAll('li, div')].filter(e =>
        e.offsetParent && e.innerText && e.innerText.includes('milhas')
        && e.innerText.includes('Mais detalhes'));
    return els.sort((a, b) => a.innerText.length - b.innerText.length)
        .slice(0, 40).map(e => e.innerText);
}"""
CARD_JS = """() => {
    const els = [...document.querySelectorAll('*')].filter(e =>
        e.children.length === 0 &&
        /milhas por passageiro/.test(e.innerText || ''));
    const cards = els.map(el => {
        let c = el;
        for (let i = 0; i < 4 && c.parentElement; i++) c = c.parentElement;
        return (c.innerText || '').replace(/\\s*\\n+\\s*/g, ' | ').slice(0, 300);
    });
    return [...new Set(cards)];
}"""
NO_RESULTS_MARKERS = ["não encontramos", "nao encontramos", "nenhum voo",
                      "não há voos", "nao ha voos", "infelizmente", "esgot"]


def epoch_ms_brt(d: date) -> int:
    """Meia-noite BRT (UTC-3) em epoch ms — formato aceito pelo Smiles."""
    tz = timezone(timedelta(hours=-3))
    return int(datetime(d.year, d.month, d.day, tzinfo=tz).timestamp() * 1000)


def build_url(origin: str) -> str:
    from urllib.parse import urlencode
    params = {
        "adults": settings.adults, "cabin": "ALL", "children": 0,
        "departureDate": epoch_ms_brt(settings.departure_date), "infants": 0,
        "isElegible": "false", "isFlexibleDateChecked": "false",
        "returnDate": epoch_ms_brt(settings.return_date),
        "searchType": "congenere", "segments": 1, "tripType": 1,
        "originAirport": origin, "originCity": "", "originCountry": "",
        "originAirportIsAny": "false",
        "destinationAirport": settings.destination, "destinCity": "",
        "destinCountry": "", "destinAirportIsAny": "false",
        "novo-resultado-voos": "true",
    }
    return ("https://www.smiles.com.br/mfe/emissao-passagem/?"
            + urlencode(params))


def _wait_timeout_s() -> int:
    return 180  # resultados demoram ~45-60s; margem p/ 2 adultos


async def _search_origin(page, origin: str) -> FlightQuote:
    quote = FlightQuote(
        source="smiles", origin=origin, destination=settings.destination,
        departure_date=settings.departure_date,
        return_date=settings.return_date, passengers=settings.adults,
        status=Status.UNKNOWN_ERROR)

    await page.goto(build_url(origin), timeout=90_000)
    for text in ("Rejeitar todos", "Rejeitar Tudo", "Aceitar todos Cookies",
                 "Outro dia", "Reject All", "Accept All Cookies"):
        try:
            btn = page.locator(f"button:has-text('{text}')").first
            if await btn.is_visible(timeout=800):
                await btn.click()
                await asyncio.sleep(0.5)
        except Exception:
            continue

    # SPA: aguarda um estado CONHECIDO (shell/spinner/resultados); reload 1x
    known = False
    known_markers = ("alterar busca", "escolha sua passagem", "aguarde",
                     "milhas por passageiro", "nenhum voo", "não há voos")
    for attempt in range(2):
        for _ in range(15):  # 45s
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            low = body.lower()
            if any(m in low for m in known_markers):
                known = True
                break
            await asyncio.sleep(3)
        if known:
            break
        if attempt == 0:
            if not body.strip():
                print(f"    [WARN] {origin}: página vazia, goto completo...")
                await page.goto(build_url(origin), timeout=90_000)
            else:
                print(f"    [WARN] {origin}: estado desconhecido, reload...")
                await page.reload(timeout=90_000)
            await asyncio.sleep(4)
            for text in ("Rejeitar Tudo", "Aceitar todos Cookies"):
                try:
                    btn = page.locator(f"button:has-text('{text}')").first
                    if await btn.is_visible(timeout=600):
                        await btn.click()
                        await asyncio.sleep(0.4)
                except Exception:
                    continue

    body = ""
    resolved = False
    for _ in range(_wait_timeout_s() // 3):
        await asyncio.sleep(3)
        try:
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
        except Exception:
            continue  # navegação em curso
        low = body.lower()
        if "milhas" in low and "aguarde" not in low:
            resolved = True  # valores em milhas renderizaram (qualquer formato)
            break
        if any(m in low for m in NO_RESULTS_MARKERS) \
                and "aguarde" not in low:
            resolved = True
            break

    lower = body.lower()

    # extrai CARTÕES (dedup por contenção) e escolhe o de menor milhas;
    # companhia aérea vem do próprio cartão
    best = None  # (milhas, airline, card_text)
    try:
        texts = await page.evaluate(CARDS_JS) or []
        texts.sort(key=len)
        cards: list[str] = []
        for t in texts:
            if not any(t in acc for acc in cards):
                cards.append(t)
        for card in cards[:25]:
            ms = [int(x.replace(".", "")) for x in
                  MILES_RE.findall(card) if int(x.replace(".", "")) >= 1000]
            if not ms:
                continue
            names: list[str] = []
            seen_names: set[str] = set()
            for m in re.finditer(
                    r"(Qatar Airways|Malaysia Airlines|LATAM|Emirates|"
                    r"Etihad Airways|Etihad|Turkish Airlines|SWISS|KLM|"
                    r"Air France|Lufthansa|Ethiopian|Japan Airlines|"
                    r"American Airlines|United Airlines|United|Delta|"
                    r"ITA Airways|Air Canada|Korean Air|Air Europa|"
                    r"Iberia|British Airways)", card, re.IGNORECASE):
                key = m.group(1).lower()
                if key not in seen_names:
                    seen_names.add(key)
                    names.append(m.group(1))
            cand = (min(ms), " & ".join(names)[:120] or None, card)
            if best is None or cand[0] < best[0]:
                best = cand
    except Exception:
        best = None

    miles = sorted({int(m.replace(".", "")) for m in MILES_RE.findall(body)
                    if int(m.replace(".", "")) >= 1000})

    if any(m in lower for m in ("unusual traffic", "acesso negado")):
        quote.status = Status.BLOCKED
    elif best is not None:
        quote.status = Status.SUCCESS
        quote.miles = best[0]  # 7.9 menor só-milhas (por viajante)
        quote.airline = best[1]
        # 7.10 híbrido sob 120k: cartões trazem "ou combine milhas e dinheiro"
        hybrids = [m for m in miles if m <= settings.hybrid_max_miles]
        if hybrids:
            quote.hybrid_miles = max(hybrids)
        quote.raw_sample = {"distinct_miles": miles[:10],
                            "card": best[2][:300]}
    elif not resolved and "aguarde" in lower:
        quote.status = (Status.CALENDAR_NOT_OPEN
                        if settings.departure_date
                        > date.today() + timedelta(days=300)
                        else Status.TIMEOUT)
    elif any(m in lower for m in NO_RESULTS_MARKERS):
        quote.status = Status.NO_AVAILABILITY
    elif looks_like_results_shell(lower):
        # shell renderiza (rota no header) sem spinner e sem resultados =
        # soft-block silencioso do Akamai (rate-limit por IP; dura 10h+)
        quote.status = Status.BLOCKED
    else:
        quote.status = Status.PARSER_ERROR
        # evidência para diagnosticar estados desconhecidos
        try:
            await page.screenshot(
                path=str(REPORTS / f"smiles_erro_{origin}.png"), full_page=True)
            quote.raw_sample = {"body_head": body[:400],
                                "estado_renderizado": known}
        except Exception:
            pass
    return quote


def looks_like_results_shell(lower: str) -> bool:
    return ("alterar busca" in lower
            or "escolha sua passagem" in lower
            or "emissao-passagem" in lower)


async def scrape() -> list[FlightQuote]:
    """Origens sequenciais com spacing (rate-limit Akamai: 1 busca/origem/dia)."""
    quotes: list[FlightQuote] = []
    async with RealChrome(port=9301) as chrome:
        page = await chrome.page()
        for i, origin in enumerate(settings.origins):
            if i:
                await asyncio.sleep(settings.smiles_origin_spacing_s)
            origin = origin.strip()
            try:
                quote = await _search_origin(page, origin)
            except Exception as exc:
                quote = FlightQuote(
                    source="smiles", origin=origin,
                    destination=settings.destination,
                    departure_date=settings.departure_date,
                    return_date=settings.return_date,
                    passengers=settings.adults,
                    status=Status.UNKNOWN_ERROR,
                    raw_sample={"error": str(exc)[:300]})
            quotes.append(quote)
    return quotes
