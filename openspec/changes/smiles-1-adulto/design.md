# Design: smiles-1-adulto

## Context

Auditoria da evidência do projeto (09-02 a 09-09):

| Observação | Datas | Adultos | Cliente | Resultado |
|---|---|---|---|---|
| Print manual (`smiles_julho.png`) | jul/27 | **1** | Chrome humano | ✅ renderiza |
| POC CDP 09-02 (`smiles_cdp_real.png`) | dez/26 | **1** | patchright CDP | ✅ renderiza ~45s |
| Validação 05-09 (`smiles.png`, URL `adults=1`) | dez/26 | **1** | CDP | ✅ renderiza |
| Gate CDP 09-02 (`smiles_gate_cdp_results.json`) | dez/26 | **2** | CDP | ❌ spinner |
| Gate CDP 09-02 | jul/27 | **2** | CDP | ❌ spinner |
| Produção 04-08/09 | jul/27 | **2** | CDP | ❌ spinner |
| Probe neutro (`july_neutral_net.json`) | jul/27 | **2** | playwright+stealth | ❌ XHR de disponibilidade nunca completa |

Matriz 2×2 completa: 1 adulto renderiza em qualquer data; 2 adultos nunca renderizou. A codificação de data está descartada (`epoch_ms_brt(2027-07-21) == 1816138800000`, idêntico à URL manual). A hipótese "flag Akamai" para as falhas de julho não é sustentável: 06/09 com flag medidamente clearado ainda falhou — e a correção daquele dia se baseou em evidência manual do usuário que usava **1 adulto**, ou seja, nunca foi uma comparação controlada com a automação (2 adultos).

Restrições: arquitetura CDP em Chrome real (patchright) é a única validada contra o Akamai; rate-limit silencioso por IP é real (rajadas 09-02); cadência de produção = 1 busca/origem/dia; o combo Smiles & Money é capturado sobre a MESMA página de resultados e herda o fix.

## Goals / Non-Goals

**Goals:**
- Confirmar (ou refutar) `adults=2` como causa do spinner eterno, com experimento controlado e matriz de decisão explícita
- Se confirmado: produção consulta o Smiles com 1 passageiro, sem alterar Google/Azul
- Semântica dos preços explícita no Telegram ("por viajante")
- Classificador de estados com discriminante real (busca-controle), encerrando a correção pendente de 06/09
- Registrar a correção da hipótese no findings da POC

**Non-Goals:**
- Verificar disponibilidade real de 2 assentos (fica explícito que o MVP não valida)
- Consolidar origens em SAO (change futura — reduziria 2 buscas para 1)
- Mudar Google Flights ou Azul (continuam `ADULTS=2`)
- Derrotar o sensor Akamai / API browserless (descartados com evidência na POC)

## Decisions

### D1 — Experimento ANTES da mudança de produção (gate explícito)

Probe `poc/smiles/probe_adults_discriminant.py` com a arquitetura validada (RealChrome patchright CDP), 3 buscas espaçadas 10 min (`smiles_origin_spacing_s`), evidência por run (screenshot + body + milhas + JSON consolidado em `poc/reports/smiles_adults_discriminant.json`):

1. **A** — jul/27, GRU, 1 adulto → previsto: **renderiza**
2. **B** — dez/26 (controle), GRU, 2 adultos → previsto: **spinner**
3. **C** — jul/27, GRU, 2 adultos → previsto: **spinner**

Matriz de decisão:

| A (jul,1a) | B (dez,2a) | C (jul,2a) | Conclusão | Ação |
|---|---|---|---|---|
| ✅ | ❌ | ❌ | **Consistente com adults=2** | NÃO muda produção ainda — ver D1b |
| ✅ | ✅ | ❌ | interação data×adultos (jul+2a específico) | NÃO mudar produção; investigar |
| ✅ | ✅ | ✅ | tudo renderiza (site intermitente) | repetir experimento noutro dia |
| ❌ | — | — | teoria adults morta — cliente/ambiente | pivot: perfil persistente, login, CDP no Chrome do usuário |

