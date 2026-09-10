## ADDED Requirements

### Requirement: Single-passenger availability search
The system SHALL executar a busca de disponibilidade do Smiles com **1 passageiro**, parâmetro isolado das demais fontes, pois a consulta com 2 adultos não é respondida pelo back-end (spinner eterno — evidência 2026-09-02 a 09).

#### Scenario: Search executed with one passenger
- **WHEN** o scraper do Smiles monta a URL de consulta
- **THEN** o parâmetro `adults` da URL é 1
- **AND** as fontes Google Flights e Azul continuam consultando com os passageiros da viagem (2)

#### Scenario: Passenger count configurable
- **WHEN** o comportamento precisar ser revertido ou ajustado
- **THEN** o número de passageiros da busca do Smiles é lido de `SMILES_ADULTS` no `.env`
- **AND** o default no código é 1 (produção correta mesmo sem config)

#### Scenario: Quote records actual search
- **WHEN** a quote do Smiles é persistida
- **THEN** `passengers` registra o número de fato consultado (1)
- **AND** nenhuma coluna de schema é alterada

### Requirement: Per-traveler pricing semantics
The system SHALL tratar e expor os valores do Smiles como **por viajante** (como o site exibe: "milhas por viajante"), deixando explícito que a disponibilidade de 2 assentos não é verificada pelo MVP.

#### Scenario: Telegram marks per-traveler semantics
- **WHEN** a mensagem do Telegram inclui a linha de pontos do Smiles
- **THEN** o valor aparece com a marcação "por viajante"
- **AND** o padrão é consistente com o sufixo "/pessoa" já existente para preços em dinheiro

#### Scenario: Miles-only value unchanged
- **WHEN** a busca com 1 passageiro renderiza
- **THEN** o valor só-milhas extraído tem o mesmo significado de antes ("a partir de X milhas por viajante")
- **AND** o fluxo de combo Smiles & Money continua funcionando sobre a mesma página

### Requirement: Availability classification via control search
The system SHALL classificar falhas de renderização do Smiles por meio de busca-controle (datas rolling hoje+90/97 dias — sempre dentro da janela —, 1 passageiro, mesma sessão), e NÃO por inferência da distância da data. A busca-controle só executa quando o alvo não renderiza.

#### Scenario: Control renders, target fails
- **WHEN** a busca-alvo não renderiza e a busca-controle renderiza na mesma sessão
- **THEN** a sessão está sadia e a falha é específica do alvo
- **AND** partida >300 dias classifica `CALENDAR_NOT_OPEN`
- **AND** caso contrário classifica `TIMEOUT`

#### Scenario: Control also fails
- **WHEN** a busca-controle também não renderiza
- **THEN** a sessão está comprometida (flag do Akamai)
- **AND** o status é `BLOCKED`, independentemente da data

#### Scenario: Happy path adds no extra calls
- **WHEN** a busca-alvo renderiza normalmente
- **THEN** nenhuma busca-controle é executada
- **AND** a cadência de produção não aumenta

### Requirement: Compatible automation driver
The system SHALL acessar o Smiles por meio do driver de automação com capacidade de renderização comprovada neste site (playwright vanilla `connect_over_cdp` sobre Chrome real), e qualquer troca de driver SHALL ser validada com um render real antes de adoção.

#### Scenario: Production uses the proven driver
- **WHEN** o scraper do Smiles abre a sessão CDP
- **THEN** usa o driver com render comprovado (playwright vanilla)
- **AND** outros sites (Google) podem manter drivers distintos, pois a validação é POR SITE

#### Scenario: Driver changes require render validation
- **WHEN** um driver/publisher de automação for trocado ou atualizado
- **THEN** um render real do Smiles é verificado antes da adoção em produção
- **AND** a troca silenciosa sem validação é o defeito que esta regra previne (evidência 68ac0e9, 05-09: patchright quebrou o Smiles por 4+ dias sem diagnóstico)

## REMOVED Requirements

### Requirement: Two-passenger pricing
**Reason**: O requisito nunca refletiu a realidade da extração — o site exibe valores "por viajante" e a busca com 2 adultos não é respondida pelo back-end (spinner eterno; evidência consolidada 2026-09-02 a 09). Totais para 2 passageiros não são calculados nem verificáveis pelo MVP.
**Migration**: Substituído por "Per-traveler pricing semantics" (valores por viajante com marcação explícita no Telegram); a verificação de disponibilidade para 2 assentos fica fora do escopo do MVP.
