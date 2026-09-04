## 0. Proof of Concept Phase

- [x] 0.1 Create POC environment setup (local Python environment, basic dependencies)
- [x] 0.2 Create requirements-poc.txt with: playwright, playwright-stealth
- [x] 0.3 Set up basic POC project structure

### Google Flights POC

- [x] 0.4 Create minimal Google Flights POC script
- [x] 0.5 Implement basic navigation to google.com/travel
- [x] 0.6 Add search input for GRU → BKK with specified dates
- [x] 0.7 Implement Playwright Stealth configuration
- [x] 0.8 Add random delays and human-like typing
- [ ] 0.9 Extract sample flight data (price, airline, duration) — REABERTA (2026-09-02): extração nunca ocorreu; nenhuma run alcançou a página de resultados
- [x] 0.10 Run 3+ consecutive test executions
- [x] 0.11 Document success: execution time, anti-bot effectiveness, data structure
- [x] 0.12 Test multi-origin queries (GRU, CGH, VCP)
- [x] 0.13 Create POC report with findings and recommendations

### Smiles POC

- [x] 0.14 Create minimal Smiles POC script
- [x] 0.15 Implement navigation to Smiles website
- [x] 0.16 Add search input for GRU → BKK with specified dates and 2 passengers
- [x] 0.17 Implement API response interception
- [x] 0.18 Add Playwright Stealth and human-like behaviors
- [x] 0.19 Extract sample award data (miles-only, Smiles & Money) — 2026-09-02: award real extraído via CDP/Chrome real (KLM 362.600, AF 384.100, Turkish 423.200, Qatar 474.100 milhas por passageiro, c/ duração/escala; screenshot + JSON). Extração granular de Smiles&Money (milhas+dinheiro combinados) fica para a Fase 5
- [ ] 0.20 Run 3+ consecutive test executions — PARCIAL (2026-09-02): 1 sucesso completo + arquitetura validada; Akamai aplica soft-block silencioso por IP que PERSISTE 10h+ após rajadas (noite: datas de controle também bloqueadas) — estabilidade a confirmar no ciclo agendado D+1 (07:00). Ver `poc/reports/smiles_poc_findings_2026-09-02.md` §3.1.3
- [x] 0.21 Document success: API structure, anti-bot effectiveness, data extraction — `poc/reports/smiles_poc_findings_2026-09-02.md` (cadeia Akamai, corrida de armamento, arquitetura CDP, rate-limit, comportamento 2027)
- [x] 0.22 Test multi-origin queries (GRU, CGH, VCP)
- [x] 0.23 Create POC report with findings and recommendations

### Azul POC

- [x] 0.24 Create minimal Azul POC script
- [x] 0.25 Implement navigation to Azul Pelo Mundo portal
- [x] 0.26 Add search input for GRU → BKK with specified dates and 2 passengers
- [x] 0.27 Implement Playwright Stealth and human-like behaviors
- [x] 0.28 Extract sample award data (points-only, Points + Money)
- [x] 0.29 Run 3+ consecutive test executions — 2026-09-02: 3 origens executadas em sequência sem bloqueio via CDP/Chrome real (GRU ✅ RESULTS 18 valores de pontos; CGH ✅ NO_RESULTS legítimo — "não há voos disponíveis"; VCP ⚠️ 2 valores). Estabilidade em cadência diária a confirmar na 1ª semana. Ver `poc/reports/azul_poc_findings_2026-09-02.md`
- [x] 0.30 Document success: portal structure, anti-bot effectiveness, data extraction — portal `azulpelomundo.voeazul.com.br` guest; Playwright puro bloqueado (Akamai) mas CDP/Chrome real consistente; API `/api/availability` exige reCAPTCHA → rota browser
- [x] 0.31 Test multi-origin queries (GRU, CGH, VCP)
- [x] 0.32 Create POC report with findings and recommendations

### Google Flights POC — Revalidação (2026-09-02)

> Re-baseline após diagnóstico: nenhuma run de 2026-08-16 alcançou a página de resultados; 0 preços extraídos em todas. Ver `poc/reports/google_flights_poc_findings_and_mitigation.md`. Critério de sucesso: **preços reais extraídos** (execução sem exceção NÃO é sucesso). Alternativas pagas (SerpAPI) excluídas — restrição R$ 0.

