## Context

This is a new project for an MVP-level flight and promotion monitoring system. The system will run daily automated checks for flight prices (cash, Smiles miles, Azul points) and promotional news (C6 Bank/Átomos), then send a consolidated report via Telegram.

**Key Constraints:**
- Operating cost must be R$ 0 (free tiers only)
- Single runtime (Python) to reduce complexity
- Target route: São Paulo (GRU/VCP) → Bangkok (BKK) for 2 adults — CGH removida (2026-09-03): aeroporto doméstico, sem voos internacionais/interline (evidência das POCs)
- Travel dates monitoradas: 21/07/2027 - 28/07/2027 (ajustado pelo usuário em 2026-09-03; datas originais do plano: 28/07 - 05/08/2027)
- Maximum itinerary duration: 30 hours

**Stakeholders:**
- End user: Receives daily Telegram reports for flight purchasing decisions
- Developer: Maintains scrapers as web sources change

## Goals / Non-Goals

**Goals:**
- Daily automated execution at 07:00 BRT via GitHub Actions
- Multi-source flight price monitoring (Google Flights, Smiles, Azul)
- RSS feed monitoring for C6 Bank/Átomos promotions
- Consolidated Telegram reporting with all results
- Historical data persistence for future trend analysis
- Error isolation so individual source failures don't block overall execution

**Non-Goals (explicitly out of scope for MVP):**
- Sophisticated mileage valuation calculations
- Opportunity scoring algorithms
- Historical price comparison features
- Price prediction
- Intraday monitoring
- Multiple configurable routes per user
- Multiple loyalty program accounts
- Baggage fee calculations
- Economic equivalence between cash and miles
- Commercial API integrations
- Real-time availability guarantees after query

## Decisions

### 1. Single Runtime Architecture

**Decision:** Use Python for all modules (scrapers, feeds, database, notifications).

**Rationale:**
- Reduces number of dependencies and configurations needed
- Simplifies GitHub Actions setup (no need for multi-language workflows)
- Python has excellent web scraping libraries (Playwright) and feed processing (feedparser)
- All modules can share common data models and database client

**Alternatives considered:**
- Node.js for scrapers + Python for feeds → More complex, two runtimes to manage
- Separate microservices → Overkill for MVP, higher operational cost

### 2. Trigger for Daily Execution — SUPERSEDED (ver Decisão 12)

> ⚠️ **SUPERSEDED 2026-09-02** pela Decisão 12 (execução self-hosted Variante A). Mantido como registro histórico. GitHub Actions permanece como opção futura apenas para o Google Flights (task 0.43, opcional).

**Decision (original):** Use GitHub Actions with cron at 10:00 UTC (07:00 BRT).

**Rationale:**
- Free tier sufficient for daily execution
- Built-in secret management
- No additional infrastructure needed
- Straightforward cron configuration

**Alternatives considered:**
- AWS Lambda + EventBridge → Would exceed $0 goal (potential costs)
- VPS cron → Requires payment and maintenance
- Supabase Functions → Less familiar for scheduled tasks

### 3. Supabase for Data Persistence

**Decision:** Use Supabase PostgreSQL (Free tier) for data storage.

**Rationale:**
- Generous free tier (500MB database)
- Built-in connection pooling
- Direct SQL access via Python client
- Automatic backups
- UUID generation for primary keys

**Alternatives considered:**
- SQLite in repo → Not suitable for GitHub Actions (no persistent storage)
- AWS RDS Free Tier → More complex setup, 12-month limit
- Firebase → Less SQL-friendly for structured queries

### 4. Database Schema Design

**Decision:** Three main tables: daily_executions, daily_flight_quotes, daily_promotions.

**Rationale:**
- `daily_executions`: Tracks each run with per-source status fields (google_status, smiles_status, azul_status, rss_status, telegram_status)
- `daily_flight_quotes`: One row per execution with columns for each source's results (normalization deferred to post-MVP)
- `daily_promotions`: UNIQUE constraint on article_url for deduplication

**Trade-off:** Denormalized flight quotes schema for MVP simplicity. Future iterations may normalize into separate tables per source.

### 5. Error State Enumeration

**Decision:** Explicit status codes: SUCCESS, NO_AVAILABILITY, CALENDAR_NOT_OPEN, BLOCKED, TIMEOUT, PARSER_ERROR, UNKNOWN_ERROR.

**Rationale:**
- Distinguishes technical failures from legitimate no-availability scenarios
- Enables clear reporting to users ("blocked" vs "no flights found")
- Each scraper returns uniform {status, data, error} structure

**Alternative considered:** Boolean success/failure → Would mask important distinctions

### 6. Playwright for Web Scraping

**Decision:** Use Playwright (with optional Playwright Stealth) for all web scrapers.

