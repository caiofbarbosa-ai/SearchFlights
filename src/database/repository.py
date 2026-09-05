"""Camada de persistência Supabase (Fase 2 — tasks 2.1–2.5)."""

import logging
from datetime import date

from supabase import create_client

from src.config import settings
from src.models import FlightQuote, Promotion

log = logging.getLogger(__name__)

_client = None


def get_client():
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError(
                "SUPABASE_URL/SUPABASE_KEY ausentes — configure o .env")
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


def create_execution(execution_date: date) -> str:
    """Cria o registro daily_executions; retorna o uuid (2.2, 2.5)."""
    data = get_client().table("daily_executions").insert(
        {"execution_date": execution_date.isoformat()}).execute()
    return data.data[0]["id"]


def open_execution(execution_date: date) -> str:
    """Uma linha por dia: varreduras parciais (--only rss) fazem merge na
    execução existente do dia em vez de criar linha duplicada."""
    client = get_client()
    data = client.table("daily_executions").select("id").eq(
        "execution_date", execution_date.isoformat()).limit(1).execute()
    if data.data:
        return data.data[0]["id"]
    return create_execution(execution_date)


def finish_execution(execution_id: str, statuses: dict, overall: str,
                     error_details: dict | None = None) -> None:
    payload = {
        **statuses,
        "overall_status": overall,
        "finished_at": "now()",
    }
    if error_details:
        payload["error_details"] = error_details
    get_client().table("daily_executions").update(payload).eq(
        "id", execution_id).execute()


def telegram_already_sent(execution_date: date) -> bool:
    """Idempotência do Telegram (10.7): não reenviar no mesmo dia."""
    data = get_client().table("daily_executions").select(
        "telegram_status").eq(
        "execution_date", execution_date.isoformat()).execute()
    return any(row["telegram_status"] for row in data.data)


def set_telegram_status(execution_id: str, status: str) -> None:
    get_client().table("daily_executions").update(
        {"telegram_status": status}).eq("id", execution_id).execute()


def insert_quote(execution_id: str, execution_date: date, q: FlightQuote) -> None:
    payload = {
        "execution_id": execution_id,
        "execution_date": execution_date.isoformat(),
        "source": q.source,
        "origin": q.origin,
        "destination": q.destination,
        "departure_date": q.departure_date.isoformat(),
        "return_date": q.return_date.isoformat(),
        "status": q.status,
        "passengers": q.passengers,
        "cash_price_brl": q.cash_price_brl,
        "miles": q.miles,
        "cash_component_brl": q.cash_component_brl,
        "airline": q.airline,
        "duration_minutes": q.duration_minutes,
        "stops": q.stops,
        "price_is_per_passenger": q.price_is_per_passenger,
        "raw_sample": q.raw_sample,
    }
    get_client().table("daily_flight_quotes").insert(payload).execute()


def promotions_last_24h() -> list[Promotion]:
    """Notícias persistidas nas últimas 24h (inclui inserções de varreduras
    RSS intermediárias) — é o que o relatório diário deve exibir."""
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(hours=24))         .isoformat()
    data = get_client().table("daily_promotions").select("*").gte(
        "created_at", since).order("created_at").execute()
    return [Promotion(article_url=r["article_url"], title=r["title"] or "",
                      source_feed=r.get("source_feed") or "",
                      published_at=r.get("published_at"))
            for r in data.data]


def insert_promotions(promotions: list[Promotion]) -> list[Promotion]:
    """Insere com ON CONFLICT DO NOTHING; retorna apenas as novas (2.4, 5.5–5.6)."""
    client = get_client()
    new_ones: list[Promotion] = []
    for promo in promotions:
        data = client.table("daily_promotions").upsert(
            {"article_url": promo.article_url,
             "title": promo.title,
             "source_feed": promo.source_feed,
             "published_at": promo.published_at,
             "matched_keywords": promo.matched_keywords},
            on_conflict="article_url",
            ignore_duplicates=True).execute()
        if data.data:
            new_ones.append(promo)
    return new_ones