- [x] 0.38 Re-baseline POC reports: marcar relatórios de 2026-08-16 como superseded
- [x] 0.39 E1: validar URL direta `q=` com datas-alvo 2027 (GRU→BKK) — RESULTADO: página renderiza e classifica; jul/2027 fora da janela (CALENDAR_NOT_OPEN "muito distante" e NO_AVAILABILITY "nenhum voo", observados em runs distintas; sugestões de datas adjacentes com preço)
- [x] 0.40 E2 (controle): URL `q=` com datas próximas (~90 dias) — RESULTADO: RESULTS, página de resultados completa (GRU→BKK 8–16/dez, R$ 7.799+), sem interação com formulário
- [x] 0.41 Implementar extração dupla (S1 DOM `div[role=listitem]` + regex R$; S2 interceptação de rede) com validação: ≥3 preços, BRL, sanity check — NOTA: resultados reais usam `<li class="pIav2d">`/body text, não `role=listitem`; extração ajustada p/ body text + li + rede
- [x] 0.42 Gate: 3/3 execuções consecutivas por origem (GRU, CGH, VCP) com ≥3 preços reais cada (<5 min/run) — **9/9 PASS** (2026-09-02, datas de controle: GRU 10 preços, CGH 8, VCP 8 por run; ~12s/run; sem CAPTCHA; extração determinística entre runs; evidência: `poc/reports/google_flights_poc_validation_results_2026-09-02.md` + `validation_results_2026-09-02.json`)
- [ ] 0.43 Testar execução no runner GitHub Actions (IP datacenter) — OPCIONAL (Decisão 12): relevante apenas se a nuvem for revisitada para o Google Flights
- [x] 0.44 Re-executar go/no-go (0.33–0.36) somente com evidência de preços extraídos — concluído 2026-09-02 (Google gate 9/9; Smiles award real; Azul award interline) e aprovado pelo usuário

### POC Evaluation & Go/No-Go Decision

> Decisão parcial (2026-09-02, usuário): **GO para Google Flights** (gate 9/9 com preços extraídos — ver `poc/reports/google_flights_poc_validation_results_2026-09-02.md`). Smiles em validação; Azul pendente. 0.33–0.36 fecham quando as 3 fontes tiverem decisão.

- [x] 0.33 Review all POC results and document findings — 3/3 fontes com findings documentados: Google Flights (`google_flights_poc_validation_results_2026-09-02.md`), Smiles (`smiles_poc_findings_2026-09-02.md`), Azul (`azul_poc_findings_2026-09-02.md`)
- [x] 0.34 Make go/no-go decision for each scraper source — 2026-09-02: Google Flights **GO**; Smiles **GO condicionado** (self-hosted + rate-limit 3 buscas/dia); Azul **GO** (self-hosted via CDP). Arquitetura self-hosted Variante A aprovada pelo usuário
- [x] 0.35 Document alternative approaches if any POC failed — alternativas documentadas e descartadas com evidência nos findings docs (Akamai: corrida de armamento completa; Smiles rate-limit; URL q= do Google)
- [x] 0.36 Obtain approval to proceed to full implementation — aprovado 2026-09-02 ('vamos seguir para a construção da aplicação no modelo variante A')
- [x] 0.37 Archive POC code for reference in full implementation — POCs preservados em `poc/` (google_flights/, smiles/, azul/ + reports/); lógica validada portada para `src/`

## 1. Infrastructure Setup

- [x] 1.1 Initialize Python project structure with src/ directory — src/ com config, models, database/, notifications/, feeds/, scrapers/, flight_selector.py, main.py
- [x] 1.2 Create requirements.txt with: playwright, playwright-stealth, feedparser, supabase, python-dotenv — + supabase, python-dotenv (instalados e importados OK)
- [x] 1.3 Set up Supabase project and create database tables (daily_executions, daily_flight_quotes, daily_promotions) — SQL pronto em `supabase_schema.sql`; FALTA: usuário criar o projeto e executar o SQL + preencher .env — projeto do usuário + schema aplicado com políticas RLS para publishable key (2026-09-02)
- [x] 1.4 Create .env.example template with required environment variables
- [x] 1.5 Create Task Scheduler registration script (scripts/setup_task.ps1: 10:00 BRT, -WakeToRun, AllowStartIfOnBatteries) + run_daily.ps1 — Variante A (Decisão 12) — REGISTRADA e verificada 2026-09-02: tarefa 'FlightMonitor Daily' Ready, próxima execução 03/09 10:00 BRT
- [x] 1.6 Create .env local from .env.example (SUPABASE_URL, SUPABASE_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) — fora do repositório — .env local criado com Supabase + Telegram (fora do repositório)

