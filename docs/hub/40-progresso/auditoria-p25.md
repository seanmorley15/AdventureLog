# Auditoria P2.5 — bugs e gaps da base AdventureLog

> Arquivo temporário (insumo das issues 2.5.4). Gerado em 2026-07-19.

## 2.5.1 — Stack local dev

- `docker compose -f docker-compose.dev.yml up -d` falhou na 1ª tentativa: container
  `web` (frontend) morreu com `exec: "sh": executable file not found in $PATH` — a imagem
  `ghcr.io/seanmorley15/adventurelog-frontend:latest` puxada do registry não tinha `sh`.
  **Resolvido:** `docker compose build web` (rebuild local a partir de `./frontend/`) e novo
  `up -d`. Depois disso: `web`, `db`, `server` de pé; frontend HTTP 200 em `:8015`, backend
  `/api/` HTTP 200 em `:8016`. **DoD atingido.**
  - Anotar como possível gap de doc: pré-voo do plano de execução não menciona que pode ser
    necessário `docker compose build web` antes do primeiro `up` se a imagem puxada do
    registry estiver desatualizada/incompatível com o compose local. Candidato a
    `backlog-p26` (doc) ou fix no `docker-compose.dev.yml`.

## 2.5.2 — Roteiro manual

**OSRM não disponível** (artefatos `.osrm*` não pré-processados nesta máquina — decisão
tomada com o Caio: pular otimizar-rota-real e testar o resto; reprocessar fica pra sessão
dedicada). Feature "Otimizar rota" ficou indisponível por *ausência de infra*, comportamento
esperado (I4) — não é bug.

Collection de teste criada: "Auditoria P2.5" (01–03/08/2026), 3 paradas reais no Dia 1
(Colosseo, Fontana di Trevi, Pantheon), via geocoding real (Nominatim).

### Anomalias encontradas

1. **BLOQUEANTE — "Otimizar rota" nunca encontra paradas otimizáveis via fluxo normal da UI.**
   - Repro: criar itinerário, adicionar 3+ paradas via menu "+" -> "Location" (único fluxo
     exposto na UI do Itinerário), clicar "Otimizar rota".
   - Resultado: toast "Menos de 2 paradas com coordenadas resolvíveis nesse grupo — nada
     para otimizar", mesmo com 3 paradas com coordenadas válidas.
   - Causa raiz (confirmada por leitura de código): `adventures/utils/itinerary.py::resolve_item_coordinates`
     só resolve coordenadas para itens cujo `content_type` é `Visit` ou `Lodging`
     (`itinerary.py` linhas 118–148). Mas o endpoint de criação
     (`adventures/views/itinerary_view.py::create`, linhas 63–202) recebe `content_type='location'`
     do fluxo "+" -> "Location" da UI (`CollectionItineraryPlanner.svelte`) e salva o
     `CollectionItineraryItem` com `content_type=Location` — o `Visit` que é criado como
     efeito colateral (linhas 160–202, pra exibir no calendário) **não** é o que fica linkado
     no item do itinerário. Resultado: `item.item` sempre resolve pra uma instância `Location`,
     nunca `Visit`, e `resolve_item_coordinates` retorna `None` sempre pra esse fluxo.
   - Impacto: a feature "Otimizar rota" (P2, já implementada e testada — 23/23 verde) fica
     inutilizável na prática pelo único caminho de UI disponível pra montar um dia de
     itinerário. Bloqueia o roteiro real de uso (adicionar paradas -> otimizar).
   - **Ação:** issue https://github.com/Caio-Coutinho01/Trilho/issues/1 (`bloqueante`).
     **Corrigido em 2.5.5** desta mesma sessão: `resolve_item_coordinates` passou a resolver
     `Location` diretamente (tem `latitude`/`longitude` próprios). Teste de regressão
     `test_optimize_resolves_stops_added_via_the_location_quick_add_flow` adicionado.
     Suíte `adventures routing`: 24/24 verde.

