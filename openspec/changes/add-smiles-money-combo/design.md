## Context

O scraper do Smiles (src/scrapers/smiles.py) hoje captura apenas o valor **só-milhas** do card mais barato (regex flexível "X milhas" + extração por cartão com assinatura "Mais detalhes"). O print do usuário (`poc/reports/smiles_completo.png`) revela que cada card tem um botão **"Selecionar tarifa"** que abre um quadro com duas seções — **"Use milhas"** e **"Pague com Smiles & Money"** — e que a seção "Pague com Smiles & Money" tem uma caixa **"Combinações para clientes Smiles a partir de"** com botão **"Combinar"**, que abre um **slider** de milhas com o valor em reais correspondente. É a alternativa de menor desembolso de milhas na rota (combos a partir de ~19.300 milhas + R$ 7.360) e hoje não é capturada.

## Goals / Non-Goals

**Goals:**
- Capturar a combinação milhas + dinheiro do card do voo mais barato: **maior quantidade de milhas < 210.000** (configurável) e o **valor em reais** correspondente
- Exibir no Telegram **os dois valores** (só-milhas E combo), sem descartar o existente
- Persistir em `daily_flight_quotes` nos campos já existentes (`hybrid_miles`, `cash_component_brl`) — sem mudança de schema
- Evidência automática (screenshot + texto) quando o fluxo do combo falhar, sem invalidar o só-milhas

**Non-Goals:**
- Comprar/reservar (a interação termina na leitura do valor; "Confirmar" NÃO é clicado)
- Combinacoes do "Clube Smiles" (caixa superior — exige assinatura; fora do MVP)
- Tarifa para 2 adultos somada (valores capturados são por viajante, como exibidos)
- Mudança de schema do Supabase

## Decisions

### 1. Navegação do combo por assinaturas de texto do card/painel

**Decision:** localizar o card do voo mais barato pelo texto do piso já extraído (número das milhas), clicar **"Selecionar tarifa"** dentro dele; aguardar o quadro pelo texto **"Pague com Smiles & Money"**; clicar o **"Combinar"** do quadro **"Combinações para clientes Smiles a partir de"** (inferior direito — o de clientes, não o de Clube); aguardar o quadro do slider por **"Combinar do seu jeito"**/"Confirmar".

**Rationale:** seletores por texto sobrevivem a mudanças de classe CSS (lições das POCs); os textos do print são estáveis na UI.

**Alternatives considered:** seletores por classe CSS → quebram a cada deploy do MFE (padrão observado no Smiles).

### 2. Slider: posicionar no maior combo < 210k e ler o reais

**Decision:** o slider é lido como intervalo de combinações (valor em milhas ⇄ valor em reais, inversamente proporcionais). O scraper identifica o **maior passo de milhas < `SMILES_COMBO_MAX_MILES`** (default 210.000) e lê o **valor em reais exibido abaixo do slider** para essa posição.

**Implementation notes:**
- O controle expõe a posição atual como texto ("193.100 milhas" + "+ R$ 3.680,00" no print) — a leitura é feita do texto do quadro após cada ajuste
- Ajuste do slider: teclado (setas ←/→ no handle focado) com verificação do texto após cada passo — mais determinístico que arrastar com mouse
- Se o limite 210k cair entre dois passos, seleciona o **maior passo abaixo** dele

**Alternatives considered:** arrastar com mouse (mouse.move) → menos determinístico; calcular proporção e setar via JS → frágil a componentes customizados.

### 3. Threshold 210k configurável e por fonte

**Decision:** `SMILES_COMBO_MAX_MILES` (default 210000) no `.env`/config — substitui, para o Smiles, o placeholder de 120k da Decisão 7 do MVP (que permanece para o Azul).

**Rationale:** o valor veio da análise do usuário sobre o que é "acessível" para a viagem; desacoplar por fonte permite calibrar cada programa.

### 4. Falha do combo ≠ falha da fonte

**Decision:** o fluxo do combo roda **após** a captura e persistência do só-milhas; qualquer falha (painel/slider não encontrado em 15s por etapa) registra o estado em `raw_sample` (screenshot + texto) e deixa `hybrid_miles`/`cash_component_brl` vazios. O status da fonte permanece o do só-milhas.

**Rationale:** o combo é um enriquecimento; quebrar a fonte por causa dele repetiria o erro histórico de declarar falha total quando um sub-fluxo falha.

## Risks / Trade-offs

- **Slider é componente customizado**: o ajuste por teclado pode não ser suportado → fallback: clicar na posição do trilho proporcional ao valor-alvo (coordenadas do trilho)
- **Combo só existe se houver assentos Smiles & Money no voo**: cards sem combo ficam sem o quadro → tratado como ausência (campos vazios)
- **Tempo do ciclo aumenta** (~30-60s por origem para o quadro do combo) → aceito (limite 60 min)
- **Clube Smiles vs clientes**: o print mostra caixas distintas; o scraper mira a de **clientes** (inferior direita). Se a assinatura de texto mudar, a evidência salva permite diagnóstico

## Migration Plan

1. Implementar a fase de combo em `src/scrapers/smiles.py` (após extração do só-milhas, mesma sessão CDP)
2. `SMILES_COMBO_MAX_MILES` no `.env`/`.env.example`/config
3. Linha do combo no Telegram (`src/notifications/telegram.py`, seção Smiles)
4. Teste com datas de controle (dez/2026) comparando com o print do usuário
5. Evidência de falha isolada (combo sem painel) validando que o só-milhas segue intacto

## Open Questions

- O quadro "Combinações para clientes Smiles" só aparece para rotas/voos com inventory Smiles & Money — tratar ausência como "sem combo" (campos vazios), não erro
