# Google Flights POC — Resultados da Validação (2026-09-02)

**Status:** ✅ **VALIDADO — preços corretamente extraídos** (gate 9/9, critério do usuário cumprido)
**Script:** `poc/google_flights/poc_validation_2026_09_02.py` (URL `q=` + extração dupla)
**Dados brutos:** `poc/reports/validation_results_2026-09-02.json` (todos os runs acumulados)

---

## 1. Matriz de experimentos (E1/E2)

| Experimento | URL | Resultado |
|---|---|---|
| **E1** — datas-alvo 2027 | `q=Flights from GRU to BKK on 2027-07-28 through 2027-08-05` | Página renderiza e classifica corretamente: `CALENDAR_NOT_OPEN` ("A data de voo solicitada está muito distante") ou `NO_AVAILABILITY` ("Não há nenhum voo para sua pesquisa") — **ambos os sub-estados observados em runs distintas**; painel "Use datas diferentes" oferece datas adjacentes com preço (28–29/jul a partir de R$ 8.786) |
| **E2** — controle (8–16/12/2026) | mesma estrutura, datas próximas | ✅ `RESULTS` — página completa de resultados: "Principais voos de ida" + "Outros voos de ida", R$ 7.799–23.793, ida e volta |

**Conclusão da matriz:** a abordagem `q=` funciona; **a janela de reservas para jul/2027 está fechada hoje** (~11 meses antes). O monitoramento das datas-alvo começa quando o Google abrir o calendário; até lá o sistema reporta `CALENDAR_NOT_OPEN` (status já previsto no design).

## 2. Gate de aceitação — 9/9 PASS

3 execuções consecutivas por origem, datas de controle (8→16/12/2026), critério: ≥3 preços reais em BRL por run, <5 min/run.

| Origem | Runs | Preços DOM/run | Min (R$) | Tempo/run | CAPTCHA/Bloqueio |
|---|---|---|---|---|---|
| GRU | 3/3 ✓ | 10 | 7.799 | ~12,2s | Nenhum |
| CGH | 3/3 ✓ | 8 | 3.843 | ~11,1s | Nenhum |
| VCP | 3/3 ✓ | 8 | 7.799 | ~12,4s | Nenhum |

- **Determinismo:** min/max idênticos entre as 3 runs de cada origem → extração correta e estável
- **Cross-check visual:** menor preço GRU (R$ 7.799) confere com o screenshot da página ("a partir de R$ 7.799", Qatar Airways)
- **Velocidade:** ~12s/run vs. ~120s do POC antigo; ciclo completo de 3 origens ≈ 2,5 min

## 3. O que foi aprendido sobre a página (para a Fase 4)

| Descoberta | Implicação |
|---|---|
| Resultados renderizam como `<li class="pIav2d">` (28–32 por página) — **não existem `div[role="listitem"]`** | Seletores por `role` genérico falham; usar body text + `li` com regex de preço (resiliente a troca de classe) |
| `hl=pt-BR&gl=BR&curr=BRL` na URL fixa idioma/moeda | Página determinística; mata o problema de seletores bilingual do POC antigo |
| Estados sem-voos têm texto próprio: "muito distante" (janela) e "nenhum voo para sua pesquisa" (com sugestões de datas alternativas **com preço**) | Classificar esses estados ANTES de extrair preços, senão sugestões viram falso-positivo (bug corrigido no validador) |
| Captura de rede (S2) confirma preços independentemente do DOM (3–12 preços/run) | Estratégia de fallback viável para quando o Google mudar o DOM |
| "Os preços incluem os tributos e tarifas obrigatórios **para 1 adulto**" | Query `q=` default 1 adulto. Produção (2 adultos): ajustar seletor de passageiros pós-navegação, usar `tfs` protobuf, ou multiplicar — **decidir na Fase 4** |

## 4. Evidências

- Screenshots: `validation_E1_2027_GRU.png`, `validation_E2_controle_GRU.png`, `validation_gate_r{1..3}_{GRU,CGH,VCP}.png`
- HTML: `validation_*.html`
- JSON: `validation_results_2026-09-02.json` — **15 runs acumuladas** (6 de experimentos, incluindo as iterações do classificador, + 9 do gate); os screenshots/HTML refletem o run mais recente de cada label

## 5. Pendências (go/no-go final)

1. **Task 0.43 — risco datacenter IP:** testar 1 execução no runner do GitHub Actions **antes** da Fase 4. É o único risco aberto da arquitetura (todo o sucesso acima é IP residencial local).
2. **Tasks 0.33–0.36 — go/no-go formal:** com o gate 9/9, o Google Flights está APTO. Decisão e aprovação: do usuário.
3. Smiles e Azul: POCs **nunca executadas** — go/no-go separado, não bloqueia o Google Flights.

---

*Validação executada em 2026-09-02, IP residencial local, headless=False, viewport 1920×1080, pt-BR/BRL.*

---

# ADENDO 2026-09-03: tarifa degradada para sessões automatizadas (CRÍTICO)

O usuário validou o scraper contra o Google manualmente e encontrou **R$ 13.677 total (2 adultos)** onde o scraper persistia **R$ 16.432**. Cadeia de investigação (todos os passos com evidência em `poc/google_flights/probe_*.py`):

| Hipótese | Teste | Veredito |
|---|---|---|
| Cidade vs aeroporto específico | cidade = GRU = 8.216/pax | ❌ |
| Formato q= vs tfs canônico | tfs do usuário automatizado = 8.216/pax | ❌ |
| Nº de passageiros (1 vs 2) | usuário c/ 1 adulto = 6.839 | ❌ |
| Login/sessão | outro notebook anônimo = 6.839 | ❌ |
| Timing (tarifa carrega em ondas) | usuário viu 8.239→7.505→6.839; janela de 90s na automação não recebeu ondas | parcial |
| **Detecção de automação pelo Google** | **patchright (CDP-leaks corrigidos) + Chrome real → 8.216→6.839** | ✅ **CAUSA RAIZ** |

**Mecanismo:** o Google detecta Playwright padrão (vazamentos de CDP) e serve **apenas a primeira onda de tarifas** (piso inflado, R$ 8.216/pax). O usuário observou a carga progressiva na própria tela: 8.239 → 7.505 → 6.839. Com **patchright** (fork do Playwright com vazamentos corrigidos) + Chrome real, as ondas chegam e o piso real (6.839) é capturado.

**Correções aplicadas ao scraper de produção:**
1. `patchright` + `channel="chrome"` substitui Playwright+stealth
2. Rastreamento de MÍNIMO em janela fixa de 90s (a tarifa chega em ondas; extrair na 1ª infla o preço)
3. Rotas finas (ex.: VCP→BKK, 1-2 opções): SUCCESS = shell de resultados + ≥1 preço (exigir 3+ classificava errado)
4. Grounding: GRU persistiu **R$ 13.678** (= 13.677 do usuário + arredondamento de 1 real em 6.839×2)

**Implicação histórica:** quotes anteriores a 03/09 têm viés de ALTA (primeira onda). O monitor diário com a correção captura o piso real — que é exatamente o propósito do projeto.

**Smiles (mesma sessão de testes):** soft-block do Akamai persiste 10h+ após rajadas; estado "shell sem spinner e sem resultados" = `BLOCKED` (classificador corrigido).
