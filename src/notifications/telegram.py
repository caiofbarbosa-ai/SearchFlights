"""Notificador Telegram (Fase 4 — tasks 4.1–4.7). HTML + escaping + idempotência."""

import html
import json
import logging
import urllib.parse
import urllib.request

from src.config import settings
from src.models import FlightQuote, OK_STATUSES, Promotion, Status

log = logging.getLogger(__name__)

# Estimativa provisória do combo Smiles & Money (enquanto a captura real do
# painel não funciona): combo com 200k milhas ≈ (só-milhas − 200.000) × R$ 0,022
COMBO_ESTIMATE_MILES = 200_000
COMBO_ESTIMATE_RATE_BRL_PER_MILE = 0.022

API = "https://api.telegram.org/bot{token}/sendMessage"


def escape(text: str) -> str:
    """Escaping obrigatório para HTML (4.3)."""
    return html.escape(text, quote=False)


def _fmt_brl(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"R$ {value:,.0f}".replace(",", ".")


def _quote_lines(quotes: list[FlightQuote], source: str = "") -> list[str]:
    lines = []
    by_origin: dict[str, list[FlightQuote]] = {}
    for q in quotes:
        by_origin.setdefault(q.origin, []).append(q)
    for origin, qs in by_origin.items():
        best = next((q for q in qs
                     if q.status == Status.SUCCESS and q.miles is not None), None)
        cash = next((q for q in qs
                     if q.status == Status.SUCCESS and q.cash_price_brl), None)
        for q in qs:
            if q.status == Status.SUCCESS:
                continue
            label = {
                Status.NO_AVAILABILITY: "sem disponibilidade",
                Status.CALENDAR_NOT_OPEN: "calendário ainda não aberto",
                Status.BLOCKED: "acesso bloqueado",
                Status.TIMEOUT: "timeout",
                Status.PARSER_ERROR: "erro de parsing",
                Status.UNKNOWN_ERROR: "erro desconhecido",
            }.get(q.status, q.status.lower())
            lines.append(f"  {escape(origin)}: {label}")
        if cash:
            suffix = " /pessoa" if cash.price_is_per_passenger else ""
            airline = f" — {escape(cash.airline)}" if cash.airline else ""
            lines.append(f"  💵 {escape(origin)}: {_fmt_brl(cash.cash_price_brl)}"
                         f"{suffix}{airline}")
        if best and best.miles:
            extra = (f" (+ {_fmt_brl(best.cash_component_brl)})"
                     if best.cash_component_brl else "")
            airline = f" — {escape(best.airline)}" if best.airline else ""
            lines.append(f"  🎫 {escape(origin)}: {best.miles:,} pontos{extra}"
                         f"{airline}".replace(",", "."))
        combo = next((q for q in qs if q.status == Status.SUCCESS
                      and q.hybrid_miles and q.cash_component_brl), None)
        if combo:
            lines.append(f"  💰 {escape(origin)}: combo {combo.hybrid_miles:,} "
                         f"milhas + {_fmt_brl(combo.cash_component_brl)}"
                         .replace(",", "."))
        elif source == "smiles" and best and best.miles                 and best.miles > COMBO_ESTIMATE_MILES:
            # estimativa provisória: painel de combos não capturável em automação
            est = (best.miles - COMBO_ESTIMATE_MILES) \
                * COMBO_ESTIMATE_RATE_BRL_PER_MILE
            lines.append(f"  💰 {escape(origin)}: ~combo "
                         f"{COMBO_ESTIMATE_MILES:,} milhas + "
                         f"{_fmt_brl(est)} (estimado)".replace(",", "."))
    return lines


def build_report(execution_date: date, quotes: list[FlightQuote],
                 promotions: list[Promotion], statuses: dict) -> str:
    """Mensagem consolidada com todas as fontes (4.4–4.6)."""
    d = execution_date.strftime("%d/%m/%Y")
    parts = [f"<b>Monitor de Viagens — {d}</b>"]

    gf = [q for q in quotes if q.source == "google"]
    sm = [q for q in quotes if q.source == "smiles"]
    az = [q for q in quotes if q.source == "azul"]

    parts.append("\n✈️ <b>Google Flights (dinheiro)</b>")
    parts.extend(_quote_lines(gf, "google") or ["  — sem dados"])

    parts.append("\n🎫 <b>Smiles (milhas)</b>")
    parts.extend(_quote_lines(sm, "smiles") or ["  — sem dados"])

    parts.append("\n🔵 <b>Azul Fidelidade (pontos)</b>")
    parts.extend(_quote_lines(az, "azul") or ["  — sem dados"])

    parts.append("\n📣 <b>Promoções</b>")
    if promotions:
        for promo in promotions[:5]:
            parts.append(f"  • <a href=\"{promo.article_url}\">"
                         f"{escape(promo.title or promo.article_url)}</a>")
    else:
        parts.append("  Nenhuma promoção nova hoje.")  # 4.6

    overall = statuses.get("overall_status", "")
    if overall and overall != "SUCCESS":
        parts.append(f"\n⚠️ status geral: {escape(overall)}")
    return "\n".join(parts)


def send_message(text: str) -> bool:
    """Envia via Bot API (4.1). Retorna True em caso de sucesso."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        log.warning("Telegram não configurado no .env — mensagem não enviada")
        return False
    payload = json.dumps({
        "chat_id": settings.telegram_chat_id,
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        API.format(token=settings.telegram_bot_token), data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            ok = resp.status == 200
            if not ok:
                log.error("Telegram respondeu %s", resp.status)
            return ok
    except Exception as exc:
        log.error("Falha ao enviar Telegram: %s", exc)
        return False
