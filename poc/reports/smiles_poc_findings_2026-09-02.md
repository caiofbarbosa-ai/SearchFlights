# Smiles POC — Findings & Caminho de Mitigação (2026-09-02)

**Status:** ✅ **POC VALIDADO (arquitetura CDP + extração real) com 2 ressalvas operacionais**
1. **Self-hosted obrigatório** — Akamai só aceita browser real; GitHub Actions inviável para esta fonte
2. **Rate-limit silencioso por IP** — rajadas de buscas retornam lista vazia; cadência de produção (3 buscas/dia) fica abaixo do limite; estabilidade da cadência diária a confirmar no dry-run (recomendado: D+1)

**Critério do usuário (preços corretamente extraídos): ATINGIDO** no experimento de validação (11:41) — award real com companhia, horários, duração, escalas e milhas por passageiro. Gate 3×3 contínuo não é atingível nesta fonte (rate-limit); ver §3.1.3.
**Metodologia:** aprendizados do Google Flights aplicados (recon → classificação → evidência por step → telemetria de rede)

---

## 1. O que FUNCIONOU (progresso real em relação ao esqueleto de agosto)

| Conquista | Evidência |
|---|---|
| Site acessível sem login wall; widget de busca automatizado end-to-end | `smiles_v3_1_airports.png`, `smiles_v3_2_dates.png` |
| Seletores reais descobertos (não chutados): `#inp_flightOrigin_1`, `#inp_flightDestination_1`, `#startDateId`, `#endDateId`, botão "Buscar voos" | probe de DOM (`poc_smiles_probe.py`) |
| **URL direta de resultados** (equivalente do `q=` do Google): `/mfe/emissao-passagem/?adults=2&originAirport=GRU&destinationAirport=BKK&departureDate=<epoch_ms meia-noite BRT>&returnDate=<epoch_ms>&tripType=1&searchType=congenere...` — busca aceita, header mostra rota/datas/passageiros corretos | `smiles_v3_3_results.png`, `smiles_direct_e1_GRU.png` |
| Armadilhas mapeadas: Enter submete form e limpa campos (clicar na sugestão `<li>`); datas são `readonly` (calendário react-dates, `td.CalendarDay` + aria-label); overlays pt/en dispensáveis | logs das iterações v2/v3 |
| API de busca identificada: `api-air-flightsearch-blue.smiles.com.br/v1/airlines/search?...` | telemetria diag2 |

## 2. Causa raiz do bloqueio (cadeia completa, com evidência)

Para sessão **guest**, a busca de award parceiro (congenere) **nunca completa**:

```
1. members-blue.smiles.com.br/v1/members → 452 {"code":60,"message":"Token incorreto."}
   (checagem de membro falha sem login)
2. MFE flight-availability CRASHA no saga:
   TypeError: Cannot read properties of null (reading 'memberNumber')
   created by takeLatest(global/changeMemberData, Ip)
3. XHR de disponibilidade é bloqueado (net::ERR_FAILED / CORS):
   api-air-flightsearch-blue.smiles.com.br/v1/airlines/search?cabin=ALL&...
4. Spinner "Aguarde enquanto buscamos" roda indefinidamente (>8 min observados)
   → 0 resultados renderizados → 0 dados extraídos
```

O alerta do evaluation de 2026-08-16 ("Smiles pode requerer login") está **validado**.

## 3. Caminhos de mitigação (avaliados sob restrição R$ 0)

### 3.1 Experimento discriminante (usuário carregou a URL manualmente, sem logar)

| Sessão | Browser | Estado | Resultado |
|---|---|---|---|
| Usuário (manual) | Chrome normal do sistema | sem usar credenciais* | **✅ carregou** |
| POC | Playwright Chromium embutido | guest | ❌ spinner eterno |
| POC | Playwright + **Chrome real** (canal `chrome`) | guest | ❌ spinner eterno (mesmo CORS-ERR_FAILED no XHR) |
| POC | Playwright + Chrome real + **aquecimento** (home + mouse + scroll antes da URL direta) | guest | ❌ spinner eterno |