Ordem A primeiro: é a run com previsão mais valiosa e merece a sessão mais limpa; se A renderiza, a sessão provou-se sã e as falhas de B/C são atribuíveis aos seus parâmetros.

### D1b — Validação de CONFIABILIDADE em 3 manhãs (critério do usuário)

O usuário objetou com razão: "Smiles praticamente nunca funcionou" (zero SUCCESS em ciclos de produção na história; 2 renders avulsos) — **um render de sorte numa manhã não é confiabilidade**. A matriz da D1 testa a CAUSA; a D1b testa a CONFIABILIDADE, que é o que produção exige. Antes de qualquer mudança de produção, a run A (jul/27, GRU, 1 adulto — a config de produção candidata) deve renderizar em **3 manhãs consecutivas** de sessão limpa (antes do ciclo das 10:00, que renova o bloqueio do cliente automatizado — evidência 09/09: produção 10:08 flaggeou, probe 14:31 girou, URL idêntica renderizou no Chrome humano em 40s às 15:20).

- **3/3 manhãs** → config 1 adulto é confiável → prosseguir grupos 2-4
- **Parcial (1-2/3)** → adults necessário mas insuficiente; a confiabilidade do cliente automatizado é o problema real → pivot arquitetural (CDP no Chrome real do usuário, login, perfil persistente)
- **0/3** → teoria adults morta → pivot

**DECISÃO 09/09 (usuário): gate antecipado.** Com o diagnóstico fechado (2 causas medidas, fix de 2 linhas, rollback de 2 linhas), manter a config atual em produção virou o pior dos mundos garantido — ela tem 0 sucessos em toda a história; qualquer dia com ela é dia perdido por antecipação. O fix (grupos 2-3) foi aplicado no mesmo dia, e os CICLOS REAIS passam a ser a validação de confiabilidade: 3 ciclos consecutivos SUCCESS = confirmado; qualquer falha → investigar com o discriminante de busca-controle (grupo 3, já em produção) antes de concluir, e rollback trivial (`SMILES_ADULTS=2` + `driver="patchright"`) se o fix for o problema. O combo do Telegram só confirma quando o ciclo renderiza.

Custo: após a matriz da D1, cada manhã adicional é 1 busca isolada (~5 min).

*Alternativa descartada*: mudar produção direto e observar os ciclos diários — mais lento (1 ciclo/dia), confundido com a intermitência do site e sem controle de variáveis.

### D2 — `SMILES_ADULTS` específico do Smiles, default 1 no código

`adults` (2) é requisito da VIAGEM (Google/Azul). A busca do Smiles passa a ter parâmetro próprio: `smiles_adults = int(os.getenv("SMILES_ADULTS", "1"))`. Default **1 no código** (não só no .env): mesmo sem config, produção fica correta. `build_url()` ganha overrides opcionais (`departure_date`, `return_date`, `adults`) — retrocompatível, e reutilizado pelo probe e pelo discriminante.

`FlightQuote.passengers` do Smiles registra `smiles_adults` (o que foi de fato consultado) — sem mudança de schema.

*Alternativa descartada*: mudar `ADULTS=1` global — alteraria Google/Azul, que precisam de 2.

### D3 — Semântica "por viajante" explícita no Telegram

Linha de pontos do Smiles ganha sufixo "(por viajante)" — espelha o padrão existente `price_is_per_passenger` do dinheiro (Google). Deixa explícito ao usuário que o MVP não verifica 2 assentos. O requisito antigo "Two-passenger pricing" nunca refletiu a extração real (valores renderizados são "por viajante" — bug do wording 05/09 provou isso); o spec passa a descrever a realidade.

### D4 — Discriminante de busca-controle no classificador

Hoje (`smiles.py:431`): spinner eterno + data >300 dias → `CALENDAR_NOT_OPEN` — a inferência ambígua que gerou dias de rótulos errados. Novo fluxo quando o alvo não renderiza:

```
alvo não renderizou
  └─ busca CONTROLE (dez/2026, 1 adulto, mesma sessão/página)
       ├─ controle renderiza  → sessão SÃA → falha é do ALVO
       │     ├─ partida >300 dias → CALENDAR_NOT_OPEN (legítimo)
       │     └─ caso contrário    → TIMEOUT (comportamento atual)
       └─ controle falha      → sessão comprometida → BLOCKED (flag Akamai)
```

A lógica é a inversa do rascunho registrado no findings 06/09 ("controle abre e alvo não → flag") — se o controle abre, a sessão **não** está bloqueada; quem falhou foi o alvo. O findings será corrigido junto.

Custo: a busca-controle só roda no caminho de falha (raro); no caminho feliz, zero chamadas extras.

### D5 — Probe de combo apontado para as datas de controle

`probe_visual_combo.py` define `D, R = dez/2026` mas chama `build_url()` sem argumentos → caía em jul/27+2 adultos (página que nunca renderiza). Com os overrides de D2, o probe passa `D, R` e o painel de combos finalmente pode ser validado em automação ("combo não renderiza" era o mesmo bug).

### D6 — Reverter o driver do Smiles para playwright vanilla (descoberta 09/09)

A objeção do usuário ("Smiles praticamente nunca funcionou; deve haver outra razão") expôs o viés da teoria de bloqueio. Git-archaeology + experimento revelaram: **patchright nunca renderizou no Smiles** — a troca silenciosa de `68ac0e9` (05-09, herdada do Google) precede exatamente a era de falhas. O Azul usa o default vanilla e funciona. Matriz 2×2 de 09/09 (site sã, ~1h, controle intra-sessão):

| driver | adultos | resultado |
|---|---|---|
| patchright | 1 | ❌ spin (14:31) |
| vanilla | 2 | ❌ spin (15:22) |
| **vanilla** | **1** | ✅ **24s (15:35)** |
| humano | 1 | ✅ 40s (15:20) |

Duas causas independentes; o fix são 2 linhas (`driver="playwright"` + `SMILES_ADULTS=1`). Google mantém patchright (problema diferente: degradação de tarifas); Azul não muda. Lição: mudança de cliente anti-detecção exige revalidação POR SITE — o spec passa a exigir isso (requirement "Compatible automation driver").

*Alternativa descartada*: manter patchright + retry/aguardar "flag clearar" — sem base empírica (patchright: 0 renders em toda a história).

## Risks / Trade-offs

- **[Busca-controle pode acionar rate-limit]** → só roda em falha (raro); cadência de produção continua ≪ limite observado (~20 buscas/dia)
- **[1 adulto esconde falta de 2 assentos]** → aceito e explícito no Telegram; verificação de 2 assentos é non-goal do MVP
- **[Experimento pode dar falso negativo por flag acumulada na sessão]** → ordem A primeiro + spacing 10 min; matriz de decisão cobre os 4 desfechos, inclusive "repetir noutro dia"
- **[Site intermitente (07-08/09) contamina o experimento]** → o desfecho "tudo renderiza" está na matriz; repetição é o tratamento
- **[Troca de REMOVED/ADDED no spec pode perder intenção original]** → o requisito novo preserva a intenção (valores corretos) com semântica real; o histórico fica no findings

## Migration Plan

1. Probe do experimento → rodar → registrar evidência + desfecho da matriz
2. **Só se confirmado**: `smiles_adults` no config + `build_url` overrides + quote `passengers` + sufixo no Telegram + discriminante no classificador + fix do probe de combo
3. Se **refutado** (A falha): nada muda em produção; findings registra o desfecho e as próximas hipóteses (perfil persistente, login, CDP no Chrome do usuário)
4. Rollback: `SMILES_ADULTS=2` no `.env` restaura o comportamento anterior sem mudança de código (o discriminante é aditivo e só atua em falha)

## Open Questions

- Nenhuma bloqueante. (Curiosidade residual: o mecanismo interno pelo qual 2 adultos derruba a saga do MFE — o experimento é empírico e não depende dessa resposta.)