**Rationale:**
- Modern, well-maintained browser automation
- Good anti-detection capabilities (especially with Stealth)
- Python and JavaScript/TypeScript support
- Explicit waiting mechanisms (waitForResponse, waitForSelector)

**Alternatives considered:**
- Selenium → Older API, less reliable waiting
- Puppeteer → Node.js-first, would require multi-runtime
- HTTP API clients → Not applicable for sites without APIs

### 7. Selection Rules for MVP

**Decision:** Implement simple rules for MVP, defer economic optimization.

**Rules:**
- **Cash:** Lowest total price within 30h limit
- **Miles/Points only:** Lowest quantity within 30h limit
- **Hybrid (miles + money):** Highest mileage under 120k total, within 30h limit

**Rationale:**
- 120k limit is a placeholder for MVP based on typical redemption values
- Avoids complex economic calculations for initial version
- Architecture allows rule replacement without changing scrapers

**Future consideration:** Economic optimization (miles per dollar, cash equivalence)

### 8. Scraper Independence

**Decision:** Design scrapers as pluggable sources returning normalized data.

**Rationale:**
- Sources can be replaced (e.g., scraper → API) without affecting business logic
- Each scraper has same interface: `{status, data, error}`
- Normalization happens at scraper boundary

**Architecture:**
```
Source → Scraper → Normalized Data → Business Logic → Persistence → Notification
```

### 9. Feedparser for RSS

**Decision:** Use Python's feedparser library for RSS monitoring.

**Rationale:**
- Handles various RSS formats transparently
- Well-maintained, standard library
- Simple API for article extraction

**Alternative considered:** Direct HTTP + XML parsing → More error-prone

### 10. Telegram Format

**Decision:** Use HTML or MarkdownV2 with proper character escaping.

**Rationale:**
- Rich formatting support
- Familiar to users
- Both formats supported by Telegram Bot API

**Trade-off:** Must implement character escaping to avoid format breakage

### 11. Google Flights Access via Direct URL Query

**Decision (2026-09-02):** Access Google Flights by navigating directly to the results URL using the textual `q=` parameter with pinned locale (`hl=pt-BR&gl=BR&curr=BRL`), instead of automating the search form. Form interaction (typed dates in pt-BR, verified before submission) is the fallback; `tfs` protobuf URL is the fallback for reliable passenger count and trip type.

**Rationale:**
- POC re-baseline (`poc/reports/google_flights_poc_findings_and_mitigation.md`) showed the UI flow never reached the results page: departure date truncated, return date empty, URL direct attempt bounced to homepage — 0 prices extracted in every run
- The `q=` URL bypasses calendar navigation and suggestion modals entirely (the observed point of failure)
- Pinned locale makes the page deterministic, eliminating the language-dependent selector issues hit early in the POC

**Alternatives considered:**
- Full form automation (POC 2026-08-16 approach) → failed at date selection in all runs
- Paid APIs (SerpAPI) → **explicitly excluded** by the R$ 0 constraint (see Non-Goals); free tier (~100 searches/month) does not cover 3 origins × daily with retry margin

**Caveat:** textual `q=` may not configure 2 adults (default 1). Set passenger count via the passenger selector after navigation, or use `tfs`. Extraction must store the **total price for 2 adults** (`cash_price_brl`).

## Risks / Trade-offs

### Risk: Web source structure changes
**Impact:** High - Scrapers may break without notice
**Mitigation:**
- Explicit response validation before processing
- Graceful error handling with PARSER_ERROR status
- Regular monitoring and prompt updates

### Risk: Anti-bot detection escalation
**Impact:** High - Sources may block automated access
**Mitigation:**
- Playwright Stealth as first line of defense
- Explicit status reporting (BLOCKED) so users understand
- Paid API alternatives (e.g., SerpAPI) explicitly excluded per R$ 0 constraint — instead: reduce interaction surface (direct results URL, Decision 11), self-hosted runner on residential IP, local scheduled execution

### Risk: GitHub Actions datacenter IPs face stricter anti-bot
**Impact:** High - Scraper validated locally (residential IP) may hit CAPTCHA/blocks when running on GitHub Actions runners
**Mitigation (2026-09-02, Decisão 12):** execução local aprovada — risco aplicável apenas se a Variante B/nuvem for revisitada. Task 0.43 tornou-se opcional.

### Risk: máquina indisponível no horário da execução (Variante A)
**Impact:** Low - dia sem execução = 1 ponto faltante no histórico de preços
**Mitigation:**
- Notebook em repouso na tomada: Task Scheduler acorda (`-WakeToRun`) — "Allow wake timers" ativo no plano de energia
- "Start the task only if on AC power" desmarcado (tarefa roda mesmo na bateria)
- Missed day é aceitável para monitoramento; sem compensação no MVP