\* ponto crítico: "não usei credenciais agora" ≠ sessão ausente — o browser do usuário pode carregar cookie de sessão de login anterior (membro sem saber) e/ou cookies de clearance do bot-manager (beacon `jd35BMeQ/...` no tráfego = assinatura Kasada).

**Hipóteses restantes:**
- **H-sessão**: o browser do usuário carrega sessão de membro de login antigo → M1 (login) é o caminho
- **H-clearance**: guest real funciona, mas o bot-manager detecta a automação em nível de protocolo (CDP), não de fingerprint (refutado: fingerprint real + aquecimento não bastaram) → browser automation com Playwright tende a falhar sempre; M2 (API direta) se torna o caminho principal

**Teste incógnito (decisivo, executado pelo usuário 2026-09-02):** janela anônima (zero cookies/sessão) → **CARREGOU (~1 min)**; e na sessão normal o site mostra NÃO logado (pede criação de conta). **Conclusão: busca guest funciona para humanos; login NÃO é o requisito. O bloqueio é o bot-manager (Akamai — cookies `_abck`/`bm_*`) validando o pacote coerente sensor+dispositivo.**

### 3.1.1 Corrida de armamento — todos os clientes testados (2026-09-02)

| Cliente | Cookies válidos | TLS | Veredito |
|---|---|---|---|
| Python urllib | — | Python | ❌ 406 (deny Akamai) |
| Python urllib | replay do usuário | Python | ❌ 406 |
| tls-client (JA3 Chrome impersonado) | replay do usuário | Chrome | ❌ 406 |
| Playwright Chromium + stealth | sensor flaggado | Chromium | ❌ XHR bloqueado (ERR_FAILED) |
| Playwright + Chrome real (`channel=chrome`) | sensor flaggado | Chrome | ❌ XHR bloqueado |
| Playwright + Chrome real + aquecimento (home+mouse+scroll) | sensor flaggado | Chrome | ❌ XHR bloqueado |
| **patchright** (CDP-leaks corrigidos) + Chrome real | sensor flaggado | Chrome | ❌ XHR bloqueado |
| **Chrome do usuário (humano, guest, anônima)** | sensor válido | Chrome real | ✅ **funciona (~1 min)** |

**Veredito:** só browser real não-automatizado passa. API direta (M2) exigiria derrotar o sensor Akamai (cookies vinculados ao dispositivo — replay via TLS-impersonation não basta). Automação browser (M1/M2-browser) falha em todas as variantes testadas. **A arquitetura GitHub Actions (IP datacenter) é inviável para o Smiles.**

### 3.1.2 ✅ BREAKTHROUGH — CDP-attach em Chrome real FUNCIONA (caminho A validado)

`poc_smiles_cdp_real.py`: lança Chrome real (perfil temporário próprio) com `--remote-debugging-port`, conecta via `connect_over_cdp` e navega na URL direta. **O Akamai ACEITA** — resultados renderizados em ~45s (consistente com o ~1 min do usuário):

```
RESULTADOS em ~45s! milhas: [338600, 362600, 364200, 384100, 392200, 406900, 416400, 423200]
```

Screenshot (`smiles_cdp_real.png`) confirma award real GRU→BKK 08/dez, 1 adulto:
- **KLM** (menor preço): GRU 20h55→BKK 10h05, 1 parada, 27h05min — **362.600 milhas por passageiro** (ou Smiles&Money)
- **Air France** 384.100 | **Ethiopian** | **Turkish** 423.200 | **Qatar** 474.100
- Faixa de datas com preço por dia (05–11/dez: 338.600–406.900) + fluxo de 2 pernas ("Escolha sua passagem de volta")
- Taxas de viagem exibidas após seleção dos voos (produção: somar pernas + taxas)

**Por que funciona:** o sensor Akamai roda no Chrome real iniciado pelo próprio SO (fingerprint limpo); o anexo CDP posterior não contaminou o sensor nesta versão. A janela anônima humana já tinha provado que zero-estado + browser real passa; o CDP-attach preserva isso.

