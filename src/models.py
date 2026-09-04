"""Modelos de dados e status de execução (design: Decisões 4 e 5)."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional


class Status:
    SUCCESS = "SUCCESS"
    NO_AVAILABILITY = "NO_AVAILABILITY"
    CALENDAR_NOT_OPEN = "CALENDAR_NOT_OPEN"
    BLOCKED = "BLOCKED"
    TIMEOUT = "TIMEOUT"
    PARSER_ERROR = "PARSER_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# Status considerados "executou e respondeu corretamente" (não são falha técnica)
OK_STATUSES = {Status.SUCCESS, Status.NO_AVAILABILITY, Status.CALENDAR_NOT_OPEN}


@dataclass
class FlightQuote:
    source: str                     # google | smiles | azul
    origin: str
    destination: str
    departure_date: date
    return_date: date
    status: str
    passengers: int = 2
    cash_price_brl: Optional[float] = None      # total p/ passageiros (google)
    miles: Optional[int] = None                 # menor só-milhas/pontos
    cash_component_brl: Optional[float] = None  # componente $ do híbrido (azul)
    hybrid_miles: Optional[int] = None          # milhas do híbrido
    airline: Optional[str] = None
    duration_minutes: Optional[int] = None
    stops: Optional[int] = None
    price_is_per_passenger: bool = False
    raw_sample: dict[str, Any] = field(default_factory=dict)


@dataclass
class Promotion:
    article_url: str
    title: str
    source_feed: str
    published_at: Optional[str] = None
    matched_keywords: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Contrato uniforme de retorno de cada fonte (design: Decisão 8)."""
    source: str
    status: str
    quotes: list[FlightQuote] = field(default_factory=list)
    promotions: list[Promotion] = field(default_factory=list)
    error: Optional[str] = None
