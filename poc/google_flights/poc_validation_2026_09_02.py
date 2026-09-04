"""
Google Flights POC - Validação 2026-09-02 (re-baseline)
Abordagem: URL direta com query textual `q=` + locale fixado (Decisão 11 do design.md).

Critério de sucesso: preços reais extraídos (execução sem exceção NÃO é sucesso).

Modos:
  experiment - E1 (datas-alvo 2027) + E2 (controle, datas próximas), origem GRU
  gate       - 3 execuções consecutivas por origem com >=3 preços reais cada

Uso:
  python poc/google_flights/poc_validation_2026_09_02.py experiment
  python poc/google_flights/poc_validation_2026_09_02.py gate [--origins GRU,CGH,VCP] [--headless]
"""

import argparse
import asyncio
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Console Windows (cp1252) não imprime setas/checkmarks — força UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Configuração do monitoramento (design.md: Dynamic parameters)
ORIGINS = ["GRU", "CGH", "VCP"]
DESTINATION = "BKK"
TARGET_DEPARTURE = "2027-07-28"   # datas-alvo da viagem
TARGET_RETURN = "2027-08-05"
CONTROL_DEPARTURE = "2026-12-08"  # controle: ~3 meses à frente (janela aberta)
CONTROL_RETURN = "2026-12-16"

PRICE_RE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)")
PRICE_FLOOR_BRL = 100  # sanity: nenhuma passagem internacional custa menos

BLOCK_MARKERS = ["unusual traffic", "tráfego incomum", "/sorry/", "confirm you're human"]
NOT_OPEN_MARKERS = [
    "prices are not available", "não estão disponíveis", "nao estao disponiveis",
    "ainda não disponíveis", "not yet available", "não é possível encontrar",
    "muito distante", "data de voo solicitada",  # "A data de voo solicitada está muito distante"
]

REPORTS = Path(__file__).resolve().parents[1] / "reports"
RESULTS_JSON = REPORTS / "validation_results_2026-09-02.json"


def build_q_url(origin: str, departure: str, return_date: str) -> str:
    """URL de resultados via query textual com locale/moeda fixados (hl/gl/curr)."""
    q = f"Flights from {origin} to {DESTINATION} on {departure} through {return_date}"
    return (
        "https://www.google.com/travel/flights"
        f"?q={quote(q)}&hl=pt-BR&gl=BR&curr=BRL"
    )


def parse_prices(text: str) -> list[int]:
    """Extrai preços BRL normalizados (int) com sanity check."""
    out = set()
    for match in PRICE_RE.findall(text):
        value = int(round(float(match.replace(".", "").replace(",", "."))))
        if value >= PRICE_FLOOR_BRL:
            out.add(value)
    return sorted(out)


class NetworkCapture:
    """S2: acumula corpos de resposta p/ extração imune a reestruturação de DOM."""

    MAX_BYTES = 5 * 1024 * 1024

    def __init__(self):
        self.bodies: list[str] = []
        self._bytes = 0

    async def on_response(self, response):
        try:
            url = response.url
            if "gstatic" in url or ".png" in url or ".woff" in url:
                return
            if response.status != 200:
                return
            body = await response.text()
            if "R$" in body or "price" in body.lower():
                self._bytes += len(body)
                if self._bytes < self.MAX_BYTES:
                    self.bodies.append(body)
        except Exception:
            pass  # respostas binárias/redirects são esperadas