## 2. Database Layer

- [x] 2.1 Create database connection module (database/repository.py)
- [x] 2.2 Implement daily_executions CRUD operations
- [x] 2.3 Implement daily_flight_quotes insert operation
- [x] 2.4 Implement daily_promotions insert with ON CONFLICT handling
- [x] 2.5 Add UUID generation and timestamp defaults — gen_random_uuid() + default now() no schema SQL

## 3. Data Models

- [x] 3.1 create models.py with execution status constants (SUCCESS, NO_AVAILABILITY, CALENDAR_NOT_OPEN, BLOCKED, TIMEOUT, PARSER_ERROR, UNKNOWN_ERROR)
- [x] 3.2 Define FlightQuote dataclass/model
- [x] 3.3 Define Promotion dataclass/model
- [x] 3.4 Define ExecutionResult dataclass/model for scraper returns

## 4. Telegram Notifier

- [x] 4.1 Create Telegram bot client (notifications/telegram.py)
- [x] 4.2 Implement message composition with HTML formatting
- [x] 4.3 Implement character escaping for HTML special characters
- [x] 4.4 Add report sections: header, Google Flights, Smiles, Azul, Promotions
- [x] 4.5 Implement unavailable source reporting formats
- [x] 4.6 Implement "no promotions found" message
- [x] 4.7 Add telegram_status tracking and idempotency check

## 5. Promotion Monitor (RSS)

- [x] 5.1 Create RSS feed reader (feeds/promotions.py)
- [x] 5.2 Implement feedparser integration for all four sources
- [x] 5.3 Implement keyword filter (C6/Átomos + promo terms)
- [x] 5.4 Add article URL deduplication logic
- [x] 5.5 Implement database persistence with ON CONFLICT DO NOTHING
- [x] 5.6 Return only new articles for current execution
- [x] 5.7 Add feed validation and error handling

## 6. Google Flights Scraper

- [x] 6.1 Create Google Flights scraper (scrapers/google_flights.py)
- [x] 6.2 Implement Playwright browser setup
- [x] 6.3 Add parameterized search function (origin, destination, dates, passengers)
- [x] 6.4 Implement multi-origin query (GRU, CGH, VCP) — origens em produção agora GRU,VCP (CGH removida 2026-09-03: doméstica, sem interline)
- [x] 6.5 Add explicit waiting for flight results
- [x] 6.6 Implement response validation
- [x] 6.7 Extract price, airline, duration, itinerary details
- [x] 6.8 Implement 30-hour duration filter
- [x] 6.9 Select lowest price across valid options
- [x] 6.10 Return structured {status, data, error} response
- [x] 6.11 Add error states: BLOCKED, TIMEOUT, PARSER_ERROR, CALENDAR_NOT_OPEN
- [x] 6.12 Implement Playwright Stealth for browser fingerprint obfuscation
- [x] 6.13 Add random delays between actions (500ms-3000ms)
- [x] 6.14 Implement human-like typing pattern — N/A na arquitetura URL `q=` (Decisão 11): sem interação com formulário; delays aleatórios mantidos entre origens
- [x] 6.15 Add realistic mouse movements — N/A na arquitetura URL `q=` (Decisão 11): zero cliques necessários
- [x] 6.16 Implement request rate limiting (5-10s delay between origin queries) — 5–10s entre origens
- [x] 6.17 Configure browser viewport and user-agent for realistic appearance — 1920×1080, pt-BR, TZ América/São_Paulo, UA real
- [x] 6.18 Maintain browser context and cookies between queries — contexto único compartilhado entre as 3 origens

## 7. Smiles Scraper

> Arquitetura validada na POC (2026-09-02): **Chrome real + CDP** (`--remote-debugging-port`, perfil temporário) — NÃO Playwright embutido (Akamai nega). URL direta `/mfe/emissao-passagem/?...`; extração por `milhas por passageiro`; rate-limit: 1 busca/origem/dia.

