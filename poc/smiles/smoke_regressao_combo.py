"""Regressão SMILES_COMBO_ENABLED (tasks 3.4/7.4 da change
add-smiles-money-combo): com o flag OFF, o fluxo de produção deve produzir
quote idêntica à pré-combo — só-milhas/status/airline intactos, SEM
cash_component_brl e SEM raw_sample["combo"] — e o Telegram cai na linha
"~combo (estimado)" (fallback). Com o flag ON, a linha real 💰 substitui.

Chama a função de PRODUÇÃO _search_origin e despeja a quote + as linhas de
Telegram em JSON. Duas execuções (env por processo, settings lê no import):
  SMILES_COMBO_ENABLED=false python poc/smiles/smoke_regressao_combo.py off
  SMILES_COMBO_ENABLED=true  python poc/smiles/smoke_regressao_combo.py on
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

from src.config import settings
from src.notifications.telegram import _quote_lines
from src.scrapers.chrome_cdp import RealChrome
from src.scrapers.smiles import _search_origin

REPORTS = Path("poc/reports").resolve()


def log(m):
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


async def main():
    suffix = sys.argv[1] if len(sys.argv) > 1 else "run"
    log(f"SMILES_COMBO_ENABLED={settings.smiles_combo_enabled} "
        f"(max_miles={settings.smiles_combo_max_miles:,})".replace(",", "."))
    # config de produção: driver vanilla, port 9301 (como em scrape())
    async with RealChrome(port=9301, driver="playwright") as chrome:
        page = await chrome.page()
        q = await _search_origin(page, "GRU")
    t_lines = _quote_lines([q], "smiles")
    out = {
        "sufixo": suffix,
        "flag_combo": settings.smiles_combo_enabled,
        "status": str(q.status),
        "miles": q.miles,
        "hybrid_miles": q.hybrid_miles,
        "cash_component_brl": q.cash_component_brl,
        "airline": q.airline,
        "passengers": q.passengers,
        "raw_sample": q.raw_sample,
        "telegram_lines": t_lines,
    }
    p = REPORTS / f"combo_regressao_{suffix}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str),
                 encoding="utf-8")
    log(f"status={out['status']} miles={out['miles']} "
        f"hybrid={out['hybrid_miles']} cash={out['cash_component_brl']} "
        f"airline={out['airline']}")
    for ln in t_lines:
        log(f"TG: {ln}")
    log(f"JSON: {p}")


if __name__ == "__main__":
    asyncio.run(main())