### Risk: GitHub Actions execution limits
**Impact:** Medium - Free tier has monthly minute limits
**Mitigation:**
- Single execution per day (well within limits)
- Efficient scraper timeout configuration
- Monitor usage; can migrate if needed

### Risk: Supabase free tier exhaustion
**Impact:** Medium - Database storage or connection limits
**Mitigation:**
- Current usage (~1 record/day) is far below limits
- Can archive old records if needed
- Migration path to paid tier is straightforward

### Risk: RSS feed changes or failures
**Impact:** Low - Promotions are supplementary to core flight monitoring
**Mitigation:**
- Feed validation and error handling
- Individual feed failures don't block other modules
- No promotions message is a valid state

### Trade-off: Denormalized schema
**Impact:** Medium - Harder to query historical trends by source
**Reasoning:** Acceptable for MVP; can normalize in future if analysis needs grow
**Migration path:** Add source-specific tables, migrate data, update queries

### Trade-off: Fixed 120k hybrid limit
**Impact:** Low - May not always find optimal economic choice
**Reasoning:** Simple placeholder rule for MVP; architecture allows rule replacement
**Future:** Implement economic calculation (miles value per dollar)

### 12. Self-Hosted Local Execution — Variante A (2026-09-02, APROVADA)

**Decision:** Execução diária **100% local no notebook do usuário**, disparada pelo **Windows Task Scheduler às 10:00 BRT** (ajustado de 07:00 pelo usuário em 2026-09-02), substituindo o cron do GitHub Actions (Decisão 2, superseded). GitHub Actions fica como opção futura somente para o Google Flights (task 0.43, opcional).

**Rationale (evidência das POCs de 2026-09-02):**
- Smiles e Azul exigem **browser real em IP residencial** (Akamai valida sensor+fingerprint; Playwright puro/patchright/Python puro/CI todos negados — ver findings docs). Único padrão validado: **CDP-attach em Chrome real** (`--remote-debugging-port` em perfil temporário descartável)
- Google Flights funciona local (gate 9/9) e evita o risco de CAPTCHA em datacenter IP
- RSS não depende de browser — roda em qualquer lugar
- R$ 0 mantido; zero serviços novos na Variante A

**Componentes:**
- Task Scheduler: gatilho diário 10:00 BRT com `-WakeToRun`, execução independente de bateria (`AllowStartIfOnBatteries`), limite de 30 min
- Repouso (sleep): suportado — o Task Scheduler acorda o notebook (notebook na tomada; "Allow wake timers" ativo no plano de energia)
- Orquestrador `src/main.py`: executa RSS + 3 scrapers com isolamento de erro por fonte, persiste no Supabase, envia Telegram
- Google Flights: Playwright próprio (browser embarcado) — local funciona
- Smiles/Azul: Chrome real + CDP (mesmo fluxo validado nos POCs; perfil temporário, não o perfil pessoal do usuário)
- Secrets: arquivo `.env` local (não GitHub Secrets)
- Logs: arquivo local por execução

**Trade-offs aceitos:**
- PC precisa estar ligado (ou em sleep na tomada) no horário — dia perdido = 1 ponto faltante no histórico (aceitável para monitoramento)
- Janelas do Chrome aparecem na tela por alguns minutos às 07:00 (execução é headed por exigência anti-bot)

**Riscos e mitigações:** ver "Risk: máquina indisponível no horário" em Risks / Trade-offs.

**Future:** Variante B (runner self-hosted do GitHub para histórico/log na UI) é migração de gatilho apenas — zero mudança de código.

### 13. Sequential Source Execution (2026-09-05)

**Decision:** As fontes executam SEQUENCIALMENTE (um browser por vez), substituindo o paralelismo com threads da Decisão/original 10.3. Isolamento de erro por fonte mantido.

**Rationale (evidência 04-05/09):** Azul falhava por timeout EXCLUSIVAMENTE em execuções paralelas (3 Chrome pesados simultâneos) e funcionava isolado — mesma versão de código. Smiles herda o mesmo risco de contenção. Ciclo total sequencial ~15-30 min, dentro do limite de 60 min da tarefa.

**Trade-off:** ciclo mais longo que o paralelo (~10 min). Aceito: confiabilidade > velocidade para monitoramento diário.

### Trade-off: Single route configuration
**Impact:** Low - Not generalizable to other routes
**Reasoning:** Reduces MVP complexity; can parameterize if MVP succeeds
**Future:** Add route configuration table, make scrapers fully dynamic

## Migration Plan

**Phase 0 - Proof of Concept (Week 1)**
*Validate each scraper's technical feasibility before committing to full implementation*

