## 1. Configuração

- [x] 1.1 Adicionar `SMILES_COMBO_MAX_MILES=210000` no `.env.example` e default em `src/config.py` (`smiles_combo_max_miles`)
- [x] 1.2 Documentar no README (seção Smiles: combo ≤210k milhas + reais)

## 2. Fluxo de captura do combo (src/scrapers/smiles.py)

- [x] 2.0 Criar função APARTADA `_capture_money_combo(page, floor_miles)` com try/except próprio que NUNCA propaga exceção (toda etapa com timeout e retorno None em falha, com log + screenshot) e flag `SMILES_COMBO_ENABLED` no .env (default true; false = fluxo idêntico ao atual)
- [x] 2.1 Dentro da função apartada: localizar o card do voo mais barato (pelo número de milhas do piso) e clicar "Selecionar tarifa"
- [x] 2.2 Aguardar o quadro "Pague com Smiles & Money" (texto âncora) com timeout de 15s
- [x] 2.3 Clicar "Combinar" da caixa "Combinações para clientes Smiles a partir de" (inferior direita; NÃO a de Clube Smiles)
- [x] 2.4 Aguardar o quadro do slider ("Combinar do seu jeito"/Confirmar)
- [x] 2.5 Selecionar o maior valor de milhas < 210.000 via teclado (setas) com verificação do texto após cada passo; fallback: clique proporcional no trilho
- [x] 2.6 Capturar o valor em reais exibido abaixo do slider para a posição selecionada
- [x] 2.7 Fechar o quadro (Cancelar/Escape) SEM confirmar a compra
- [x] 2.8 Evidência: screenshot + texto do quadro em caso de falha de qualquer etapa (sem invalidar o só-milhas)

## 3. Modelos e persistência

- [x] 3.1 Preencher `hybrid_miles` e `cash_component_brl` na quote do Smiles
- [x] 3.2 Registrar o card/texto do combo em `raw_sample` (evidência)
- [x] 3.3 Validar que status/miles do só-milhas permanecem intactos em falha do combo
- [ ] 3.4 REGRESSÃO: executar com `SMILES_COMBO_ENABLED=false` e com falha forçada do combo — confirmar que só-milhas/status/Telegram saem idênticos ao fluxo atual (garantia de não impacto)

## 4. Telegram

- [x] 4.1 Linha do combo na seção Smiles: "🎫 GRU: 193.100 milhas + R$ 3.680 (combo ≤210k)" além do só-milhas
- [x] 4.2 Formato: combo exibido APÓS o só-milhas, sem substituí-lo

## 5. Validação

- [x] 5.1 Teste com datas de controle (dez/2026, GRU): combo capturado e valores conferidos com o print do usuário — VALIDADO 10/09 na config de produção (jul/27, AF 301.500): âncora 1 = 16.000+R$6.100 (igual ao print do usuário de 09/09) e melhor combo ≤210k = 159.000+R$3.220, capturado IDÊNTICO pelas duas vias (slider 12:28 e API pricesm 12:33)
- [ ] 5.2 Teste de falha isolada: combo ausente no card → só-milhas preservado
- [ ] 5.3 Validação em produção (ciclo 10:00): combo presente no Telegram para GRU

## 6. Diagnóstico da falha do combo com página renderizando (09/09)

Contexto: primeiro smoke test com página viva (pós-fix driver+adultos) — o combo falhou no passo 3 ("caixa 'clientes Smiles' não encontrada", 30s sem achar) e o diag mostrou NENHUM elemento "Combinações..." no DOM. Prints do usuário (jul/27, AF 301.500): a caixa EXISTE e monta "praticamente imediato" no browser humano (16.000 milhas + R$ 6.100; slider 16.000–254.400 ↔ R$ 1.320–6.100). Hipóteses vivas: **C3** re-render derruba o painel (combo rodou 24s após o render, MFE assentando) × **C5** montagem preguiçosa que exige viewport/scroll (clique via JS não rola a página). C1 (pricing lento) e C2 (caixa ausente p/ a tarifa) já descartadas pelos prints.

