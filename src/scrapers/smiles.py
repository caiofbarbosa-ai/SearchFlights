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

# JS do fluxo de combo (hoisted do _capture_money_combo p/ re-click no
# endurecimento §6.4 da change add-smiles-money-combo; \\d escapado evita
# SyntaxWarning de escape inválido no Python)
_JS_CLIQUE_MENOR_TARIFA = """() => {
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
            /(\\d{1,3}(?:\\.\\d{3})+)\\s*milhas/g)]
            .map(m => parseInt(m[1].replace(/\\./g, '')))
            .filter(v => v >= 1000);
        if (ms.length && Math.min(...ms) < bestMiles) {
            bestMiles = Math.min(...ms);
            best = card;
        }
    }
    if (!best) return null;
    const btn = [...best.querySelectorAll('button, [role=button]')]
        .find(b => (b.innerText || '').trim() === 'Selecionar tarifa');
    if (!btn) return null;
    btn.click();
    return bestMiles;
}"""

_JS_SCROLL_PAINEL = """() => {
    const els = [...document.querySelectorAll('div, section')]
        .filter(e => e.offsetParent &&
            (e.innerText || '').includes('Pague com Smiles & Money'))
        .sort((a, b) => (a.innerText || '').length -
                         (b.innerText || '').length);
    if (!els.length) return false;
    els[0].scrollIntoView({behavior: 'smooth', block: 'center'});
    return true;
}"""

_JS_COMBINAR_CLIENTES = """() => {
    const vis = e => {
        const r = e.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
    };
    // Parte dos botões "Combinar" e confirma pela ancestralidade que é o da
    // caixa de CLIENTES (NÃO o de Clube Smiles). Buscar a caixa pelo menor
    // elemento com o texto achava só o <título>, sem o botão dentro —
    // falha 10/09: "botão Combinar não clicável" com o botão desenhado.
    const btns = [...document.querySelectorAll('button, [role=button], a')]
        .filter(b => vis(b) &&
            (b.innerText || '').trim().toLowerCase() === 'combinar');
    for (const btn of btns) {
        let el = btn.parentElement;
        for (let i = 0; i < 8 && el; i++) {
            const t = el.innerText || '';
            if (t.includes('Combinações para clientes Smiles')) {
                btn.click();
                return true;
            }
            if (t.includes('Clube Smiles')) break;
            el = el.parentElement;
        }
    }
    return false;
}"""


def epoch_ms_brt(d: date) -> int:
    """Meia-noite BRT (UTC-3) em epoch ms — formato aceito pelo Smiles."""
    tz = timezone(timedelta(hours=-3))
    return int(datetime(d.year, d.month, d.day, tzinfo=tz).timestamp() * 1000)


