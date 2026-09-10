## 1. Experimento discriminante (GATE — nada muda em produção antes do desfecho)

- [x] 1.1 Criar `poc/smiles/probe_adults_discriminant.py`: RealChrome (patchright CDP), 3 runs espaçados `smiles_origin_spacing_s` — A: jul/27+GRU+1 adulto; B: dez/26+GRU+2 adultos; C: jul/27+GRU+2 adultos — usando `build_url()` com overrides; cada run registra estado final (renderizou/spinner), milhas extraídas, screenshot e body de evidência
- [ ] 1.2 Consolidar resultado em `poc/reports/smiles_adults_discriminant.json` + logs no console
- [x] 1.3 Rodar a matriz do experimento e classificar pela matriz de decisão (design D1) — 09/09: DESFECHO DRIVER_FIX_PLUS_ADULTS. Matriz 2×2 completa no dia (site sã, ~1h): patchright+1a ❌ (14:31), vanilla+2a ❌ (15:22), **vanilla+1a ✅ 24s (15:35)**, humano+1a ✅ 40s (15:20). Duas causas independentes: patchright nunca renderizou no Smiles (0 sucessos desde 68ac0e9 05-09; Azul usa vanilla default e funciona) E 2 adultos não renderiza nem com driver certo
- [ ] 1.3a Validação de confiabilidade D1b: run A1 (vanilla + 1 adulto — a config candidata de produção) em 3 manhãs consecutivas de sessão limpa, antes do ciclo das 10:00 (`PROBE_ONLY=A1`, ~5 min/dia). 09/09 conta como evidência, não como manhã (não foi pré-ciclo)
- [x] 1.4 Atualizar `poc/reports/smiles_poc_findings_2026-09-02.md`: correção da hipótese "flag Akamai" (inferência sem medição; o A/B de 09/09 — mesmo IP/URL, Chrome humano 40s vs patchright spin — não exige flag), descoberta do driver (patchright vs vanilla, troca silenciosa de 68ac0e9) e do adults, matriz 09/09, lógica invertida do discriminante de 06/09 corrigida
- [ ] 1.5 CHECKPOINT: ~~3/3 manhãs antes de tocar em produção~~ **SUPERADO pela decisão do usuário (09/09)**: gate antecipado — fix aplicado com ciclos reais como validação (D1b revisada no design). Rollback: `SMILES_ADULTS=2` + `driver="patchright"`

## 2. Mudança de produção (aplicada 09/09 — decisão do usuário: gate antecipado, ciclos reais validam)

- [x] 2.0 `src/scrapers/smiles.py`: reverter driver p/ `RealChrome(port=9301, driver="playwright")` — patchright não renderiza neste site (0 sucessos desde 68ac0e9; vanilla 2/2 históricos + matriz 09/09). Google mantém patchright (motivo original: degradação de tarifas); Azul já roda vanilla default — não tocar
- [x] 2.1 `src/config.py`: adicionar `smiles_adults: int = int(os.getenv("SMILES_ADULTS", "1"))` com comentário do motivo (busca 2 adultos → spinner eterno; evidência do experimento)
- [x] 2.2 `src/scrapers/smiles.py`: estender `build_url(origin, departure_date=None, return_date=None, adults=None)` com overrides opcionais; URL usa `smiles_adults`
- [x] 2.3 `src/scrapers/smiles.py`: quotes do Smiles registram `passengers=settings.smiles_adults` (em `_search_origin` e no fallback de exceção do `scrape`)
- [x] 2.4 `src/notifications/telegram.py`: linha de pontos E de combo do Smiles com sufixo "(por viajante)" — espelhando o padrão "/pessoa" do dinheiro
- [x] 2.5 `.env`: `SMILES_ADULTS=1` documentado (default do código já cobre)

## 3. Classificador com discriminante (aplicado 09/09)

- [x] 3.1 `src/scrapers/smiles.py`: `build_url` com overrides de datas/adults (reuso p/ busca-controle)
- [x] 3.2 `_classify_with_control`: no ramo de spinner eterno, busca-controle com datas ROLLING (hoje+90/97d — nunca sai da janela), 1 passageiro, mesma sessão; controle abre/responde → `CALENDAR_NOT_OPEN` (se partida >300 dias) senão `TIMEOUT`; controle não abre → `BLOCKED`; inferência pura por data removida
- [x] 3.3 Resultado da busca-controle registrado em `raw_sample["controle"]` (evidência p/ diagnóstico)

## 4. Probe de combo + validação

- [x] 4.1 `poc/smiles/probe_visual_combo.py`: passa as datas de controle (D, R) ao `build_url` (o "combo não renderiza em automação" era a URL de produção jul/27+2 adultos)
- [x] 4.2 Validação do caminho de produção (smoke test direto `scrape()`, sem Supabase/Telegram): **GRU SUCCESS, miles=301.500, AIR FRANCE, pax=1** (09/09 16:0x). Combo falhou de forma contida ("clientes Smiles não encontrada" — isolado por design, domínio da change add-smiles-money-combo). Ciclo completo GRU+VCP no real de amanhã 10h
- [x] 4.3 Validar mensagem do Telegram (offline, sem envio): "🎫 GRU: 301.500 pontos (por viajante) — AIR FRANCE"
- [ ] 4.4 Ciclos reais como validação de confiabilidade (design D1b, decisão 09/09): 3 ciclos SUCCESS consecutivos confirmam o fix; qualquer falha → discriminante (grupo 3, já em produção) decide antes de concluir; rollback trivial se o fix for o problema. Ao confirmar: atualizar tasks 0.20/12.5 do `flight-monitoring-mvp`
