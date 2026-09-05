"""Smiles scraper (Fase 7) — arquitetura validada na POC 2026-09-02:
Chrome real + CDP (Akamai nega Playwright embutido); URL direta
`/mfe/emissao-passagem/?...` (epoch ms meia-noite BRT); extração por
"milhas por passageiro"; rate-limit: 1 busca/origem/dia."""

import asyncio
import json
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

# cartões de voo: ancorados no botão "Mais detalhes" de cada card, subindo
# até o ancestral que contém a rota (GRU) — isola a faixa de datas
CARDS_JS = """() => {
    const btns = [...document.querySelectorAll('button')]
        .filter(b => b.offsetParent &&
            (b.innerText || '').trim() === 'Mais detalhes');
    const texts = [];
    const seen = [];
    for (const b of btns) {
        let el = b;
        for (let i = 0; i < 8 && el; i++) {
            el = el.parentElement;
            if (!el) break;
            const t = el.innerText || '';
            if (t.includes('milhas') && t.includes('GRU')) {
                if (!seen.some(s => t.includes(s))) {
                    seen.push(t);
                    texts.push(t);
                }
                break;
            }
        }
    }
    return texts;
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


async def _capture_money_combo(page):
    """Fluxo APARTADO do combo Smiles & Money (enriquecimento isolado).

    GARANTIA de não impacto (Decisão 5 da change add-smiles-money-combo):
    - NUNCA propaga exceção: toda etapa tem timeout próprio e retorna None
      em falha, com log + evidência
    - NÃO clica em "Confirmar" (apenas lê os valores do quadro)
    - Alvo: maior combinação de milhas abaixo do limite configurado

    Retorna (milhas, reais) ou None.
    """
    limit = settings.smiles_combo_max_miles

    def log(m):
        print(f"    [combo] {m}", flush=True)

    async def safe_evaluate(js, arg=None):
        try:
            return await page.evaluate(js, arg) if arg is not None \
                else await page.evaluate(js)
        except Exception:
            return None

    try:
        # 1. cards dedupados → o de MENOR milhas → "Selecionar tarifa" nele
        clicked = await safe_evaluate("""() => {
            const els = [...document.querySelectorAll('li, div')].filter(e =>
                e.offsetParent && e.innerText &&
                e.innerText.includes('milhas') &&
                e.innerText.includes('Mais detalhes'));
            els.sort((a, b) => a.innerText.length - b.innerText.length);
            const cards = [];
            for (const e of els) {
                if (!cards.some(c => e.innerText.includes(c.innerText)))
                    cards.push(e);
            }
            let best = null, bestMiles = Infinity;
            for (const card of cards) {
                const ms = [...card.innerText.matchAll(
                    /(\d{1,3}(?:\.\d{3})+)\s*milhas/g)]
                    .map(m => parseInt(m[1].replace(/\./g, '')))
                    .filter(v => v >= 1000);
                if (ms.length && Math.min(...ms) < bestMiles) {
                    bestMiles = Math.min(...ms);
                    best = card;
                }
            }
            if (!best) return null;
            const btn = [...best.querySelectorAll('button, [role=button]')]
                .find(b => (b.innerText || '').trim()
                    === 'Selecionar tarifa');
            if (!btn) return null;
            btn.click();
            return bestMiles;
        }""")
        if not clicked:
            log("card do piso não localizado — combo indisponível")
            return None
        floor_miles = clicked

        # 2. aguarda o quadro "Pague com Smiles & Money" (15s)
        opened = False
        for _ in range(15):
            await asyncio.sleep(1)
            body = await safe_evaluate(
                "() => document.body ? document.body.innerText : ''") or ""
            if "Pague com Smiles & Money" in body or "Use milhas" in body:
                opened = True
                break
        if not opened:
            log("quadro de tarifas não abriu — combo indisponível")
            return None

        # 3. "Combinar" da caixa de CLIENTES (inferior direita; NÃO a de Clube)
        clicked_combinar = False
        for tent in range(15):  # retry 30s: o painel carrega o conteúdo async
            for frame in page.frames:
                try:
                    clicked_combinar = await frame.evaluate("""() => {
                        const vis = e => {
                            const r = e.getBoundingClientRect();
                            return r.width > 0 && r.height > 0;
                        };
                        const boxes = [...document.querySelectorAll(
                            'div, section')]
                            .filter(e => vis(e) && (e.innerText || '')
                                .includes('Combinações para clientes Smiles'))
                            .sort((a, b) => (a.innerText || '').length -
                                             (b.innerText || '').length);
                        const box = boxes[0];
                        if (!box) return false;
                        const btn = [...box.querySelectorAll('button')]
                            .find(b => (b.innerText || '').trim()
                                .toLowerCase() === 'combinar');
                        if (btn) { btn.click(); return true; }
                        return false;
                    }""")
                    if clicked_combinar:
                        log(f"Combinar clicado (frame, tentativa {tent+1})")
                        break
                except Exception:
                    continue
            if clicked_combinar:
                break
            await asyncio.sleep(2)
        if not clicked_combinar:
            # diagnóstico: o que existe com "Combina"/"Smiles &" em cada frame
            diag = []
            for frame in page.frames:
                try:
                    t = await frame.evaluate("""() => {
                        const vis = e => {
                            const r = e.getBoundingClientRect();
                            return r.width > 0 && r.height > 0;
                        };
                        return [...document.querySelectorAll('div')]
                            .filter(e => vis(e) && ((e.innerText || '')
                                .includes('Combina') ||
                                (e.innerText || '').includes('Smiles &')))
                            .map(e => (e.innerText || '')
                                .slice(0, 80).replace(/\\n/g, ' | '));
                    }""")
                    if t:
                        diag.append({"frame": frame.url[:100], "itens": t[:10]})
                except Exception:
                    continue
            log(f"combo: caixa 'clientes Smiles' não encontrada. "
                f"diag: {json.dumps(diag, ensure_ascii=False)[:600]}")
            return None
        if not clicked_combinar:
            log("combo: caixa 'clientes Smiles' não encontrada")
            return None

        # 4. aguarda o quadro do slider (milhas + R$ juntos)
        async def read_box():
            return await safe_evaluate("""() => {
                const s = [...document.querySelectorAll('[role=slider]')]
                    .filter(e => e.offsetParent);
                if (!s.length) return '';
                let el = s[0];
                for (let i = 0; i < 6 && el.parentElement; i++) {
                    el = el.parentElement;
                    const t = el.innerText || '';
                    if (t.includes('milhas') && t.includes('R$')) return t;
                }
                return '';
            }""") or ""

        async def miles_of(text):
            vals = [int(m.replace(".", "")) for m in
                    re.findall(r"(\d{1,3}(?:\.\d{3})+)\s*milhas", text,
                               re.IGNORECASE)
                    if int(m.replace(".", "")) >= 1000]
            return min(vals) if vals else None

        async def reais_of(text):
            m = re.search(r"\+\s*R\$\s?([\d.,]+)", text)
            if not m:
                return None
            return float(m.group(1).replace(".", "").replace(",", "."))

        box = await read_box()
        cur = await miles_of(box) if box else None
        log(f"slider inicial: {cur} milhas")

        # 5. desce (ArrowLeft) até ficar ABAIXO do limite — o 1º valor abaixo
        #    do limite é automaticamente o MAIOR valor válido
        guard = 0
        while cur is not None and cur >= limit and guard < 60:
            await page.keyboard.press("ArrowLeft")
            await asyncio.sleep(0.5)
            box = await read_box()
            cur = await miles_of(box) if box else None
            guard += 1
        if cur is None or cur >= limit:
            log("combo: nenhum valor abaixo do limite no slider")
            return None

        # 6. maximiza: sobe (ArrowRight) enquanto permanecer < limite;
        #    se estourar, volta um passo
        while guard < 80:
            await page.keyboard.press("ArrowRight")
            await asyncio.sleep(0.5)
            box = await read_box()
            new = await miles_of(box) if box else None
            if new is None or new >= limit:
                await page.keyboard.press("ArrowLeft")
                await asyncio.sleep(0.5)
                box = await read_box()
                cur = await miles_of(box) if box else cur
                break
            cur = new
            guard += 1

        box = await read_box()
        reais = await reais_of(box) if box else None
        if reais is None:
            m = re.search(r"\+\s*R\$\s?([\d.,]+)", box or "")
            reais = float(m.group(1).replace(".", "").replace(",", ".")) \
                if m else None

        # 7. fecha SEM confirmar (apenas leitura de valores)
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)

        log(f"combo capturado: {cur:,} milhas + R$ {reais}".replace(",", ".")
            if reais else f"combo capturado: {cur:,} milhas")
        return (cur, reais)
    except Exception as exc:
        log(f"combo falhou (exceção contida): {str(exc)[:150]}")
        try:
            await page.screenshot(
                path=str(REPORTS / f"smiles_combo_erro.png"), full_page=True)
        except Exception:
            pass
        return None


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

        # combo Smiles & Money: função APARTADA (enriquecimento isolado —
        # falha aqui NUNCA invalida o só-milhas; Decisão 5 da change)
        if settings.smiles_combo_enabled:
            try:
                combo = await _capture_money_combo(page)
                if combo:
                    quote.hybrid_miles = combo[0]
                    quote.cash_component_brl = combo[1]
                    quote.raw_sample["combo"] = {"miles": combo[0],
                                                 "brl": combo[1]}
            except Exception as exc:
                print(f"    [WARN] {origin}: combo falhou (ignorado): "
                      f"{str(exc)[:120]}")
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
    async with RealChrome(port=9301, driver="patchright") as chrome:
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
