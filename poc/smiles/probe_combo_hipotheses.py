"""Probe diagnóstico do combo (change add-smiles-money-combo, tasks 6.1-6.3):
por que "Combinações para clientes Smiles" não montou em 30s na automação
(seu browser: imediato) — C3 re-render derruba o painel × C5 lazy-mount que
exige scroll/viewport × C1 montagem lenta.

Fases (design capturado em tasks.md §6):
  A (0-30s)  observação PASSIVA — reproduz a produção
  B          "Use milhas" sumiu  → re-click           (testa C3)
             painel aberto       → scrollIntoView      (testa C5)
  C (+60s)   observação pós-ação
Bônus: se a caixa montar, executa o fluxo completo de produção
(Combinar → ler slider → Escape) e captura os valores.

Rodar da raiz:  python poc/smiles/probe_combo_hipotheses.py
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, ".")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from src.scrapers.chrome_cdp import RealChrome
from src.scrapers.smiles import MILES_RE, build_url

REPORTS = Path("poc/reports").resolve()
OUT_JSON = REPORTS / "combo_hipotheses.json"

CLICK_MENOR_TARIFA = """() => {
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

SCROLL_PAINEL = """() => {
    const els = [...document.querySelectorAll('div, section')]
        .filter(e => e.offsetParent &&
            (e.innerText || '').includes('Pague com Smiles & Money'))
        .sort((a, b) => (a.innerText || '').length -
                         (b.innerText || '').length);
    if (!els.length) return false;
    els[0].scrollIntoView({behavior: 'smooth', block: 'center'});
    return true;
}"""


def log(m):
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


async def shot(page, name, artifacts):
    p = REPORTS / f"combo_hyp_{name}.png"
    try:
        await page.screenshot(path=str(p), full_page=False)  # viewport
        artifacts.append(p.name)
    except Exception:
        pass


async def dismiss_cookies(page):
    for _ in range(8):
        clicked = False
        for text in ("Rejeitar todos", "Rejeitar Tudo",
                     "Aceitar todos Cookies", "Outro dia", "Reject All",
                     "Accept All Cookies"):
            try:
                btn = page.locator(f"button:has-text('{text}')").first
                if await btn.is_visible(timeout=600):
                    await btn.click()
                    clicked = True
                    await asyncio.sleep(0.4)
            except Exception:
                continue
        if not clicked:
            break
        await asyncio.sleep(1)


async def state(page):
    """(use_milhas, box_clientes, aguarde) do frame principal."""
    try:
        body = await page.evaluate(
            "() => document.body ? document.body.innerText : ''") or ""
    except Exception:
        return None, None, None
    low = body.lower()
    return ("use milhas" in low,
            "combinações para clientes smiles" in low,
            "aguarde" in low)


async def wait_render(page):
    for _ in range(60):
        await asyncio.sleep(3)
        um, box, aguarde = await state(page)
        if um is None:
            continue
        miles_ok = False
        try:
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''") or ""
            miles_ok = bool([m for m in MILES_RE.findall(body)
                             if int(m.replace(".", "")) >= 1000])
        except Exception:
            pass
        if miles_ok and not aguarde:
            return True
    return False


async def read_slider(page):
    """Fluxo de produção a partir da caixa montada: Combinar → ler slider."""
    clicked = False
    for frame in page.frames:
        try:
            clicked = await frame.evaluate("""() => {
                const vis = e => {
                    const r = e.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                };
                const btns = [...document.querySelectorAll(
                    'button, [role=button], a')]
                    .filter(b => vis(b) &&
                        (b.innerText || '').trim().toLowerCase()
                            === 'combinar');
                for (const btn of btns) {
                    let el = btn.parentElement;
                    for (let i = 0; i < 8 && el; i++) {
                        const t = el.innerText || '';
                        if (t.includes(
                                'Combinações para clientes Smiles')) {
                            btn.click();
                            return true;
                        }
                        if (t.includes('Clube Smiles')) break;
                        el = el.parentElement;
                    }
                }
                return false;
            }""")
            if clicked:
                break
        except Exception:
            continue
    if not clicked:
        return None, "botão Combinar não encontrado"
    for _ in range(15):
        await asyncio.sleep(2)
        try:
            txt = await page.evaluate("""() => {
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
        except Exception:
            continue
        if txt:
            return txt.replace("\n", " | ")[:300], None
    return None, "slider não apareceu após Combinar"


async def main():
    net = []
    timeline = []
    artifacts = []

    async def on_response(resp):
        u = resp.url.lower()
        if any(k in u for k in ("price", "offer", "combo", "money",
                                "award", "fare", "avail", "search")):
            try:
                size = len(await resp.text())
            except Exception:
                size = -1
            net.append({"t": datetime.now().strftime("%H:%M:%S"),
                        "status": resp.status, "size": size,
                        "url": resp.url[:160]})

    async def on_reqfailed(req):
        u = req.url.lower()
        if any(k in u for k in ("price", "offer", "combo", "money",
                                "award", "fare", "avail", "search")):
            net.append({"t": datetime.now().strftime("%H:%M:%S"),
                        "status": "FAILED", "size": None,
                        "url": req.url[:160]})

    async with RealChrome(port=9306, driver="playwright") as chrome:
        page = await chrome.page()
        page.on("response", on_response)
        page.on("requestfailed", on_reqfailed)

        log("abrindo busca (config de produção: jul/27, GRU, 1 adulto)...")
        await page.goto(build_url("GRU"), timeout=90_000)
        await dismiss_cookies(page)
        if not await wait_render(page):
            log("página não renderizou em 180s — evidência + saída")
            await shot(page,"00_nao_renderizou", artifacts)
            try:
                dump = await page.evaluate(
                    "() => document.body ? document.body.innerText : ''") or ""
                (REPORTS / "combo_hyp_nao_renderizou.txt").write_text(
                    dump, encoding="utf-8")
                artifacts.append("combo_hyp_nao_renderizou.txt")
            except Exception:
                pass
            OUT_JSON.write_text(json.dumps(
                {"generated_at": datetime.now().isoformat(timespec="seconds"),
                 "outcome": "NO_RENDER", "network": net,
                 "artifacts": artifacts}, ensure_ascii=False, indent=1),
                encoding="utf-8")
            return
        log("página renderizada — estado 'settling' reproduzido "
            "(combo começa ~24s após o render, como na produção)")
        await shot(page,"01_render", artifacts)

        floor = await page.evaluate(CLICK_MENOR_TARIFA)
        log(f"clicado 'Selecionar tarifa' no card de menor milhas: {floor}")
        await asyncio.sleep(2)
        await shot(page,"02_pos_clique", artifacts)

        # FASE A (0-30s): observação passiva
        outcome = None
        use_milhas_visto = False
        colapso_em = None
        box_em = None
        t0 = asyncio.get_event_loop().time()
        for i in range(15):
            await asyncio.sleep(2)
            um, box, _ = await state(page)
            el = round(asyncio.get_event_loop().time() - t0)
            if um:
                use_milhas_visto = True
            if box:
                box_em = el
                log(f"  A[{el}s] CAIXA MONTOU")
                break
            if use_milhas_visto and not um:
                colapso_em = el
                log(f"  A[{el}s] painel COLAPOU (Use milhas sumiu)")
                break
            if i % 5 == 0:
                log(f"  A[{el}s] use_milhas={um} box={box}")
            timeline.append({"fase": "A", "t": el, "use_milhas": um,
                             "box_clientes": box})
        await shot(page,"03_fim_faseA", artifacts)

        if box_em is not None:
            outcome = ("C1_SLOW_MOUNT" if box_em > 10
                       else "MONTOU_NA_FASE_A")
        elif colapso_em is not None:
            # FASE B1: re-click (testa C3)
            log(f"  B: re-clicando 'Selecionar tarifa' (painel colapsou "
                f"em {colapso_em}s)...")
            await page.evaluate(CLICK_MENOR_TARIFA)
            await shot(page,"04_pos_reclique", artifacts)
            for i in range(15):
                await asyncio.sleep(2)
                um, box, _ = await state(page)
                el = round(asyncio.get_event_loop().time() - t0)
                timeline.append({"fase": "B-reclick", "t": el,
                                 "use_milhas": um, "box_clientes": box})
                if box:
                    box_em = el
                    break
            if box_em is not None:
                outcome = "C3_RE_RENDER_COLAPSE"
        else:
            # FASE B2: scrollIntoView (testa C5)
            log("  B: painel aberto sem caixa — scrollIntoView do painel...")
            await page.evaluate(SCROLL_PAINEL)
            await shot(page,"04_pos_scroll", artifacts)
            for i in range(30):
                await asyncio.sleep(2)
                um, box, _ = await state(page)
                el = round(asyncio.get_event_loop().time() - t0)
                timeline.append({"fase": "B-scroll", "t": el,
                                 "use_milhas": um, "box_clientes": box})
                if box:
                    box_em = el
                    break
                if i % 5 == 0:
                    log(f"  B[{el}s] use_milhas={um} box={box}")
            if box_em is not None:
                outcome = "C5_LAZY_VIEWPORT"

        if box_em is None:
            outcome = outcome or "UNKNOWN"
        log(f"DESFecho: {outcome} (caixa montou em t={box_em}s)")

        # BÔNUS: fluxo completo de produção a partir da caixa montada
        slider_txt = None
        slider_erro = None
        if box_em is not None:
            await shot(page,"05_box_montada", artifacts)
            slider_txt, slider_erro = await read_slider(page)
            if slider_txt:
                log(f"slider capturado: {slider_txt[:120]}")
                await shot(page,"06_slider", artifacts)
            else:
                log(f"slider falhou: {slider_erro}")
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass

    doc = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "outcome": outcome,
        "box_montou_em_s": box_em,
        "colapso_em_s": colapso_em,
        "slider": slider_txt or None,
        "slider_erro": slider_erro,
        "timeline": timeline,
        "network": net,
        "artifacts": artifacts,
    }
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    log(f"JSON: {OUT_JSON}")


if __name__ == "__main__":
    asyncio.run(main())
