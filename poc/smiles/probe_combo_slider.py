"""Probe focado: o que acontece DEPOIS de clicar Combinar (caixa clientes)?

Contexto (10/09 12:14, probe_combo_hipotheses 2ª execução): o clique
registrou — pricesm SMILES_MONEY 200 (532B) 1s após o clique — mas o quadro
do slider não montou em 30s e a página não mudou visualmente (screenshots
byte-idênticos). Captura agora: BODY da resposta pricesm, timeline do DOM
('do seu jeito'? [role=slider]? input[type=range]? Confirmar?), screenshots
a cada mudança e dump final do body.

Rodar da raiz:  python poc/smiles/probe_combo_slider.py
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
from src.scrapers.smiles import (
    MILES_RE,
    _JS_CLIQUE_MENOR_TARIFA,
    _JS_COMBINAR_CLIENTES,
    build_url,
)

REPORTS = Path("poc/reports").resolve()
OUT_JSON = REPORTS / "combo_slider.json"


def log(m):
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


async def shot(page, name, artifacts, full_page=False):
    p = REPORTS / f"combo_slider_{name}.png"
    try:
        await page.screenshot(path=str(p), full_page=full_page)
        artifacts.append(p.name)
    except Exception:
        pass


async def state(page):
    """Marcadores do quadro pós-Combinar + texto do quadro se houver slider."""
    try:
        return await page.evaluate("""() => {
            const body = document.body ? document.body.innerText : '';
            const low = body.toLowerCase();
            const rs = document.querySelector('[role=slider]');
            const ir = document.querySelector('input[type=range]');
            let quadro = '';
            const el = ir || rs;
            if (el) {
                let p = el;
                for (let i = 0; i < 8 && p; i++) {
                    p = p.parentElement;
                    const t = (p && p.innerText) || '';
                    if (t.includes('milhas') && t.includes('R$')) {
                        quadro = t; break;
                    }
                }
            }
            return {
                use_milhas: low.includes('use milhas'),
                box_clientes: low.includes(
                    'combinações para clientes smiles'),
                seu_jeito: low.includes('do seu jeito'),
                confirmar: low.includes('confirmar'),
                role_slider: !!rs,
                input_range: !!ir,
                quadro: quadro.replace(/\\n/g, ' | ').slice(0, 400),
            };
        }""")
    except Exception:
        return {}


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


async def wait_render(page):
    for _ in range(60):
        await asyncio.sleep(3)
        try:
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''") or ""
        except Exception:
            continue
        if "aguarde" not in body.lower() and body.lower().strip():
            if bool([m for m in MILES_RE.findall(body)
                     if int(m.replace(".", "")) >= 1000]):
                return True
    return False


async def main():
    net = []
    timeline = []
    artifacts = []

    async def on_response(resp):
        u = resp.url.lower()
        if any(k in u for k in ("pricesm", "price", "offer", "combo",
                                "money", "award")):
            body_txt = None
            try:
                body_txt = (await resp.text())[:2000]
            except Exception:
                pass
            net.append({"t": datetime.now().strftime("%H:%M:%S"),
                        "status": resp.status,
                        "url": resp.url[:160], "body": body_txt})
            if "pricesm" in u:
                log(f"pricesm {resp.status}: {(body_txt or '')[:200]}")

    async with RealChrome(port=9306, driver="playwright") as chrome:
        page = await chrome.page()
        page.on("response", on_response)

        log("abrindo busca (config de produção: jul/27, GRU, 1 adulto)...")
        await page.goto(build_url("GRU"), timeout=90_000)
        await dismiss_cookies(page)
        if not await wait_render(page):
            log("página não renderizou em 180s — saída")
            await shot(page, "00_nao_renderizou", artifacts)
            OUT_JSON.write_text(json.dumps(
                {"generated_at": datetime.now().isoformat(
                    timespec="seconds"),
                 "outcome": "NO_RENDER", "network": net,
                 "artifacts": artifacts}, ensure_ascii=False, indent=1),
                encoding="utf-8")
            return
        await shot(page, "01_render", artifacts)

        floor = await page.evaluate(_JS_CLIQUE_MENOR_TARIFA)
        log(f"clicado 'Selecionar tarifa' no card de menor milhas: {floor}")
        for _ in range(15):
            await asyncio.sleep(2)
            st = await state(page)
            if st.get("box_clientes"):
                break
        log(f"caixa clientes: {st.get('box_clientes')}")
        await shot(page, "02_box", artifacts)

        clicked = await page.evaluate(_JS_COMBINAR_CLIENTES)
        log(f"Combinar clicado: {clicked}")
        await shot(page, "03_pos_combinar", artifacts)

        prev = None
        quadro_txt = None
        for i in range(24):  # 48s
            await asyncio.sleep(2)
            st = await state(page)
            el = (i + 1) * 2
            marca = {k: v for k, v in st.items() if k != "quadro"}
            if marca != prev:
                log(f"  [{el}s] {marca}")
                prev = marca
                await shot(page, f"04_mudanca_{el}s", artifacts)
            timeline.append({"t": el, **st})
            if (st.get("role_slider") or st.get("input_range")) \
                    and st.get("quadro"):
                quadro_txt = st["quadro"]
                log(f"QUADRO DO SLIDER em t={el}s: {quadro_txt[:150]}")
                await shot(page, "05_slider", artifacts)
                break

        if quadro_txt is None:
            log("slider não montou em 48s — dump do body p/ diagnóstico")
            body = await page.evaluate(
                "() => document.body ? document.body.innerText : ''") or ""
            (REPORTS / "combo_slider_sem_slider.txt").write_text(
                body, encoding="utf-8")
            artifacts.append("combo_slider_sem_slider.txt")
            await shot(page, "06_final", artifacts, full_page=True)

    doc = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "slider_montou": quadro_txt is not None,
        "quadro": quadro_txt,
        "timeline": timeline,
        "network": net,
        "artifacts": artifacts,
    }
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    log(f"JSON: {OUT_JSON}")


if __name__ == "__main__":
    asyncio.run(main())
