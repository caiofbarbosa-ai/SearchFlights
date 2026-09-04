"""Azul POC - Run única CGH com wait_for_widget + reload (robustez SPA lazy)."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from poc_azul_gate import REPORTS, RESULTS_JSON, log, run_once  # noqa: E402


async def main():
    # run_once do gate, com tentativa dupla (reload resolve SPA lazy)
    r = await run_once("CGH", "gate_cgh_retry")
    if r["status"] in ("UNKNOWN_PAGE", "ERROR"):
        log("segunda tentativa (reload resolve SPA lazy)...")
        r = await run_once("CGH", "gate_cgh_retry2")
    save(r)
    print(f"\nCGH final: {r['status']} | pontos: {r['points'][:6]}")
    return 0 if r["status"] == "RESULTS" else 1


def save(entry: dict):
    existing = json.loads(RESULTS_JSON.read_text(encoding="utf-8")) \
        if RESULTS_JSON.exists() else []
    RESULTS_JSON.write_text(
        json.dumps(existing + [entry], ensure_ascii=False, indent=2),
        encoding="utf-8")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
