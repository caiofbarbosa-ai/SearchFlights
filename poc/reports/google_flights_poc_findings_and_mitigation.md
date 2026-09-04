# Google Flights POC — Diagnóstico Real & Caminho de Mitigação

**Data:** 2026-09-02
**Status:** ⚠️ RE-BASELINE — este documento **substitui** as conclusões de `google_flights_poc_final_report.md` e `poc_evaluation_summary.md` (2026-08-16)
**Critério de sucesso (inalterável):** um run só é "SUCCESS" se **preços reais forem corretamente extraídos**. Execução sem exceção não é sucesso.

---

## 1. O que os artefatos realmente mostram (re-avaliação evidência por evidência)

Os relatórios de 2026-08-16 declararam "GO confirmado / 100% sucesso" medindo execução sem exceções. A re-avaliação dos screenshots finais mostra que **nenhuma run alcançou a página de resultados**:

```
                FUNIL REAL DO POC (9 arquivos de POC, 2026-08-16)
 ────────────────────────────────────────────────────────────────
  Navegar até a página ............ ✅ 9/9 runs
  Preencher origem ................ ✅ (fluxo UI)
  Preencher destino ............... ✅ (fluxo UI)   ❌ (URL direta)
  Selecionar datas ................ ❌ ← PONTO DE MORTE
  Executar busca .................. ❌
  Ver página de resultados ........ ❌ NUNCA ALCANÇADA
  Extrair preços .................. ❌ 0 preços em TODAS as runs
 ────────────────────────────────────────────────────────────────
```

### Evidência

| Artefato | O que mostra |
|---|---|
| `reports/validated_GRU_final.png` | Origem e destino preenchidos; data de ida **truncada** (`sáb., 22 de a` — e 28/07/2027 é quarta-feira, o dia nem corresponde); volta **vazia**; página exibida é a **home**, não resultados |
| `reports/robust_GRU_url_direta_results.png` | Destino `Para onde?` **vazio**, datas vazias, botão `Explorar` (não `Pesquisar`) — o Google rejeitou os parâmetros da URL e caiu de volta na home |
| `reports/validated_poc_results.json` | 3/3 runs com `status: NO_PRICES`, `prices_found: 0` |
| `reports/validated_*_html.html` | HTML da home, sem nenhum item de resultado |

### Consequências

1. **O código de extração de preços nunca foi testado contra uma página de resultados real** — toda a iteração (timeouts, seletores, stealth) aconteceu numa camada que nunca foi alcançada.
2. **A hipótese "janela de reservas 2027" nunca foi isolada** — todas as runs usaram julho/2027; "datas fora da janela" e "automação frágil" produzem o mesmo sintoma sem um experimento de controle.
3. O relatório formal do projeto ainda diz GO — **as tasks 0.33–0.37 (go/no-go) permanecem abertas** e a decisão deve ser refeita sobre evidência de extração real. A Fase 1+ não foi iniciada, então nada foi construído sobre a premissa falsa.

---

## 2. Decisões registradas (2026-09-02)

### D1 — SerpAPI e APIs pagas: REMOVIDAS das alternativas
A recomendação de 2026-08-16 de usar SerpAPI é **revogada**. Motivo: restrição arquitetural **R$ 0** (design.md Non-Goals: "Commercial API integrations"). O free tier da SerpAPI (~100 buscas/mês) mal cobriria 3 origens × 30 dias = 90 buscas, sem margem para retries. Avaliação de alternativas pós-POC fica restrita a abordagens de custo zero.

### D2 — Acesso ao Google Flights via URL direta `q=` como abordagem primária
Contorna inteiramente o ponto de morte do POC (calendário visual + modais):

```
https://www.google.com/travel/flights
  ?q=Flights%20from%20GRU%20to%20BKK%20on%202027-07-28%20through%202027-08-05
  &hl=pt-BR&gl=BR&curr=BRL
```

- `q=` aceita query textual; o Google parseia e navega **direto à página de resultados**
- `hl`/`gl`/`curr` fixam idioma (pt-BR), região (BR) e moeda (BRL) → página determinística, eliminando o problema de seletores em inglês vs. português
- Fallbacks, em ordem: (a) `tfs` protobuf (base64) na URL — codifica trip type, datas e **nº de passageiros** de forma confiável; (b) fluxo de UI com datas digitadas em formato pt-BR via eventos de teclado, verificando o conteúdo do campo antes de submeter

