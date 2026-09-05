## 1. Configuração

- [ ] 1.1 Adicionar `SMILES_COMBO_MAX_MILES=210000` no `.env.example` e default em `src/config.py` (`smiles_combo_max_miles`)
- [ ] 1.2 Documentar no README (seção Smiles: combo ≤210k milhas + reais)

## 2. Fluxo de captura do combo (src/scrapers/smiles.py)

- [ ] 2.1 Localizar o card do voo mais barato (pelo número de milhas do piso) e clicar "Selecionar tarifa"
- [ ] 2.2 Aguardar o quadro "Pague com Smiles & Money" (texto âncora) com timeout de 15s
- [ ] 2.3 Clicar "Combinar" da caixa "Combinações para clientes Smiles a partir de" (inferior direita; NÃO a de Clube Smiles)
- [ ] 2.4 Aguardar o quadro do slider ("Combinar do seu jeito"/Confirmar)
- [ ] 2.5 Selecionar o maior valor de milhas < 210.000 via teclado (setas) com verificação do texto após cada passo; fallback: clique proporcional no trilho
- [ ] 2.6 Capturar o valor em reais exibido abaixo do slider para a posição selecionada
- [ ] 2.7 Fechar o quadro (Cancelar/Escape) SEM confirmar a compra
- [ ] 2.8 Evidência: screenshot + texto do quadro em caso de falha de qualquer etapa (sem invalidar o só-milhas)

## 3. Modelos e persistência

- [ ] 3.1 Preencher `hybrid_miles` e `cash_component_brl` na quote do Smiles
- [ ] 3.2 Registrar o card/texto do combo em `raw_sample` (evidência)
- [ ] 3.3 Validar que status/miles do só-milhas permanecem intactos em falha do combo

## 4. Telegram

- [ ] 4.1 Linha do combo na seção Smiles: "🎫 GRU: 193.100 milhas + R$ 3.680 (combo ≤210k)" além do só-milhas
- [ ] 4.2 Formato: combo exibido APÓS o só-milhas, sem substituí-lo

## 5. Validação

- [ ] 5.1 Teste com datas de controle (dez/2026, GRU): combo capturado e valores conferidos com o print do usuário
- [ ] 5.2 Teste de falha isolada: combo ausente no card → só-milhas preservado
- [ ] 5.3 Validação em produção (ciclo 10:00): combo presente no Telegram para GRU