async def run_once(origin: str, departure: str, return_date: str,
                   label: str, headless: bool) -> dict:
    """Uma execução: navega pela URL q=, aguarda resultados, extrai preços."""
    started = time.monotonic()
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{stamp}] === {label}: {origin}→{DESTINATION} {departure}→{return_date} ===")
    print(f"  URL: {build_q_url(origin, departure, return_date)}")

    result = {
        "label": label, "origin": origin, "destination": DESTINATION,
        "departure": departure, "return": return_date,
        "status": "UNKNOWN", "prices": [], "network_price_count": 0,
        "li_with_price_count": 0, "suggestion_prices": [],
        "sample_options": [], "execution_time": None,
        "timestamp": datetime.now().isoformat(), "evidence": {},
    }
    capture = NetworkCapture()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        page.on("response", capture.on_response)

        try:
            await page.goto(build_q_url(origin, departure, return_date), timeout=60_000)
            await page.wait_for_load_state("domcontentloaded", timeout=30_000)

            # Aguarda resultados: >=3 preços distintos no texto da página (poll 45s)
            body_text = ""
            for _ in range(15):
                await asyncio.sleep(3)
                body_text = await page.evaluate(
                    "() => document.body ? document.body.innerText : ''")
                if len(parse_prices(body_text)) >= 3:
                    break

            await page.screenshot(
                path=str(REPORTS / f"validation_{label}_{origin}.png"), full_page=True)
            html = await page.content()
            (REPORTS / f"validation_{label}_{origin}.html").write_text(
                html, encoding="utf-8")
            result["evidence"] = {
                "screenshot": f"validation_{label}_{origin}.png",
                "html": f"validation_{label}_{origin}.html",
            }

            content_lower = (await page.content()).lower()
            url_now = page.url

            # Classificação antes da extração
            if any(m in url_now for m in ("/sorry/",)) or \
                    any(m in content_lower for m in BLOCK_MARKERS):
                result["status"] = "BLOCKED"
                return result

            # Estados "sem voos para estas datas" ANTES da extração de preços —
            # preços de sugestões de datas alternativas NÃO são resultados
            if "nenhum voo para sua pesquisa" in content_lower:
                result["status"] = "NO_AVAILABILITY"
                result["suggestion_prices"] = sorted(parse_prices(body_text))
                print(f"  [INFO] Sem voos p/ estas datas; "
                      f"sugestões c/ preço: {result['suggestion_prices'][:5]}")
                return result
            if "muito distante" in content_lower:
                result["status"] = "CALENDAR_NOT_OPEN"
                return result

            # S1: DOM - texto integral da página + <li> de resultado p/ estrutura
            # (resultados renderizam como <li class="pIav2d">, não role="listitem")
            dom_prices: set[int] = set()
            sample_options = []
            dom_prices.update(parse_prices(body_text))

            result_lis = await page.query_selector_all("li.pIav2d") \
                or await page.query_selector_all("li")
            li_with_price = 0
            for item in result_lis[:60]:
                try:
                    text = await item.inner_text()
                except Exception:
                    continue
                if parse_prices(text):
                    li_with_price += 1
                    if len(sample_options) < 5:
                        sample_options.append(text.strip()[:400])
            result["li_with_price_count"] = li_with_price

            # fallback DOM amplo: aria-labels costumam carregar "R$ X"
            if len(dom_prices) < 3:
                aria_texts = await page.eval_on_selector_all(
                    "button[aria-label]", "els => els.map(e => e.ariaLabel)")
                for t in aria_texts or []:
                    dom_prices.update(parse_prices(t or ""))

            # S2: rede - contagem independente de DOM
            network_prices: set[int] = set()
            for body in capture.bodies:
                network_prices.update(parse_prices(body))

            result["prices"] = sorted(dom_prices)
            result["network_price_count"] = len(network_prices)
            result["sample_options"] = sample_options

            if len(dom_prices) >= 3:
                result["status"] = "RESULTS"
            elif len(dom_prices) >= 1 and li_with_price > 2:
                result["status"] = "THIN_RESULTS"  # resultados ok, extração fraca
            elif any(m in content_lower for m in NOT_OPEN_MARKERS):
                result["status"] = "CALENDAR_NOT_OPEN"
            else:
                result["status"] = "NO_RESULTS"

        except Exception as exc:
            result["status"] = "ERROR"
            result["error"] = str(exc)[:300]
            print(f"  [ERROR] {exc}")
        finally:
            result["execution_time"] = round(time.monotonic() - started, 1)
            await context.close()
            await browser.close()

    print(f"  Status: {result['status']} | "
          f"preços DOM: {len(result['prices'])} | "
          f"preços rede: {result['network_price_count']} | "
          f"<li> c/ preço: {result['li_with_price_count']} | "
          f"{result['execution_time']}s")
    if result["prices"]:
        sample = result["prices"][:5]
        print(f"  Menores preços DOM: R$ {sample[0]:,} ... R$ {sample[-1]:,}"
              .replace(",", "."))
    return result