**Ressalva — passageiros:** a query textual pode não configurar 2 adultos (default 1). Prever ajuste pós-navegação (1 interação) via seletor de passageiros ou uso do `tfs`. A extração deve confirmar se o preço exibido é por passageiro ou total; a spec exige **total para 2 adultos** (`cash_price_brl`).

### D3 — Extração de preço com dupla estratégia independente
| Estratégia | Mecanismo | Resiliência |
|---|---|---|
| S1 — DOM | Aguardar `div[role="listitem"]`; extrair preços via regex `R\$\s?\d{1,3}(\.\d{3})*(,\d{2})?` sobre innerText/aria-label | Moderada (mudanças de DOM quebram) |
| S2 — Rede | `page.on("response")` filtrando payloads RPC (BatchExecute/shopping) e aplicando a mesma regex | Alta (imune a reestruturação de DOM) |

Validação mínima de cada run: ≥ 3 preços distintos, todos ≥ R$ 100 (sanity), moeda BRL, menor preço cruzado com busca manual do usuário.

### D4 — Anti-bot em IP de datacenter: risco arquitetural a testar cedo
Todo o POC validou execução **local** (IP residencial). O cron de produção planejado roda no **GitHub Actions (IP de datacenter)**, onde o Google é drasticamente mais agressivo com CAPTCHA. Risco de o scraper funcionar no PC e tomar bloqueio no primeiro run de produção.
**Mitigação (mantém R$ 0):** testar 1 execução no runner do GitHub Actions **antes** da Fase 4. Se bloquear: runner self-hosted no PC do usuário (IP residencial, gratuito) agendado via Task Scheduler, ou GitHub Actions apenas como orquestrador de notificação.

---

## 3. Plano de validação (matriz de decisão)

| # | Experimento | Condição de sucesso |
|---|---|---|
| E1 | URL `q=` com datas-alvo 2027 (GRU→BKK) | Página de resultados renderiza |
| E2 | URL `q=` com datas próximas (~90 dias) — controle | Página de resultados renderiza |

| E1 (2027) | E2 (próxima) | Diagnóstico | Ação |
|---|---|---|---|
| resultados | resultados | Abordagem OK; janela 2027 aberta | Gate completo nas 3 origens |
| vazio | resultados | Abordagem OK; janela 2027 **fechada** | Gate em datas próximas + detectar `CALENDAR_NOT_OPEN` para 2027 (status já previsto no design); monitoramento das datas-alvo inicia quando a janela abrir |
| vazio | vazio | `q=` rejeitado | Fallback (a) datas digitadas pt-BR no form → (b) `tfs` protobuf |
| CAPTCHA | CAPTCHA | Escalada anti-bot | Stealth/headed; se persistir → acionar mitigação D4 |

## 4. Gate de aceitação para re-executar o go/no-go

1. **3/3 execuções consecutivas por origem** (GRU, CGH, VCP), cada uma com **≥ 3 preços reais** extraídos em BRL, < 5 min/run
2. **OU** (janela 2027 fechada): 3/3 em datas próximas + `CALENDAR_NOT_OPEN` corretamente detectado para 2027
3. **Zero tolerância:** qualquer run com 0 preços = FALHA. Só há "GO" com evidência de extração (capturas de tela + JSON de preços)
4. Smiles e Azul permanecem PENDING (suas POCs nunca foram executadas) — go/no-go delas é separado

---

## 5. Impacto nos artefatos do projeto

| Artefato | Ação |
|---|---|
| `google_flights_poc_final_report.md` | Banner de SUPERSEDED apontando para este documento |
| `poc_evaluation_summary.md` | Banner de SUPERSEDED apontando para este documento |
| `openspec/.../tasks.md` | 0.9 desmarcado (extração nunca ocorreu); bloco 0.38–0.44 (revalidação) adicionado |
| `openspec/.../design.md` | Decisão 11 (acesso via `q=`); risco de datacenter IP; SerpAPI excluída explicitamente |
| `specs/google-flights-scraper` | Navegação via URL direta como primário; interação de form como fallback |
| `specs/proof-of-concept` | Avaliação de alternativas restrita a custo zero (SerpAPI excluída) |

---

*Re-baseline do POC Google Flights — 2026-09-02*
*Status: extração NUNCA validada; caminho de mitigação definido; go/no-go aguardando evidência de preços*
