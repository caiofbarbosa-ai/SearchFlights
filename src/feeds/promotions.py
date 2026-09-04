"""Monitor de promoções RSS (Fase 5 — tasks 5.1–5.7)."""

import logging
from datetime import datetime

import feedparser

from src.config import settings
from src.models import Promotion

log = logging.getLogger(__name__)


def _parse_published(entry) -> str | None:
    for field in ("published", "updated"):
        value = entry.get(field)
        if value:
            try:
                parsed = feedparser._parse_date(value)  # noqa: SLF001
                return datetime(*parsed[:6]).isoformat()
            except Exception:
                continue
    return None


def _match_keywords(text: str) -> list[str]:
    lower = text.lower()
    return [k for k in settings.promo_keywords if k in lower]


def _feed_variants(url: str) -> list[str]:
    """Página 1 + páginas de backfill (WordPress pagina feeds com ?paged=N)."""
    sep = "&" if "?" in url else "?"
    return [url] + [f"{url}{sep}paged={n}"
                    for n in range(2, settings.rss_backfill_pages + 1)]


def fetch_new_promotions() -> tuple[list[Promotion], str]:
    """Lê os feeds (incluindo backfill de páginas antigas), filtra por
    keywords e deduplica via banco. Retorna (novas promoções, status RSS)."""
    from src.database import repository

    if not settings.rss_feeds:
        log.info("Nenhum feed RSS configurado (RSS_FEEDS vazio)")
        return [], "SUCCESS"

    candidates: list[Promotion] = []
    failures = 0
    for feed_url in settings.rss_feeds:
        try:
            seen_links: set[str] = set()
            for variant in _feed_variants(feed_url):
                feed = feedparser.parse(variant)
                if feed.bozo and not feed.entries:
                    raise ValueError(getattr(feed, "bozo_exception",
                                             "feed inválido"))
                for entry in feed.entries:
                    link = entry.get("link", "")
                    if link in seen_links:
                        continue  # páginas de backfill podem repetir
                    seen_links.add(link)
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    matched = _match_keywords(f"{title} {summary}")
                    if not matched:
                        continue  # 5.3 filtro por keywords
                    candidates.append(Promotion(
                        article_url=link,
                        title=title,
                        source_feed=feed_url,
                        published_at=_parse_published(entry),
                        matched_keywords=matched,
                    ))
        except Exception as exc:
            failures += 1
            log.warning("Feed falhou (%s): %s", feed_url[:60], exc)

    if failures == len(settings.rss_feeds) and settings.rss_feeds:
        return [], "UNKNOWN_ERROR"

    # deduplicação por article_url no banco (5.4–5.6)
    candidates = [c for c in candidates if c.article_url]
    unique: dict[str, Promotion] = {c.article_url: c for c in candidates}
    new_ones = repository.insert_promotions(list(unique.values()))
    log.info("RSS: %d candidatas, %d novas", len(unique), len(new_ones))
    return new_ones, "SUCCESS"