2. **Backlog — reverse geocoding retorna localidade errada (cidade/label) pra coordenadas
   de Roma centro.**
   - Repro: criar Location via busca "Colosseo Roma" (ou Fontana di Trevi, ou Pantheon) ->
     selecionar resultado -> Continue.
   - Resultado: campo "Location Display Name" e a tag de cidade em "Location Selected"
     mostram **"Arcinazzo Romano, Lazio, IT"** pras 3 paradas testadas, todas em Roma centro
     (coordenadas corretas: 41.890942/12.491903, 41.900978/12.483285, 41.898616/12.476833 —
     Arcinazzo Romano fica a ~70 km de Roma).
   - Nome do local (`Name`) em si vem correto (ex.: "Piazza del Colosseo", "Oceano",
     "Billetteria Pantheon" — nomes de POI do OSM), só o componente de
     cidade/label do reverse-geocode está errado, de forma consistente (mesmo valor pras 3
     coordenadas diferentes) — sugere bug na normalização/cache da chamada de reverse
     geocode, não coincidência.
   - Impacto: cosmético (endereço exibido errado), não bloqueia uso, mas é dado factual de
     lugar incorreto — relevante pro princípio arquitetural do projeto (I1: nunca inventar
     fato geoespacial) mesmo não sendo LLM a fonte aqui.
   - **Ação:** issue https://github.com/Caio-Coutinho01/Trilho/issues/2 (`backlog-p26`).

3. **Não testado / precisa validação manual humana — reorder drag-and-drop.**
   - Tentativa de automação via Claude-in-Chrome (`left_click_drag`) não moveu os cards
     (provável limitação do simulador de mouse contra a lib de sortable, que costuma exigir
     sequência de mousedown -> moves incrementais -> mouseup pra distinguir de um clique).
   - Não é uma anomalia confirmada — só não foi possível confirmar via automação. Pedir ao
     Caio pra testar manualmente reorder de paradas dentro do mesmo dia.

4. **Não testado — notas/checklists, logout/login novamente, persistência após
   `docker compose restart`.**
   - Sessão de browser automatizado ficou instável (screenshots travando/timeout repetido na
     extensão Claude-in-Chrome) antes de cobrir esses passos do roteiro. Ficam pendentes —
     ou retomados numa sessão nova de browser, ou validados manualmente pelo Caio.

## 2.5.3 — Suíte de testes existente

- `docker compose -f docker-compose.dev.yml exec server python manage.py test adventures routing --noinput`:
  **23/23 verde** (`Ran 23 tests in 2.071s` / `OK`), baseline mantida (ADR 001 §7). O comando
  reporta erro no *teardown* do banco de teste (`ObjectInUse`, sessões concorrentes de
  threads de background de geocode ainda conectadas) — não afeta o resultado dos 23 testes,
  que já tinham passado (`OK` aparece antes do traceback de teardown). Falha pré-existente de
  infra de teste, não relacionada à Fase 1; não bloqueante.
- `docker compose -f docker-compose.dev.yml exec web sh -c "cd /app && pnpm run check"`
  (equivalente a `npm run check`): **0 erros, 0 warnings** (svelte-check).

## Resumo de bloqueantes até aqui

| # | Severidade | Resumo | Destino |
|---|---|---|---|
| 1 | Bloqueante | Otimizar rota nunca acha paradas (bug de content_type Location vs Visit) | [#1](https://github.com/Caio-Coutinho01/Trilho/issues/1) — **corrigido em 2.5.5** |
| 2 | Backlog | Reverse geocode retorna cidade errada (Arcinazzo Romano) pra Roma centro | [#2](https://github.com/Caio-Coutinho01/Trilho/issues/2) |
| 3 | Pendente | Reorder drag-and-drop — precisa validação manual | pedir ao Caio |
| 4 | Pendente | Notas/checklist/logout-login/persistência restart — não cobertos nesta sessão | retomar |