- [x] 6.1 Criar `poc/smiles/probe_combo_hipotheses.py`: driver vanilla (config de produção), jul/27+GRU+1 adulto; render → dismiss banner → clicar "Selecionar tarifa" no card de menor milhas (mesma lógica da produção) → timeline de 90s com fases: **A (0–30s)** observação passiva; **B** re-click (C3) ou scrollIntoView (C5) → observar mais 60s — PRIMEIRA TENTATIVA (09/09 17:14) inconclusiva: página não renderizou em 180s. MÉTODO COMPROVADAMENTE IDÊNTICO ao que renderizou às 15:35 (A1) e ~16:00 (smoke): URL byte-idêntica, mesmo driver/fluxo — a variável é a JANELA TEMPORAL (intermitência do site/sensor), não o método; contagem simples de buscas do dia NÃO explica (7ª e 8ª renderizaram, 9ª não). Reexecução agendada 10/09 ~10:40, DEPOIS do ciclo de produção (decisão do usuário: a prova de produção vem primeiro; o probe só roda se o ciclo renderizar e provar o ambiente bom)
- [x] 6.2 Classificação automática do desfecho: caixa montou na fase A = montagem lenta (C1) / "Use milhas" sumiu e voltou após re-click = C3 / caixa montou logo após scrollIntoView = C5 / nada = desconhecido (dump profundo)
- [x] 6.3 Evidência permanente: screenshots (clique+2s, transições de fase, montagem/falha) + body dumps + log de rede com timestamps das chamadas de pricing/offer/money + JSON consolidado em `poc/reports/combo_hipotheses.json`
- [x] 6.4 Endurecer `_capture_money_combo` (aplicado 09/09 — cobre C3 e C5 independentemente do desfecho do probe): polling da CAIXA por 90s + scrollIntoView assistido + re-click único se o painel colapsar + screenshot/body obrigatórios em `smiles_combo_nao_montou.*` na falha; JS hoisted em constantes (`_JS_CLIQUE_MENOR_TARIFA`, `_JS_SCROLL_PAINEL`, `_JS_COMBINAR_CLIENTES`)
- [x] 6.5 Revalidar 10/09: probe classificou **MONTOU_NA_FASE_A** (caixa monta em ~2s quando o site está bom — C3/C5/C1 descartados; a falha de 09/09 era intermitência) e expôs os bugs reais: seletor do Combinar pegava só o `<título>` da caixa (fix: partir dos botões e validar ancestralidade — NÃO-Clube) e o quadro usa `input[type=range]`, nunca `[role=slider]`. Smoke de produção capturou 159.000+R$3.220; ciclo real fica p/ 5.3

## 7. Pivô: slider → resposta da API pricesm (10/09, decisão do usuário)

O slider manipulável provou-se desnecessário: o clique em "Combinar" dispara `pricesm?flightuid=...&fareType=SMILES_MONEY`, cuja `fareList` traz as âncoras EXATAS que o slider exibe (GRU jul/27 AF: 16.000/6.100, 31.800/5.780, 79.600/4.820, 111.400/4.180, 159.000/3.220, 254.400/1.320) e o trilho só "snappa" nelas (clique a 81% do trilho caiu na âncora 159.000). `_capture_money_combo` reescrito: card do piso → caixa (espera §6.4) → arma listener da resposta → Combinar → aguarda JSON (30s) → maior miles < limite → Escape.

- [x] 7.1 `_capture_money_combo` via resposta pricesm (listener com timeout, evidência `smiles_combo_sem_pricesm.png` na falha, Escape fecha sem confirmar; garantias §2.0 preservadas)
- [x] 7.2 Validado em smoke (`poc/smiles/smoke_combo_producao.py` chama a função de produção direto): (159000, 3220.0) — idêntico ao fluxo do slider validado às 12:28; formato Telegram "🎫 GRU: 159.000 milhas + R$ 3220 (combo ≤210k)"
- [x] 7.3 Probes de diagnóstico mantidos como evidência: `probe_combo_hipotheses.py` (classificação C3×C5) e `probe_combo_slider.py` (corpo da pricesm + timeline do quadro)
- [x] 7.4 REGRESSÃO (equivale à 3.4, executada 10/09 16:04, `smoke_regressao_combo.py` roda `_search_origin` de produção): flag OFF → SUCCESS/301.500/AIR FRANCE, hybrid=None, cash=None, sem `raw_sample["combo"]`, Telegram `🎫 301.500 pontos (por viajante) — AIR FRANCE` + fallback `💰 ~combo 200.000 milhas + R$ 2.233 (estimado)`; flag ON → mesmos só-milhas/status/airline + `💰 combo 159.000 milhas + R$ 3.220 — AIR FRANCE (por viajante)` — linha 🎫 IDÊNTICA nas duas execuções; estimado confirmado como fallback p/ falha do combo (decisão do usuário)
- [ ] 7.5 Fechar 5.2/5.3 no ciclo real (10:00 de 11/09): combo presente no Telegram para GRU
