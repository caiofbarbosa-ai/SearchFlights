"""Seleção de voos (Fase 9 — design: Decisão 7, 30h máx, híbrido sob 120k)."""

from src.config import settings
from src.models import FlightQuote


def filter_by_duration(quotes: list[FlightQuote]) -> list[FlightQuote]:
    """9.2 — exclui itinerários acima do limite (30h). Opções sem duração
    informada passam (extração estruturada é best-effort no MVP)."""
    return [q for q in quotes
            if q.duration_minutes is None
            or q.duration_minutes <= settings.max_duration_minutes]


def select_lowest_cash(quotes: list[FlightQuote]) -> FlightQuote | None:
    """9.3 — menor preço em dinheiro entre opções válidas (6.8–6.9)."""
    valid = [q for q in filter_by_duration(quotes)
             if q.status == "SUCCESS" and q.cash_price_brl]
    return min(valid, key=lambda q: q.cash_price_brl, default=None)


def select_lowest_miles(quotes: list[FlightQuote]) -> FlightQuote | None:
    """9.4 — menor só-milhas/pontos entre opções válidas."""
    valid = [q for q in filter_by_duration(quotes)
             if q.status == "SUCCESS" and q.miles]
    return min(valid, key=lambda q: q.miles, default=None)


def select_best_hybrid(quotes: list[FlightQuote]) -> FlightQuote | None:
    """9.5 — híbrido com MAIOR milhas sob o limite (melhor valor econômico)."""
    valid = [q for q in filter_by_duration(quotes)
             if q.status == "SUCCESS" and q.hybrid_miles
             and q.hybrid_miles <= settings.hybrid_max_miles]
    return max(valid, key=lambda q: q.hybrid_miles, default=None)