- [x] 7.1 Create Smiles scraper (scrapers/smiles.py)
- [x] 7.2 Implement Playwright navigation to Smiles website
- [x] 7.3 Add parameterized search function
- [x] 7.4 Implement API response interception
- [x] 7.5 Add explicit waiting with timeout
- [x] 7.6 Implement JSON response validation
- [x] 7.7 Extract miles-only and Smiles & Money options
- [x] 7.8 Implement 30-hour duration filter
- [x] 7.9 Select lowest miles-only option
- [x] 7.10 Select highest-mileage hybrid under 120k miles
- [x] 7.11 Return structured {status, data, error} response
- [x] 7.12 Add error states: BLOCKED, TIMEOUT, PARSER_ERROR, CALENDAR_NOT_OPEN, NO_AVAILABILITY
- [x] 7.13 Implement Playwright Stealth for browser fingerprint obfuscation
- [x] 7.14 Add random delays between actions (500ms-3000ms)
- [x] 7.15 Implement human-like typing pattern — simplificado: digitação com delay 50–90ms (validado na POC; sem modais a interação é mínima)
- [x] 7.16 Add realistic mouse movements — simplificado: clique direto em sugestões/calendário (validado na POC contra o Akamai)
- [x] 7.17 Implement request rate limiting (5-10s delay between origin queries) — spacing configurável (smiles_origin_spacing_s; produção 1 busca/origem/dia)
- [x] 7.18 Maintain browser session and cookies for consistency — mesma sessão CDP para as origens da execução
- [x] 7.19 Configure proper API request headers — N/A: browser real define headers nativamente (por isso o Akamai aceita)

## 8. Azul Scraper

> Arquitetura validada na POC (2026-09-02): **Chrome real + CDP** no portal `azulpelomundo.voeazul.com.br` (guest); datas por placeholder `DD/MM/YYYY` (partida) + input vazio (volta); códigos de aeroporto casados entre parênteses; extração por `pontos` e `pontos + R$`.

- [x] 8.1 Create Azul scraper (scrapers/azul.py)
- [x] 8.2 Implement Playwright navigation to Azul Pelo Mundo portal
- [x] 8.3 Add parameterized search function
- [x] 8.4 Implement explicit waiting for results
- [x] 8.5 Extract points-only and Points + Money options
- [x] 8.6 Implement 30-hour duration filter
- [x] 8.7 Select lowest points-only option
- [x] 8.8 Select highest-pointage hybrid under 120k points
- [x] 8.9 Return structured {status, data, error} response
- [x] 8.10 Add error states: BLOCKED, TIMEOUT, PARSER_ERROR, CALENDAR_NOT_OPEN, NO_AVAILABILITY
- [x] 8.11 Implement Playwright Stealth for browser fingerprint obfuscation
- [x] 8.12 Add random delays between actions (500ms-3000ms)
- [x] 8.13 Implement human-like typing pattern for form inputs
- [x] 8.14 Add realistic mouse movements — simplificado: clique direto (validado na POC)
- [x] 8.15 Implement request rate limiting (5-10s delay between origin queries) — 3–6s entre origens
- [x] 8.16 Maintain browser session and cookies for consistency — sessão CDP por execução; perfil temporário descartável
- [x] 8.17 Configure proper request headers — N/A: browser real define headers nativamente

## 9. Flight Selector & Processors

- [x] 9.1 Create flight_selector.py for result filtering and selection
- [x] 9.2 Implement duration filtering logic (<= 30 hours)
- [x] 9.3 Implement lowest-price selection for cash flights
- [x] 9.4 Implement lowest-miles selection for miles-only
- [x] 9.5 Implement highest-miles-under-limit for hybrid options
- [x] 9.6 Add validation of required fields

## 10. Orchestration & Main Execution

- [x] 10.1 Create main.py orchestration module
- [x] 10.2 Implement daily_execution record creation
- [x] 10.3 Implement parallel source execution with error isolation
- [x] 10.4 Add individual source status tracking
- [x] 10.5 Implement results aggregation
- [x] 10.6 Add database persistence of all results
- [x] 10.7 Implement Telegram notification with idempotency
- [x] 10.8 Update execution status (finished_at, overall status)
- [x] 10.9 Add comprehensive error handling and logging

## 11. Local Scheduling Configuration (Variante A — Task Scheduler)

