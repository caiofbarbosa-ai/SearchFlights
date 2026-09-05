## ADDED Requirements

### Requirement: Source result includes Smiles & Money combo
The Smiles source result SHALL incluir, além do valor só-milhas existente, a combinação milhas + dinheiro capturada pelo fluxo `smiles-money-combo` (híbrido), permitindo que o Telegram e o histórico exibam ambos.

#### Scenario: Quote carries both values
- **WHEN** o fluxo de combo completa com sucesso para uma origem
- **THEN** a quote dessa origem contém `miles` (só-milhas, já existente), `hybrid_miles` e `cash_component_brl` (combo capturado)
- **AND** ambos são persistidos em `daily_flight_quotes` sem mudança de schema

#### Scenario: Partial combo failure isolation
- **WHEN** o fluxo de combo falha para uma origem
- **THEN** a quote mantém `status` e `miles` do só-milhas intactos
- **AND** o erro do combo é registrado em `raw_sample` (evidência) sem alterar o status da fonte
