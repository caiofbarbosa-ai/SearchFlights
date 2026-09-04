"""
Smiles POC - Gate esparso (cadência de produção)
Akamai faz rate-limit por IP na API de disponibilidade (evidência 2026-09-02:
rajadas de buscas -> resultados vazios; busca isolada funciona).
Gate adaptado: 3 runs por origem com 10 min de intervalo (~85 min total).
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from poc_smiles_gate_cdp import REPORTS, RESULTS_JSON, log, run_once  # noqa: E402

SPACING_S = 600  # 10 min entre buscas


def save(entry: dict):
    existing = json.loads(RESULTS_JSON.read_text(encoding="utf-8")) \
        if RESULTS_JSON.exists() else []
    RESULTS_JSON.write_text(
        json.dumps(existing + [entry], ensure_ascii=False, indent=2),
        encoding="utf-8")


async def main():
    results = []
    plan = [(o, f"gate_r{r}") for r in (1, 2, 3) for o in ("GRU", "CGH", "VCP")]
    for i, (origin, label) in enumerate(plan):
        if i:
            log(f"aguardando {SPACING_S}s (rate-limit Akamai)...")
            await asyncio.sleep(SPACING_S)
        r = await run_once(origin, (2026, 12, 8), (2026, 12, 16), label)
        results.append(r)
        save(r)

    ok = [r["status"] == "RESULTS" and len(r["miles_values"]) >= 3 for r in results]
    print("\n" + "=" * 70)
    print(f"GATE SMILES ESPARSO: {sum(ok)}/{len(results)} runs com >=3 award prices")
    for r in results:
        mark = "✓" if (r["status"] == "RESULTS"
                       and len(r["miles_values"]) >= 3) else "✗"
        print(f"  {mark} {r['origin']} {r['label']}: {r['status']} "
              f"({len(r['miles_values'])} milhas, {r['execution_time']}s)")


if __name__ == "__main__":
    asyncio.run(main())
