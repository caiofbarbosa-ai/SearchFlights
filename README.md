# Flight Monitor MVP

Monitor diário automatizado de preços **São Paulo (GRU/VCP) → Bangkok (BKK)**
para 2 adultos (21 → 28/07/2027), cobrindo **dinheiro** (Google Flights),
**milhas Smiles**, **pontos Azul Fidelidade** e **promoções** (RSS), com
relatório consolidado no Telegram e histórico no Supabase.

Custo operacional: **R$ 0**. Execução: **self-hosted no seu notebook**
(Variante A — Decisão 12 do design), porque Smiles/Azul são protegidos por
Akamai, que só aceita browser real em IP residencial.

## Arquitetura

```
Task Scheduler (10:00 BRT, acorda do repouso)
  └─ python -m src.main
       ├─ RSS C6/Átomos ....... feedparser (sem browser)
       ├─ Google Flights ...... Playwright + URL q= (hl/gl/curr fixados)
       ├─ Smiles .............. Chrome real + CDP (URL direta /mfe/emissao-passagem)
       ├─ Azul ................ Chrome real + CDP (azulpelomundo.voeazul.com.br)
       ├─ Supabase ............ daily_executions / daily_flight_quotes / daily_promotions
       └─ Telegram ............ relatório consolidado (idempotente por dia)
```

- **Smiles/Azul**: o scraper lança um **Chrome real com perfil temporário
  descartável** (não o seu perfil) e conecta via CDP — é o único padrão que o
  Akamai aceita. As janelas do Chrome aparecem na tela por alguns minutos.
- **Smiles rate-limit**: 1 busca/origem/dia (rajadas voltam com lista vazia).
- **Smiles & Money**: além do só-milhas, o monitor busca o combo milhas+dinheiro
  (≤210k milhas) no painel "Selecionar tarifa" — quando o painel renderiza.
- **Datas-alvo fora da janela**: Google responde `CALENDAR_NOT_OPEN`/`NO_AVAILABILITY`
  (mensagem explícita); Smiles mantém spinner (classificado por timeout);
  Azul responde "não há voos disponíveis".

## Setup (uma vez)

1. **Python 3.12+** e **Google Chrome** instalados
2. `pip install -r requirements.txt` e `python -m playwright install chromium`
3. **Supabase**: crie o projeto → SQL Editor → execute `supabase_schema.sql`
4. **Telegram**: crie bot no BotFather → mande `/start` para ele → preencha o
   token no `.env` → o chat_id é extraído via `getUpdates` (ver seção abaixo)
5. `copy .env.example .env` e preencha `SUPABASE_URL`, `SUPABASE_KEY`,
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (e `RSS_FEEDS` se quiser promoções)

## Uso

```powershell
python -m src.main                    # execução completa (todas as fontes)
python -m src.main --only google      # uma fonte (testes)
python -m src.main --no-telegram      # sem notificação

# Agendamento (PowerShell como Administrador, uma vez):
powershell -ExecutionPolicy Bypass -File scripts\setup_task.ps1
Start-ScheduledTask -TaskName "FlightMonitor Daily"   # teste manual
```

Requisitos do notebook: **na tomada** ("Allow wake timers" =
Enabled no plano de energia) — a tarefa acorda o computador do repouso.
Dia sem execução = ponto faltante no histórico (aceitável para monitoramento).

## Estados por fonte

| Status | Significado | Ação |
|---|---|---|
| `SUCCESS` | preços/milhas extraídos | — |
| `NO_AVAILABILITY` | busca válida, sem opções (ex.: CGH→BKK não tem award interline) | nenhuma |
| `CALENDAR_NOT_OPEN` | datas-alvo fora da janela de reservas (~11 meses) | monitorar; reabre sozinho |
| `BLOCKED` | CAPTCHA/bloqueio anti-bot | investigar IP/fingerprint |
| `TIMEOUT` | página não respondeu no prazo | retry manual |
| `PARSER_ERROR` | página mudou (seletores quebrados) | atualizar seletores |
| `UNKNOWN_ERROR` | exceção não tratada | ver `logs/YYYY-MM-DD.log` |

Regra: **execução sem exceção não é sucesso** — só há `SUCCESS` com dados reais
extraídos (critério da POC de 2026-09-02).

## Troubleshooting

- **`Chrome não encontrado`** → instale o Chrome ou defina `CHROME_PATH` no `.env`
- **Smiles sempre vazio** → rate-limit por IP; espere e rode 1×/dia (nunca em rajada)
- **Azul/Smiles `BLOCKED` persistente** → confirme que roda no notebook (não em VM/nuvem)
- **Telegram `chat not found`** → mande `/start` ao bot e confira o `TELEGRAM_CHAT_ID`
- **Supabase `row-level security`** → rode `supabase_schema.sql` completo (ele cria as políticas)
- **Logs**: `logs/YYYY-MM-DD.log`

## Evidências da POC (2026-09-02)

- `poc/reports/google_flights_poc_validation_results_2026-09-02.md` — gate 9/9
- `poc/reports/smiles_poc_findings_2026-09-02.md` — corrida anti-Akamai + CDP
- `poc/reports/azul_poc_findings_2026-09-02.md` — award interline + Points+Money
