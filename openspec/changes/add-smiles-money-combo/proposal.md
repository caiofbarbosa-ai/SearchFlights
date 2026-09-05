## Why

O monitor hoje captura apenas o valor **só-milhas** do Smiles. Mas a opção economicamente relevante na rota GRU/VCP → BKK é o **Smiles & Money** (combinar milhas + dinheiro) — o print do usuário (`poc/reports/smiles_completo.png`) mostra combos partindo de **19.300 milhas + R$ 7.360,00**, muito mais acessíveis que os 384.100+ milhas do só-milhas. Sem capturar o combo, o monitor ignora justamente a alternativa de menor desembolso total de milhas.

## What Changes

- Após localizar o voo mais barato (fluxo existente), o scraper clica em **"Selecionar tarifa"** no cartão, abrindo o quadro com **"Use milhas"** e **"Pague com Smiles & Money"**
- Clica em **"Combinar"** no quadro inferior direito (**"Combinações para clientes Smiles a partir de"**), abrindo o **slider** de combinação
- Move o slider para a **maior quantidade de milhas menor que 210.000** e captura o **valor em reais** exibido abaixo
- O valor capturado (combo) entra na mensagem do Telegram **junto** (sem substituir) do valor só-milhas existente
- Limiar do híbrido Smiles passa de 120k (placeholder) para **210k milhas** (configurável)

## Capabilities

### New Capabilities

- `smiles-money-combo`: captura da combinação milhas + dinheiro (Smiles & Money) a partir do card do voo mais barato — navegação Selecionar tarifa → Combinar → slider ≤210k milhas → valor em reais

### Modified Capabilities

- `smiles-scraper`: o resultado da fonte passa a incluir, além do só-milhas, o combo milhas+dinheiro (campos híbrido no quote); fluxo pós-extração do voo mais barato estendido com a interação do painel de tarifas

## Impact

- `src/scrapers/smiles.py`: nova fase pós-resultados (clique Selecionar tarifa → Combinar → slider → leitura do valor)
- `src/config.py`: novo `smiles_combo_max_miles` (default 210.000)
- `src/notifications/telegram.py`: linha do combo na seção Smiles
- `daily_flight_quotes`: `hybrid_miles` + `cash_component_brl` já existentes — sem mudança de schema
- Risco: interação UI (slider) é mais frágil que leitura passiva — com captura de evidência e status de falha isolado (combo ausente não invalida o só-milhas)
