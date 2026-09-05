"""Orquestrador diário (Fase 10) — Variante A (Decisão 12).

Executa RSS + 3 scrapers com isolamento de erro por fonte (10.3),
persiste no Supabase (10.6), envia Telegram com idempotência (10.7).

Uso:
  python -m src.main                # execução completa
  python -m src.main --no-telegram  # sem notificação (testes)
  python -m src.main --only google  # uma fonte (testes)
"""

import argparse
import asyncio
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from src.config import REPO_ROOT, settings
from src.models import ExecutionResult, OK_STATUSES, Status

log = logging.getLogger("flight_monitor")


def setup_logging() -> Path:
    logs_dir = REPO_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{datetime.now():%Y-%m-%d}.log"
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    except PermissionError:
        # arquivo preso por outro processo (ex.: redirect do scheduler) —
        # segue só com console para nunca falhar a execução por causa de log
        print(f"Aviso: {log_file} indisponível; log apenas no console")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers)
    return log_file


def _run_source(source: str) -> ExecutionResult:
    """Executa uma fonte em thread própria com isolamento total (10.3)."""
    try:
        if source == "rss":
            from src.feeds import promotions
            promos, rss_status = promotions.fetch_new_promotions()
            return ExecutionResult(source="rss", status=rss_status,
                                   promotions=promos)
        if source == "google":
            from src.scrapers import google_flights
            return ExecutionResult(source="google", status=Status.SUCCESS,
                                   quotes=asyncio.run(google_flights.scrape()))
        if source == "smiles":
            from src.scrapers import smiles
            return ExecutionResult(source="smiles", status=Status.SUCCESS,
                                   quotes=asyncio.run(smiles.scrape()))
        if source == "azul":
            from src.scrapers import azul
            return ExecutionResult(source="azul", status=Status.SUCCESS,
                                   quotes=asyncio.run(azul.scrape()))
    except Exception as exc:
        log.exception("Fonte %s falhou", source)
        return ExecutionResult(source=source, status=Status.UNKNOWN_ERROR,
                               error=str(exc)[:500])
    raise ValueError(f"fonte desconhecida: {source}")


def _worst(results: list[ExecutionResult]) -> str:
    """Status por fonte — APENAS as fontes executadas nesta corrida
    (execuções parciais não fabricam status das fontes ausentes)."""
    out = {}
    for r in results:
        if r.source == "rss":
            out["rss_status"] = r.status
            continue
        if r.error or not r.quotes:
            out[f"{r.source}_status"] = r.status if not r.quotes \
                else next((q.status for q in r.quotes
                           if q.status != Status.SUCCESS), Status.SUCCESS)
        else:
            # pior status das origens (NO_AVAILABILITY/CALENDAR_NOT_OPEN são ok)
            bad = [q.status for q in r.quotes if q.status not in OK_STATUSES]
            out[f"{r.source}_status"] = bad[0] if bad else Status.SUCCESS
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--only", choices=["rss", "google", "smiles", "azul"])
    args = parser.parse_args()

    log_file = setup_logging()
    log.info("=== Flight Monitor — execução diária ===")
    log.info("rota: %s → %s | %s → %s | %d adultos",
             "+".join(settings.origins), settings.destination,
             settings.departure_date, settings.return_date, settings.adults)

    sources = [args.only] if args.only else ["rss", "google", "smiles", "azul"]
    execution_date = date.today()

    from src.database import repository

    execution_id = None
    try:
        execution_id = repository.open_execution(execution_date)
        log.info("execução do dia: %s", execution_id)
    except Exception as exc:
        log.error("Supabase indisponível (%s) — seguindo sem persistência", exc)

    # 10.3 (revisado 2026-09-05): execução SEQUENCIAL com isolamento por fonte.
    # Paralelismo causava contenção (3 Chrome pesados simultâneos no notebook):
    # Azul falhava por timeout EXCLUSIVAMENTE em runs paralelas e funcionava
    # isolado (evidência 04-05/09). Isolamento de erro mantido por fonte.
    results: list[ExecutionResult] = []
    for source in sources:
        log.info(">>> fonte: %s", source)
        results.append(_run_source(source))

    quotes = [q for r in results for q in r.quotes]
    promotions = [p for r in results for p in r.promotions]
    statuses = _worst(results)

    for r in results:
        if r.error:
            statuses.setdefault("error_details", {})[r.source] = r.error

    # overall = pior situação REAL das fontes (não do wrapper de execução):
    # BLOCKED/UNKNOWN_ERROR em qualquer fonte impede "SUCCESS" geral
    source_statuses = [statuses[s] for s in
                       ("google_status", "smiles_status", "azul_status",
                        "rss_status") if s in statuses]
    all_ok = all(s in OK_STATUSES for s in source_statuses)
    any_ok = any(s in OK_STATUSES for s in source_statuses)
    overall = "SUCCESS" if all_ok else ("PARTIAL" if any_ok else "FAILED")
    statuses["overall_status"] = overall

    for q in quotes:
        log.info("  [%s] %s: %s%s", q.source, q.origin, q.status,
                 f" — {q.cash_price_brl:.0f} BRL" if q.cash_price_brl else
                 (f" — {q.miles:,} pts".replace(",", ".") if q.miles else ""))
    log.info("promoções novas: %d | status geral: %s", len(promotions), overall)

    # persistência (10.6)
    if execution_id:
        try:
            for quote in quotes:
                repository.insert_quote(execution_id, execution_date, quote)
            error_details = statuses.pop("error_details", None)
            repository.finish_execution(execution_id, statuses, overall,
                                        error_details)
        except Exception as exc:
            log.error("Falha ao persistir: %s", exc)

    # Telegram com idempotência (10.7, 4.7)
    if not args.no_telegram and "rss" in sources and len(sources) > 1:
        try:
            if repository.telegram_already_sent(execution_date):
                log.info("Telegram já enviado hoje — pulando (idempotência)")
                statuses["telegram_status"] = "SKIPPED_IDEMPOTENT"
            else:
                from src.notifications import telegram
                try:
                    # inclui notícias persistidas por varreduras RSS intermediárias
                    report_promotions = repository.promotions_last_24h()
                except Exception:
                    report_promotions = promotions
                message = telegram.build_report(execution_date, quotes,
                                                report_promotions, statuses)
                sent = telegram.send_message(message)
                statuses["telegram_status"] = "SUCCESS" if sent else "FAILED"
                if execution_id:
                    repository.set_telegram_status(execution_id,
                                                   statuses["telegram_status"])
        except Exception as exc:
            log.error("Falha no Telegram: %s", exc)

    log.info("log completo: %s", log_file)
    return 0 if overall != "FAILED" else 1


if __name__ == "__main__":
    sys.exit(main())
