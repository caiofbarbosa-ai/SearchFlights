# Azul POC — Findings (2026-09-02)

**Status:** ✅ **POC VALIDADO — busca guest funciona, extração real de award interline**
**Critério (preços/pontos corretamente extraídos): ATINGIDO**
**Metodologia:** recon → classificação → fluxo → gate (a mesma do Google Flights/Smiles)

---

## 1. Arquitetura descoberta

| Item | Detalhe |
|---|---|
| Portal de award interline | **`azulpelomundo.voeazul.com.br`** (link "Azul pelo mundo" no menu da voeazul) |
| Acesso | **Guest funciona — sem login** para a busca |
| Widget | `#autocompleteFlightOrigin` / `#autocompleteFlightDestination` (sugestão via API `/api/airport?searchAirport=GRU`); datas `DD/MM/YYYY` digitáveis; steppers de passageiro; **`#btnSearchTickets`**; toggle "Pontos" |
| API de disponibilidade | **`/api/availability?tripType=ROUND_TRIP&origin=GRU&destination=BKK&adult=1...`** (primeira parte, JSON ~78KB) — mas exige **token reCAPTCHA** (`400 error.recaptchaValidation` para Python puro) → **rota de browser, não browserless** |
| URL de resultados | Path-params: `/flights/RT/GRU/BKK/-/-/<ida>/<volta>/1/0/0/0/0/ALL/F/ECONOMY/-/-/-/-/A/-` |
| Proteção | Página inicial bloqueou Playwright puro na 1ª tentativa ("comportamento incomum", Akamai) — **CDP-attach em Chrome real passou consistentemente** (mesmo padrão validado no Smiles) |

## 2. Resultados do gate (3 origens, datas de controle 8→16/12/2026)

| Origem | Status | Evidência |
|---|---|---|
| **GRU** | ✅ **RESULTS — 18 valores de pontos** (156.000–410.000) | `azul_gate_gate_r1_GRU.png` |
| **CGH** | ✅ **NO_RESULTS legítimo** — "Desculpe, não há voos disponíveis para esta data." (aeroporto doméstico, sem award interline) | `azul_gate_gate_cgh_retry2_CGH.png` |
| **VCP** | ⚠️ Results com 2 valores (286.000, 357.000) — abaixo do threshold de 3, mas prova award via conexão | `azul_gate_gate_r3_VCP.png` |

Mais o run de exploração anterior: **8 valores + Points+Money + parceiras** (`azul_flow_3_results.png`).

## 3. Award interline confirmado (spec do POC atendida)

Screenshot `azul_flow_3_results.png` — "Selecione o voo de ida GRU→BKK", **só companhias parceiras** (nenhum voo Azul, como esperado):

| Companhia | Rota | Duração | Só pontos | Pontos + dinheiro |
|---|---|---|---|---|
| Qatar | 20:50→07:35 (+2d), 1 parada | 24h45 | 480.000 | **384.000 + R$ 1.485** |
| Ethiopian | 01:45→12:00, 1 parada | 24h15 | 678.500 | 543.000 + R$ 2.070 |
| Emirates | 01:05→12:30, 1 parada | 25h25 | 828.500 | 663.000 + R$ 2.925 |
| Swiss | 18:25→09:50 (+2d), 1 parada | 29h25 | 802.000 | 642.000 + R$ 2.425 |
| **Japan Airlines** | 22:00→23:00 (+2d), 2 paradas | 39h | **195.000** | **156.000 + R$ 595** (menor custo) |
| KLM | 14:40→09:30 (+3d), 2 paradas | 50h50 | 320.000 | 256.000 + R$ 1.875 |
| Air France | 14:40→09:30 (+2d), 2 paradas | 32h50 | 481.500 | 385.500 + R$ 1.475 |

✔ "results display partner airline options (not just Azul flights)" — **atendido**
✔ "Points + Money options are visible" — **atendido** ("ou X pontos + R$ Y" em todos os cartões)

## 4. Aprendizados de automação (para a Fase 6)

1. **Datas**: ambos os campos compartilham placeholder "Selecione a data" — localizar por placeholder rematcha o campo errado; usar placeholder `DD/MM/YYYY` para a partida e input **vazio** para a volta (clique por coordenadas via JS), ou verificar auto-avanço de foco
2. **Códigos de aeroporto**: `has_text="CGH"` casa "Mc**Ghee** (TYS)" — casar o código **entre parênteses** com regex
3. **SPA lazy**: widget pode não renderizar no primeiro load — poll de visibilidade + 1 reload (mesmo padrão do Smiles)
4. Sem sinais de rate-limit agressivo hoje (~12 buscas) — diferente do Smiles; confirmar na cadência diária

## 5. Pendências (para o go/no-go)

- Cadência diária: 1ª semana de produção confirma estabilidade (padrão de todas as fontes)
- Passenger 2 adultos: steppers mapeados (`btn-add-passenger-counterAdult`) — Fase 6
- Extração estruturada por cartão (airline/pontos/pontos+dinheiro/duração/paradas) — Fase 6

---

*Azul POC — 2026-09-02 — CDP-attach em Chrome real (mesma arquitetura validada no Smiles)*
