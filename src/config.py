"""Configuração central (Fase 1) — variáveis do .env local com defaults da rota."""

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")


def _env_date(name: str, default: str) -> date:
    return date.fromisoformat(os.getenv(name, default))


@dataclass
class Settings:
    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")

    # Telegram
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Rota monitorada (design: Dynamic parameters)
    origins: list[str] = field(
        default_factory=lambda: os.getenv("ORIGINS", "GRU,VCP").split(","))
    destination: str = os.getenv("DESTINATION", "BKK")
    departure_date: date = field(
        default_factory=lambda: _env_date("DEPARTURE_DATE", "2027-07-21"))
    return_date: date = field(
        default_factory=lambda: _env_date("RETURN_DATE", "2027-07-28"))
    adults: int = int(os.getenv("ADULTS", "2"))

    # Smiles/Azul: Chrome real para CDP-attach (vazio = autodetectar)
    chrome_path: str = os.getenv("CHROME_PATH", "")

    # RSS
    rss_feeds: list[str] = field(
        default_factory=lambda: [f for f in os.getenv("RSS_FEEDS", "").split(",")
                                 if f.strip()])
    promo_keywords: list[str] = field(
        default_factory=lambda: [k.strip().lower() for k in os.getenv(
            "PROMO_KEYWORDS", "c6").split(",") if k.strip()])
    # backfill: páginas antigas do feed (?paged=N) — a janela padrão de 30
    # posts cobre só ~1-2 dias em blogs que publicam muito
    rss_backfill_pages: int = int(os.getenv("RSS_BACKFILL_PAGES", "12"))

    # Seleção (design: 30h máx; híbrido sob 120k)
    max_duration_minutes: int = 30 * 60
    hybrid_max_miles: int = 120_000

    # Smiles rate-limit: intervalo entre origens (s) — Akamai bloqueia
    # buscas espaçadas por menos de ~10 min mesmo com IP "limpo"
    smiles_origin_spacing_s: int = 600


settings = Settings()

CHROME_CANDIDATES = [
    os.getenv("CHROME_PATH", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    raise RuntimeError(
        "Chrome não encontrado — instale o Google Chrome ou defina CHROME_PATH no .env")
