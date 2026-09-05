## ADDED Requirements

### Requirement: Smiles & Money combo capture
The system SHALL, após localizar o voo mais barato no Smiles, abrir o quadro de tarifas do card, acionar a combinação milhas + dinheiro destinada a **clientes Smiles**, posicionar o seletor na maior quantidade de milhas disponível que seja **menor que 210.000** (configurável) e capturar o **valor em reais** exibido para essa combinação.

#### Scenario: Open fare options panel
- **WHEN** o voo mais barato é identificado no resultado do Smiles
- **THEN** o scraper clica no botão **"Selecionar tarifa"** do card desse voo
- **AND** o quadro inferior abre exibindo as seções **"Use milhas"** e **"Pague com Smiles & Money"**
- **AND** a seção "Pague com Smiles & Money" contém as caixas "Combinações para assinantes Clube Smiles a partir de" e **"Combinações para clientes Smiles a partir de"** (inferior direita)

#### Scenario: Open combination slider
- **WHEN** o scraper clica no botão **"Combinar"** da caixa **"Combinações para clientes Smiles a partir de"** (inferior direita)
- **THEN** um novo quadro abre com o **slider** de quantidade de milhas e o valor em reais correspondente exibido abaixo
- **AND** o quadro contém os botões "Cancelar" e "Confirmar"

#### Scenario: Select largest combo under the threshold
- **WHEN** o quadro do slider está aberto
- **THEN** o scraper seleciona a **maior quantidade de milhas** oferecida que seja **menor que 210.000** (limite configurável via `SMILES_COMBO_MAX_MILES`)
- **AND** captura o **valor em reais** exibido abaixo do slider para essa combinação
- **AND** registra `hybrid_miles` (milhas da combinação) e `cash_component_brl` (reais) na quote

#### Scenario: Combo included in Telegram without discarding miles-only
- **WHEN** a mensagem do Telegram é montada
- **THEN** a seção Smiles exibe o valor **só-milhas existente** E a combinação capturada (milhas + reais) na mesma mensagem
- **AND** o valor só-milhas NÃO é descartado ou substituído pelo combo

#### Scenario: Combo flow failure does not invalidate miles-only
- **WHEN** qualquer etapa do fluxo de combo falha (painel não abre, slider ausente, valor não legível)
- **THEN** o status do só-milhas é preservado e a quote persiste normalmente
- **AND** o campo do combo fica vazio
- **AND** um screenshot de evidência é salvo em `poc/reports/` para diagnóstico

#### Scenario: Threshold configurable
- **WHEN** o limite de milhas do combo precisa mudar
- **THEN** ele é lido de `SMILES_COMBO_MAX_MILES` no `.env` (default 210000)
- **AND** nenhuma alteração de código é necessária