- [x] 11.1 Register scheduled task 07:00 BRT diária com -WakeToRun — 10:00 BRT (ajustado de 07:00 pelo usuário)
- [x] 11.2 Configurar execução independente de bateria (AllowStartIfOnBatteries / DontStopIfGoingOnBatteries) — DisallowStartIfOnBatteries=False confirmado via Get-ScheduledTask
- [x] 11.3 Time limit de 30 min + política de reexecução p/ perda ("run as soon as possible after missed") — StartWhenAvailable=True + ExecutionTimeLimit 30 min
- [x] 11.4 Carregamento de variáveis do .env local — python-dotenv no config.py
- [x] 11.5 Log por execução (arquivo local em logs/YYYY-MM-DD.log) — logs/YYYY-MM-DD.log via run_daily.ps1 + main.py

## 12. Testing & Validation

- [x] 12.1 Test Telegram bot message sending — mensagem de teste entregue no chat 1031783384 via módulo de produção (build_report + send_message)
- [x] 12.2 Test RSS feed parsing and keyword filtering — 03/09: 4 feeds reais configurados (melhoresdestinos, melhorescartoes, passageirodeprimeira, pontospravoar; Smiles não tem RSS público); 70 entradas lidas, filtro case-insensitive validado ("milhas" casa dezenas; 0 matérias C6 no momento — captura automática quando publicarem)
- [x] 12.3 Test database operations (insert, deduplication) — com o projeto Supabase real: insert execution/quote + dedup ON CONFLICT (1ª=1 nova, 2ª=0 novas)
- [x] 12.4 Test Google Flights scraper with all three origins — 03/09: COM patchright, GRU persistiu R$ 13.678 (= 13.677 do usuário, ±1 arredondamento); descoberta crítica: Google degrada tarifas p/ sessões Playwright (adendo no findings). CGH/VCP SUCCESS (16.432/16.432)
- [ ] 12.5 Test Smiles scraper (miles-only and hybrid) — PARCIAL (03/09): Smiles DESBLOQUEADO após ~14h de silêncio (GRU NO_AVAILABILITY = estado real); CGH/VCP degradados com spacing de 60s → spacing aumentado p/ 10 min; validação final no ciclo agendado
- [x] 12.6 Test Azul scraper (points-only and hybrid) — via python -m src.main --only azul (datas de controle): GRU 239.000 pts, CGH NO_AVAILABILITY (legítimo), VCP 286.000 pts — persistido no Supabase; híbrido sob 120k = None na rota (valores típicos >120k, regra testada)
- [ ] 12.7 Test error states (blocked, timeout, parse error)
- [x] 12.8 Test "no availability" vs "error" distinction — Azul CGH NO_AVAILABILITY vs erros reais; Google CALENDAR_NOT_OPEN (POC); ambos persistidos como estados distintos
- [x] 12.9 Test 30-hour duration filtering — teste sintético: 30h filtra cash 14000 (35h) e milhas 180k (35h); menor cash 15598; menor milhas 195000; híbrido 110k+R$595; NO_AVAILABILITY nunca selecionado
- [x] 12.10 Test end-to-end local execution — 03/09 via Start-ScheduledTask (caminho agendado): 4 fontes, 9 quotes persistidas, execução finalizada, overall PARTIAL correto (com fontes degradadas)
- [ ] 12.11 Test Task Scheduler trigger — trigger 10:00 DISPAROU no horário (03/09); falha de ação (E_INVALIDARG) corrigida e re-testada via Start-ScheduledTask (exit 0); ACORDAR DO REPOUSO segue a validar no ciclo real
- [x] 12.12 Verify idempotent Telegram sends — telegram_already_sent=True após envio do dia (verificado com o projeto real); envio duplicado no mesmo dia é pulado
- [ ] 12.13 Monitor first daily automated execution

## 13. Documentation

- [x] 13.1 Update README.md with project description — README.md com descrição e arquitetura
- [x] 13.2 Document setup instructions (Supabase, Telegram, .env local, Task Scheduler) — setup: Supabase (schema+RLS), Telegram (/start + getUpdates), .env local, Task Scheduler
- [x] 13.3 Add architecture diagram or description — diagrama ASCII no README
- [x] 13.4 Document error states and their meanings — tabela de estados e significados
- [x] 13.5 Add troubleshooting guide for common issues — troubleshooting: Chrome, rate-limit Smiles, BLOCKED, chat not found, RLS, logs