def save_results(results: list[dict]):
    existing = json.loads(RESULTS_JSON.read_text(encoding="utf-8")) \
        if RESULTS_JSON.exists() else []
    RESULTS_JSON.write_text(
        json.dumps(existing + results, ensure_ascii=False, indent=2),
        encoding="utf-8")


async def experiment(headless: bool) -> int:
    """E1 (2027) + E2 (controle) em GRU — matriz de decisão do findings doc."""
    e1 = await run_once("GRU", TARGET_DEPARTURE, TARGET_RETURN, "E1_2027", headless)
    await asyncio.sleep(random.uniform(6, 10))  # rate limit entre runs
    e2 = await run_once("GRU", CONTROL_DEPARTURE, CONTROL_RETURN,
                        "E2_controle", headless)
    results = [e1, e2]
    save_results(results)

    e1, e2 = results[0]["status"], results[1]["status"]
    print("\n" + "=" * 70)
    print(f"MATRIZ: E1(2027)={e1} | E2(controle)={e2}")
    if e1 == "RESULTS":
        print("→ Abordagem OK, janela 2027 aberta. Seguir para gate com datas-alvo.")
        return 0
    if e2 == "RESULTS":
        print("→ Abordagem OK, janela 2027 fechada (CALENDAR_NOT_OPEN esperado em E1).")
        print("  Gate em datas de controle + detectar CALENDAR_NOT_OPEN para 2027.")
        return 0
    print("→ q= rejeitado ou bloqueio. Acionar fallbacks (form pt-BR / tfs protobuf).")
    return 1


async def gate(origins: list[str], use_target_dates: bool, headless: bool) -> int:
    """Gate: 3/3 execuções consecutivas por origem com >=3 preços reais."""
    dep = TARGET_DEPARTURE if use_target_dates else CONTROL_DEPARTURE
    ret = TARGET_RETURN if use_target_dates else CONTROL_RETURN
    results = []
    for origin in origins:
        for run in range(1, 4):
            r = await run_once(origin, dep, ret, f"gate_r{run}", headless)
            results.append(r)
            save_results([r])
            await asyncio.sleep(random.uniform(6, 10))  # rate limit entre runs

    ok = [
        r["status"] == "RESULTS" and len(r["prices"]) >= 3
        and (r["execution_time"] or 999) < 300
        for r in results
    ]
    passed = sum(ok)
    print("\n" + "=" * 70)
    print(f"GATE: {passed}/{len(results)} runs com >=3 preços reais (<5min cada)")
    for r in results:
        mark = "✓" if (r["status"] == "RESULTS" and len(r["prices"]) >= 3) else "✗"
        print(f"  {mark} {r['label']} {r['origin']}: {r['status']} "
              f"({len(r['prices'])} preços, {r['execution_time']}s)")
    return 0 if passed == len(results) else 1


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["experiment", "gate"])
    parser.add_argument("--origins", default=",".join(ORIGINS))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--target-dates", action="store_true",
        help="gate usa datas-alvo 2027 em vez das datas de controle")
    args = parser.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print(f"GOOGLE FLIGHTS POC VALIDAÇÃO — modo {args.mode.upper()}")
    print(f"headless={args.headless} | reports: {REPORTS}")
    print("=" * 70)

    if args.mode == "experiment":
        sys.exit(await experiment(args.headless))
    else:
        sys.exit(await gate(args.origins.split(","), args.target_dates, args.headless))


if __name__ == "__main__":
    asyncio.run(main())