def build_url(origin: str, departure_date: date | None = None,
              return_date: date | None = None,
              adults: int | None = None) -> str:
    """Overrides opcionais p/ probes e busca-controle (change smiles-1-adulto);
    sem overrides usa a config de produção (1 passageiro — ver smiles_adults)."""
    from urllib.parse import urlencode
    dep = departure_date or settings.departure_date
    ret = return_date or settings.return_date
    pax = settings.smiles_adults if adults is None else adults
    params = {
        "adults": pax, "cabin": "ALL", "children": 0,
        "departureDate": epoch_ms_brt(dep), "infants": 0,
        "isElegible": "false", "isFlexibleDateChecked": "false",
        "returnDate": epoch_ms_brt(ret),
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

    Desde 10/09 (decisão com o usuário): os valores vêm da RESPOSTA da API
    pricesm (fareType=SMILES_MONEY), disparada ao clicar "Combinar" — a
    fareList traz as âncoras exatas que o slider exibe (validado no dia:
    slider parado em 159.000 mostrou +R$3.220 = offer 5 do JSON; o trilho
    só snappa nelas). Nenhuma manipulação de slider.

    GARANTIA de não impacto (Decisão 5 da change add-smiles-money-combo):
    - NUNCA propaga exceção: toda etapa tem timeout próprio e retorna None
      em falha, com log + evidência
    - NÃO confirma compra (Escape fecha o quadro)
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
        clicked = await safe_evaluate(_JS_CLIQUE_MENOR_TARIFA)
        if not clicked:
            log("card do piso não localizado — combo indisponível")
            return None
        floor_miles = clicked

        # 2. caixa "Combinações para clientes Smiles": aguarda MONTAR até 90s
        #    com recuperação automática (endurecimento §6.4 da change
        #    add-smiles-money-combo): scrollIntoView assiste a montagem
        #    preguiçosa (C5) e re-click recupera painel derrubado por
        #    re-render (C3). Evidência obrigatória na falha.
        box_montou = False
        painel_visto = False
        recliques = 0
        prazo = asyncio.get_event_loop().time() + 90
        while asyncio.get_event_loop().time() < prazo:
            await asyncio.sleep(2)
            body = await safe_evaluate(
                "() => document.body ? document.body.innerText : ''") or ""
            low = body.lower()
            if "combinações para clientes smiles" in low:
                box_montou = True
                break
            if "use milhas" in low:
                if not painel_visto:
                    painel_visto = True
                    log("painel aberto — rolando para o viewport")
                await safe_evaluate(_JS_SCROLL_PAINEL)
            elif painel_visto and recliques < 1:
                recliques += 1
                log("painel colapsou após abrir (re-render?) — re-clicando")
                await safe_evaluate(_JS_CLIQUE_MENOR_TARIFA)
                await asyncio.sleep(2)
        if not box_montou:
            log(f"combo: caixa 'clientes Smiles' não montou em 90s "
                f"(painel_visto={painel_visto}, re-cliques={recliques})")
            try:
                await page.screenshot(
                    path=str(REPORTS / "smiles_combo_nao_montou.png"),
                    full_page=True)
                dump = await safe_evaluate(
                    "() => document.body ? document.body.innerText : ''") or ""
                (REPORTS / "smiles_combo_nao_montou.txt").write_text(
                    dump, encoding="utf-8")
            except Exception:
                pass
            return None

        # 3. "Combinar" da caixa de CLIENTES (inferior direita; NÃO a de Clube)
        clicked_combinar = False
        for frame in page.frames:
            try:
                clicked_combinar = await frame.evaluate(_JS_COMBINAR_CLIENTES)
                if clicked_combinar:
                    log("Combinar clicado (caixa de clientes)")
                    break
            except Exception:
                continue
        if not clicked_combinar:
            log("combo: caixa montada mas botão Combinar não clicável")
            try:
                await page.screenshot(
                    path=str(REPORTS / "smiles_combo_sem_combinar.png"),
                    full_page=True)
            except Exception:
                pass
            return None

        # 4. captura a RESPOSTA pricesm que o próprio clique dispara — os
        #    valores vêm prontos no JSON (fareList), sem tocar no slider
        fares_fut = asyncio.get_event_loop().create_future()

        def _on_pricesm(resp):
            if "pricesm" not in resp.url.lower() or fares_fut.done():
                return

            async def _fill():
                try:
                    body = json.loads(await resp.text())
                    fares = [f for f in body.get("fareList", [])
                             if f.get("type") == "SMILES_MONEY"
                             and f.get("miles")
                             and f.get("money") is not None]
                    if fares and not fares_fut.done():
                        fares_fut.set_result(fares)
                except Exception:
                    pass

            asyncio.ensure_future(_fill())

        page.on("response", _on_pricesm)
        try:
            fares = await asyncio.wait_for(fares_fut, timeout=30)
        except Exception:
            fares = None
        finally:
            try:
                page.remove_listener("response", _on_pricesm)
            except Exception:
                pass

        # 5. fecha SEM confirmar (apenas leitura de valores — task 2.7)
        try:
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
        except Exception:
            pass

        if not fares:
            log("combo: resposta pricesm não capturada")
            try:
                await page.screenshot(
                    path=str(REPORTS / "smiles_combo_sem_pricesm.png"),
                    full_page=True)
            except Exception:
                pass
            return None

        # 6. maior combo de milhas ABAIXO do limite configurado
        validos = sorted((int(f["miles"]), float(f["money"]))
                         for f in fares if int(f["miles"]) < limit)
        if not validos:
            log(f"combo: fareList sem combo < {limit:,} milhas — "
                f"âncoras: {[f['miles'] for f in fares]}".replace(",", "."))
            return None
        milhas, reais = validos[-1]

        log(f"combo capturado (pricesm): {milhas:,} milhas + "
            f"R$ {reais}".replace(",", "."))
        return (milhas, reais)
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
        return_date=settings.return_date,
        passengers=settings.smiles_adults,
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
        # spinner eterno é AMBÍGUO — discriminante por busca-controle
        # (change smiles-1-adulto; os rótulos errados de 04-09/09 custaram
        # 4+ dias de diagnóstico)
        quote.status = await _classify_with_control(page, origin, quote)
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


# busca-controle do discriminante: datas rolling (hoje+90/97d) para ficar
# dentro da janela de reservas independentemente da data atual
_CONTROL_DEP_OFFSET = 90
_CONTROL_RET_OFFSET = 97


async def _classify_with_control(page, origin: str, quote: FlightQuote) -> str:
    """Spinner eterno tem 2 causas possíveis: falha específica do alvo OU
    sessão comprometida. A busca-controle (datas dentro da janela, 1
    passageiro, mesma sessão) decide:
    - controle abre/responde → sessão sã; falha é do alvo → CALENDAR_NOT_OPEN
      (partida >300 dias) ou TIMEOUT
    - controle também não abre → sessão comprometida → BLOCKED
    Só roda no caminho de falha; happy path não adiciona chamadas."""
    dep = date.today() + timedelta(days=_CONTROL_DEP_OFFSET)
    ret = date.today() + timedelta(days=_CONTROL_RET_OFFSET)
    print(f"    [discriminante] {origin}: alvo não renderizou — "
          f"busca-controle {dep}→{ret} na mesma sessão...", flush=True)
    try:
        await page.goto(build_url(origin, departure_date=dep,
                                  return_date=ret), timeout=90_000)
        for _ in range(_wait_timeout_s() // 3):
            await asyncio.sleep(3)
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''")
            low = body.lower()
            if "aguarde" in low:
                continue  # controle ainda carregando
            cards = await page.evaluate(CARDS_JS) or []
            respondeu = bool(cards) or any(m in low
                                           for m in NO_RESULTS_MARKERS)
            quote.raw_sample["controle"] = {
                "datas": f"{dep}→{ret}", "renderizou": bool(cards),
                "n_cartoes": len(cards)}
            if respondeu:
                return (Status.CALENDAR_NOT_OPEN
                        if settings.departure_date
                        > date.today() + timedelta(days=300)
                        else Status.TIMEOUT)
            # sem spinner, sem cards, sem mensagem: shell vazio = soft-block
            return Status.BLOCKED
        quote.raw_sample["controle"] = {"datas": f"{dep}→{ret}",
                                        "renderizou": False}
        return Status.BLOCKED
    except Exception as exc:
        quote.raw_sample["controle"] = {"erro": str(exc)[:200]}
        return Status.BLOCKED


async def scrape() -> list[FlightQuote]:
    """Origens sequenciais com spacing (rate-limit Akamai: 1 busca/origem/dia)."""
    quotes: list[FlightQuote] = []
    # driver "playwright" (vanilla): patchright NUNCA renderizou neste site
    # (0 sucessos desde 68ac0e9; matriz 09/09 no findings §RESOLUÇÃO).
    # Validação de driver é POR SITE — Google mantém patchright, Azul usa
    # este default.
    async with RealChrome(port=9301, driver="playwright") as chrome:
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
                    passengers=settings.smiles_adults,
                    status=Status.UNKNOWN_ERROR,
                    raw_sample={"error": str(exc)[:300]})
            quotes.append(quote)
    return quotes