1. Set up local POC environment (Python, Playwright, playwright-stealth)
2. **Google Flights POC:** Build minimal scraper, test 3+ executions, validate anti-bot measures
3. **Smiles POC:** Build minimal scraper with API interception, test 3+ executions, validate data extraction
4. **Azul POC:** Build minimal portal scraper, test 3+ executions, validate award access
5. Document all POC results with: execution logs, anti-bot effectiveness, data structures
6. Make go/no-go decision for each source
7. Identify alternative approaches for any failed POCs
8. Obtain approval to proceed to full implementation

**POC Success Criteria:**
- 3+ consecutive successful executions per scraper
- No blocking or CAPTCHA during testing
- Accurate data extraction validated
- Execution time under 5 minutes per source
- Anti-bot measures prove effective

**Phase 1 - Infrastructure (Week 1-2)**
1. Create project structure (src/, requirements.txt, .env.example)
2. Set up Supabase project and tables
3. Create .env local (SUPABASE_URL, SUPABASE_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
4. Create Task Scheduler task (07:00 BRT, -WakeToRun, independente de bateria) — Variante A, Decisão 12

**Phase 2 - Telegram Setup (Week 2)**
1. Create Telegram bot via BotFather
2. Configure and test TELEGRAM_CHAT_ID
3. Implement basic message sending
4. Test message formatting with sample data

**Phase 3 - RSS Module (Week 2-3)**
1. Implement feed readers for four sources
2. Implement keyword filter (C6/Átomos + promo terms)
3. Implement database deduplication
4. Test "no promotions found" message

**Phase 4 - Google Flights (Week 3-4)**
1. Implement Playwright scraper for GRU, VCP
2. Implement 30h duration filter
3. Implement lowest price selection
4. Test persistence and error states

**Phase 5 - Smiles (Week 4-5)**
1. Implement Playwright navigation and response interception
2. Implement validation and normalization
3. Implement miles-only and Smiles & Money selection
4. Test error states (blocked, timeout, parse error, no availability)

**Phase 6 - Azul (Week 5-6)**
1. Implement Playwright portal navigation
2. Implement validation and normalization
3. Implement points-only and Points + Money selection
4. Test error states

**Phase 7 - Orchestration (Week 6)**
1. Implement daily_execution creation and tracking
2. Implement parallel source execution with error isolation
3. Implement Telegram message composition from all results
4. End-to-end integration testing

**Phase 8 - Automation (Week 6)**
1. Registrar Task Scheduler task (07:00 BRT, -WakeToRun, AllowStartIfOnBatteries) — Variante A
2. Testar disparo agendado (inclui acordar do repouso)
3. Monitor first daily executions

**Rollback Strategy:**
- **POC Gate:** Full implementation only proceeds after successful POC validation
- If GitHub Actions fails: Can run manually via local Python execution
- If Telegram fails: Data is still persisted; can retry notification
- If a scraper fails: Other sources continue; report indicates failure
- If Supabase fails: Logs capture data; can investigate when service restored
- If GitHub Actions fails: Can run manually via local Python execution
- If Telegram fails: Data is still persisted; can retry notification
- If a scraper fails: Other sources continue; report indicates failure
- If Supabase fails: Logs capture data; can investigate when service restored

## Open Questions

1. **Playwright Stealth durability:** How long will Stealth be effective against anti-bot detection? → Monitor and be prepared to switch strategies.

2. **Smiles API stability:** Will the internal API endpoint remain stable? → Designed to adapt; endpoint is not hard dependency.

3. **120k hybrid rule adequacy:** Is 120k miles the right threshold for MVP? → Placeholder value; can adjust based on observed redemption options.

4. **Calendar open date:** When will July/August 2027 calendars open for booking? → System will detect via CALENDAR_NOT_OPEN status.

5. **Future route expansion:** If MVP succeeds, what's the pattern for adding routes? → Schema supports parameterization; scrapers already accept dynamic inputs.

6. **Data retention:** How long should historical data be kept? → Not specified for MVP; Supabase free tier allows indefinite retention within 500MB.

7. **Multi-user support:** Could this serve multiple users with different routes? → Architecture supports it; requires user/route configuration tables (post-MVP).

8. ~~**Self-hosted execution architecture (PROPOSED 2026-09-02, decisão pendente)**~~ → **RESOLVIDA 2026-09-02: Variante A aprovada pelo usuário** ("vamos seguir para a construção da aplicação no modelo variante A"). Ver Decisão 12.

## Future Evolution (post-MVP)

- **Scraper autoreparável com IA:** quando uma fonte mudar o HTML e o scraper retornar `PARSER_ERROR`, passo opcional envia o HTML novo ao Claude para propor seletores atualizados (diff revisável). Transforma quebra de scraper de debug manual em revisão de sugestão.
- **Interpretação de promoções com LLM:** substituir filtro por palavra-chave do RSS por classificação/sumarização com LLM (custo de API — avaliar free tiers).