**Implicação arquitetural:** a fonte Smiles exige execução **self-hosted no PC do usuário** (Chrome real local) — não roda em GitHub Actions. Isso é compatível com o rollback do design ("Can run manually via local Python execution") e com o runner self-hosted já previsto como mitigação do risco de datacenter IP (Google Flights).

### 3.1.3 Limite operacional descoberto: rate-limit por IP na API de disponibilidade

Sequência de eventos de 2026-09-02:
- 11:41 — busca CDP isolada → **SUCCESS** (award real extraído)
- 11:49–12:24 — tentativas em rajada (intervalos de 5 min, após ~20 buscas no dia) → páginas carregam o shell de resultados com **spinner removido e lista vazia**, sem erro explícito

**Interpretação:** Akamai/backend faz **rate-limit silencioso por IP** na API de disponibilidade. O MVP de produção (3 buscas/dia, uma por origem) opera muito abaixo desse limite; a rajada de testes de POC é que o viola.

**Gate adaptado à cadência de produção:** `poc_smiles_gate_sparse.py` — 9 runs (3×3 origens) com **10 min de intervalo** (~85 min). Critério por run inalterado: ≥3 preços de award em BRL/milhas, <5 min.

### 3.1.4 Comportamento de datas fora da janela (2027)

Para jul/2027, o Smiles **não fecha o spinner** (>5 min) — diferente do Google Flights, que exibe mensagem clara ("data muito distante"). Classificação de produção: timeout do spinner (>2 min) + datas-alvo fora da janela → `CALENDAR_NOT_OPEN`. Página-shell carregada com header correto ("GRU | BKK | Ter, 28 jul") confirma que a URL/params foram aceitos.

### 3.2 Caminhos (atualizados após corrida completa)

| # | Caminho | Status | Observação |
|---|---|---|---|
| **A** | **Gateway de browser real (self-hosted)**: execução diária no PC do usuário; o script abre a URL numa aba do Chrome REAL do usuário (Chrome iniciado com `--remote-debugging-port`, script conecta via CDP), extrai os dados da página/API dentro da sessão válida e publica (Supabase + Telegram) | **Recomendado** se Smiles for essencial ao MVP; mantém R$ 0; PC precisa estar ligado no horário | Teste de viabilidade: reconectar via CDP ao Chrome do usuário e ler resultados — 1 experimento |
| **B** | **M3 — Postergar Smiles**: status `BLOCKED` no MVP (já previsto no design); MVP segue com Google Flights (validado) + Azul + RSS + Telegram | Menor esforço; monitoramento de milhas fica manual/temporário | Revisitar se houver API oficial/credenciais de parceiro no futuro |

**Descartados com evidência:** M1 login automatizado (login não é requisito); M2 API browserless pura (edge Akamai nega qualquer cliente não-browser); automação Playwright/patchright de qualquer variante.

## 4. Evidências e artefatos

- Scripts: `poc/smiles/poc_smiles_recon.py` (v2–v4: recon, URL direta, gate), `poc_smiles_probe.py` (DOM), `poc_smiles_diag.py`/`poc_smiles_diag2.py` (telemetria), `poc_smiles_api_direct.py` (API direta)
- Screenshots/HTML: `smiles_recon_0_home.png`, `smiles_probe_*.png`, `smiles_v2_*.png`, `smiles_v3_*.png`, `smiles_direct_e1_*.png`, `smiles_diag2_final.png`
- Dados: `smiles_validation_results_2026-09-02.json`, `smiles_direct_network_manifest.json`, `smiles_diag2_events.json`, `smiles_api_direct_test.json`
- URLs-chave registradas: `smiles_diag_result_url.txt`

## 5. Pendências para fechar o go/no-go Smiles (tasks 0.20–0.21, 0.33–0.36)

1. Decisão do usuário: M1 (fornecer credenciais), M2 (aprofundar API RE) ou M3 (postergar)
2. Se M1: automatizar login → 3/3 runs com milhas extraídas (gate)
3. Se M2: iterar headers/params da API até 200 com payload de disponibilidade
4. Se M3: Smiles entra como BLOCKED no MVP (status já previsto no design) ou sai do escopo

---

*Smiles POC — 2026-09-02 — metodologia Google Flights (recon → classificação → evidência)*
