# Proposal: smiles-1-adulto

## Why

O Smiles não renderiza resultados nas consultas automatizadas de jul/2027 (spinner eterno), enquanto o usuário consulta manualmente com sucesso. A auditoria da evidência histórica (2026-09-02 a 09) mostrou que **nenhuma busca com 2 adultos renderizou — em nenhuma data, em nenhum cliente** — e todo sucesso (POC CDP, validação 05/09, prints manuais do usuário) usou `adults=1`. A hipótese "flag do Akamai" não sobrevive: em 06/09 o flag estava medidamente clearado e julho ainda assim falhou. O número de passageiros é o único fator que separa todo sucesso de toda falha.

Como o site exibe "milhas **por viajante**" de qualquer forma, consultar com 1 adulto **não muda o significado dos valores extraídos** — muda apenas a consulta que o back-end consegue responder.

## What Changes

- **Reverter o driver do Smiles para playwright vanilla** (`driver="playwright"`): patchright — introduzido em 05-09 (`68ac0e9`) herdado do Google — **nunca renderizou neste site** (0 sucessos; vanilla 2/2 históricos + matriz 09/09). Google mantém patchright; Azul já roda vanilla default
- **Mudança de produção**: a busca do Smiles passa a usar 1 passageiro (`SMILES_ADULTS`, default 1) — 2 adultos não renderiza nem com o driver certo (matriz 09/09) — SEM alterar as outras fontes (Google/Azul continuam com `ADULTS=2`)
- **Semântica honesta no Telegram**: linha do Smiles marcada "por viajante", deixando explícito que a disponibilidade de 2 assentos não é verificada pelo MVP
- **Correção do classificador** (pendente desde 06/09): `CALENDAR_NOT_OPEN` deixa de ser inferido da data (>300 dias) e passa a exigir discriminante de busca-controle (dez/2026 na mesma sessão: controle abre + alvo falha → alvo é o problema; controle falha → sessão comprometida/BLOCKED)
- **Correção do probe de combo**: `probe_visual_combo.py` apontava para jul/27+2 adultos (página que nunca renderiza) — passa a usar as datas de controle; explica o mistério "combo não renderiza em automação"
- Atualização do findings (RESOLUÇÃO 09/09): teoria "flag Akamai" substituída pelas duas causas medidas (driver × adultos)
- Fora do escopo (candidato a change futura): consolidar GRU+VCP → SAO (1 busca cobre os 3 aeroportos de SP); verificação de disponibilidade real para 2 assentos

## Capabilities

### New Capabilities

(nenhuma — o experimento é trabalho de validação, não capacidade do sistema; fica nas tasks)

### Modified Capabilities

- `smiles-scraper`: (1) a consulta de disponibilidade passa a ser executada com 1 passageiro, configurável e isolada das demais fontes; (2) o requisito "Two-passenger pricing" — que nunca refletiu a realidade da extração (valores exibidos são "por viajante") — é substituído por precificação por viajante com semântica explícita no Telegram; (3) classificação de estados passa a exigir discriminante de busca-controle antes de rotular `CALENDAR_NOT_OPEN` vs `BLOCKED`

## Impact

- **Código**: `src/config.py` (novo `smiles_adults`), `src/scrapers/smiles.py` (`build_url` com overrides + discriminante de controle), `src/notifications/telegram.py` (sufixo "por viajante"), `poc/smiles/probe_visual_combo.py` (datas de controle)
- **Novo**: `poc/smiles/probe_adults_discriminant.py` + evidências em `poc/reports/`
- **Config**: `SMILES_ADULTS=1` no `.env` (default no código já resolve)
- **Sem mudança de schema** no Supabase; `passengers` da quote do Smiles passa a registrar 1 (o que foi de fato consultado)
- **Risco controlado**: busca-controle só roda quando o alvo falha (não adiciona pressão ao Akamai no caminho feliz)
