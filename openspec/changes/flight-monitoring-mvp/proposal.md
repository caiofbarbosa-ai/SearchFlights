## Why

Build an automated flight monitoring system that tracks daily prices for São Paulo → Bangkok across cash, miles, and loyalty program promotions, providing consolidated intelligence via Telegram to enable optimal redemption decisions.

## What Changes

**New Capabilities:**

- **Daily automated execution** local no notebook via Windows Task Scheduler (10:00 BRT, com wake-from-sleep) — *atualizado 2026-09-02, Decisão 12 do design (arquitetura self-hosted Variante A): Smiles/Azul exigem browser real em IP residencial (Akamai); GitHub Actions permanece como opção futura apenas para Google Flights*
- **Multi-source flight price monitoring**:
  - Google Flights for cash prices (GRU, VCP → BKK)
  - Smiles program for miles-based redemption
  - Azul Pelo Mundo for points-based redemption
- **RSS feed monitoring** for C6 Bank/Átomos promotional campaigns
- **Consolidated Telegram reporting** with all results in a single message
- **Historical data persistence** in Supabase PostgreSQL for trend analysis
- **Error isolation** so individual source failures don't block overall execution
- **Deduplication** of promotional articles to avoid repeated notifications

**Key Constraints:**

- Target: 2 adults, 28/07/2027 - 05/08/2027
- Duration limit: 30 hours maximum
- Operating cost: R$ 0 using only free tiers
- Technology: Python + Playwright

## Capabilities

### New Capabilities

- `proof-of-concept`: POC phase to validate each scraper's technical feasibility before full implementation
- `daily-flight-monitoring`: Core scheduled execution orchestration, database persistence, and error handling framework
- `google-flights-scraper`: Web scraping for cash flight prices across GRU, VCP to BKK
- `smiles-scraper`: Miles availability and Smiles & Money options extraction
- `azul-scraper`: Azul Pelo Mundo points availability and hybrid options
- `promotion-monitor`: RSS feed monitoring for C6 Bank/Átomos promotions with filtering and deduplication
- `telegram-notifier`: Consolidated daily report generation and delivery

### Modified Capabilities

None (new project)

## Impact

**Dependencies:**
- Supabase (PostgreSQL, Free tier)
- Windows Task Scheduler (gatilho diário local — Variante A, Decisão 12)
- Google Chrome instalado (Smiles/Azul via CDP-attach)
- Telegram Bot API (Free)
- Python packages: Playwright, feedparser, supabase, python-dotenv

**Architecture:**
- Single-runtime Python application
- GitHub Actions for cron scheduling
- Supabase for data persistence
- Telegram for notifications

**Data Models:**
- `daily_executions`: Run tracking with per-source status
- `daily_flight_quotes`: Historical price/miles data
- `daily_promotions`: RSS article deduplication

**Security:**
- Credentials no arquivo `.env` local (SUPABASE_URL, SUPABASE_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) — fora do repositório
