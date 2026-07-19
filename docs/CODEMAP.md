# CODEMAP — Trilho (fork de AdventureLog v0.12.1)

Gerado em 2026-07-19 a partir de inspeção real do código clonado (tag `v0.12.1`,
commit `42785f1`). Objetivo: dar a qualquer sessão futura (humana ou agente) um mapa
confiável de onde as coisas vivem, sem precisar re-explorar o repo do zero.

## 1. Stack confirmada

- **Backend**: Django 5.2 + Django REST Framework + django-allauth (auth) +
  `django.contrib.gis` (PostGIS). Fica em `backend/server/`.
- **Frontend**: SvelteKit + TailwindCSS/DaisyUI + componentes de mapa em maplibre.
  Fica em `frontend/`.
- **Orquestração**: `docker-compose.yml` (prod), `docker-compose.dev.yml` (dev),
  `docker-compose-traefik.yaml` (prod com Traefik). Serviços do dev compose: `web`
  (frontend), `db` (Postgres/PostGIS), `server` (Django).

## 2. Apps Django (`backend/server/`)

`INSTALLED_APPS` relevantes: `adventures`, `worldtravel`, `users`, `integrations`
(`achievements` existe no código mas está **desativado** — comentado em `settings.py`
linha 73, "Not done yet, will be added later").

`adventures/` é o app central. Estrutura:
- `models.py` — 17 modelos: `Location`, `Visit`, `Collection`, `CollectionInvite`,
  `Transportation`, `Note`, `Checklist`/`ChecklistItem`, `ContentImage`/`ContentAttachment`,
  `Category`, `Lodging`, `Trail`, `Activity`, **`CollectionItineraryDay`**,
  **`CollectionItineraryItem`** (ver seção 3 — achado importante).
- `views/` — não é um arquivo único, é um pacote com 1 arquivo por domínio:
  `collection_view.py`, `location_view.py`, `itinerary_view.py`, `recommendations_view.py`,
  `generate_description_view.py`, `import_export_view.py`, `stats_view.py`, etc.
- `urls.py` — `DefaultRouter` do DRF registrando cada viewset (`/api/locations/`,
  `/api/collections/`, `/api/recommendations/`, `/api/itineraries/`,
  `/api/itinerary-days/`, `/api/generate/`, `/api/reverse-geocode/`, ...).
- `geocoding.py` — wrappers para busca de lugares (Google Places e OSM/Nominatim).
- `serializers.py` — 1 serializer por modelo, ~1060 linhas.

`main/urls.py` é o roteador raiz: monta `adventures.urls` e `worldtravel.urls` sob
`/api/`, auth do allauth sob `/auth/`, admin, docs Swagger em `/docs/`.

## 3. Achado importante — releia antes de planejar Fase 1/3

O AdventureLog **já tem** boa parte do que o blueprint descreve como "a construir":

- **Itinerário com dias e ordenação manual já existe**:
  `CollectionItineraryDay` (dia dentro de uma collection, com data e nome) +
  `CollectionItineraryItem` (item genérico — `Visit`, `Transportation`, `Lodging`, `Note` —
  ligado a um dia via `GenericForeignKey`, com campo `order` para ordem manual e
  `is_global`/`date` para itens que não têm dia fixo). Isso é o esqueleto de dados que a
  Fase 1 (rota otimizada) precisaria de qualquer forma — não é preciso desenhar esse
  schema do zero, só adicionar o algoritmo de otimização que popula/reordena o campo
  `order`.
- **Recomendações já existem** (`recommendations_view.py`, 29KB): busca lugares via
  **Overpass API** (OSM) e **Google Places API** (se `GOOGLE_MAPS_API_KEY` estiver setada),
  calcula um `quality_score` determinístico (rating, nº de reviews em escala log, distância
  via `geopy.distance.geodesic`, status verificado, fotos, horário de funcionamento) — sem
  LLM nenhum. Isso é praticamente o que a Fase 3 do blueprint pedia. O que falta ali é
  filtrar por restrições do usuário (dietéticas, acessibilidade, etc.) e a camada de
  julgamento qualitativo do LLM em cima — não a coleta de dados.
- **Descrição de lugar via `GenerateDescription`** não usa LLM — busca na API da Wikipedia
  (`generate_description_view.py`), com matching por `SequenceMatcher` e filtro de página
  de desambiguação. Também sem LLM.
- **O que genuinamente NÃO existe** (confirmado por grep em todo `backend/` e `frontend/`
  por `optimiz|tsp|osrm|route`): nenhum motor de roteirização, nenhum solver de TSP,
  nenhuma integração OSRM. `requirements.txt` não tem `networkx`, `ortools`, nem cliente
  OSRM. A Fase 1 do blueprint (rota multi-parada otimizada) continua 100% válida e
  necessária — é o maior gap real entre o AdventureLog e o Wanderlog.

**Implicação prática**: o P1 (pesquisa/gate de infra) do blueprint deveria gastar menos
tempo desenhando schema de itinerário/recomendação do zero e mais tempo decidindo (a)
qual motor de rota usar (OSRM local vs. serviço gerenciado) dado o invariante I4, e (b)
como o algoritmo de otimização escreve de volta no campo `order` de
`CollectionItineraryItem` sem quebrar a UI de drag-and-drop que já existe.

## 4. Frontend (`frontend/src/`)

- `routes/` — roteamento por pasta do SvelteKit. Principais: `collections/[id]`,
  `locations/[id]`, `map/`, `worldtravel/`, `calendar/`, `settings/`, `login`/`signup`.
  Existe `routes/api/[...path]` e `routes/auth/[...path]` — proxies genéricos.
- `lib/components/` — mapas em `ClusterMap.svelte`, `map/FullMap.svelte`,
  `collections/CollectionMap.svelte`, `shared/LocationSearchMap.svelte`; UI de
  recomendação já tem componente próprio: `CollectionRecommendationView.svelte`.
- `lib/config.ts` — `appTitle` (hoje `'AdventureLog'`) e `versionChangelog`. Único ponto
  central de nome do app — mas não é o único lugar com o texto hardcoded (ver seção 5).
- **Comunicação frontend↔backend**: não é proxy embutido do SvelteKit por padrão — o
  `hooks.server.ts` faz `event.fetch` direto pro backend (`PUBLIC_SERVER_URL`, default
  `http://localhost:8000` fora do compose, `http://server:8000` dentro dele) para validar
  sessão (`/auth/user-metadata/`) a cada request. Chamadas de dados das páginas usam fetch
  direto ao mesmo `PUBLIC_SERVER_URL` (server-side, via `+page.server.ts`) ou client-side
  contra o backend com cookie de sessão. CSRF: endpoint dedicado `/csrf/` no backend.

## 5. Onde está o nome "AdventureLog" hardcoded (achados para rebranding)

Texto visível ao usuário, fora de `config.ts`:
- `frontend/src/routes/+layout.svelte` linhas 88 e 91 — `<title>` e `<meta description>`.
- `frontend/src/lib/components/Navbar.svelte` linhas 206–207 — `alt` do logo e texto da
  navbar.
- `backend/server/main/settings.py` linha 239 — prefixo de assunto de e-mail de convite
  (`INVITATIONS_EMAIL_SUBJECT_PREFIX`).
- Logo/ícones em `brand/` (`adventurelog.png`, `adventurelog.svg`, `banner.png`) e
  `frontend/static/favicon.png` — não trocados nesta passada (é estética, fora do escopo
  "rebranding mínimo" do Passo 0).

## 6. Variáveis de ambiente (`.env.example` na raiz)

Já documentado com comentários no próprio arquivo. Pontos que importam para o roadmap:
- `GOOGLE_MAPS_API_KEY` (opcional) — ativa o Google Places dentro de
  `recommendations_view.py`. Sem ela, cai só no Overpass/OSM.
- Nenhuma env var de LLM existe hoje (nem OpenAI, nem Anthropic) — a Fase 4 (assistente)
  vai precisar introduzir isso do zero, respeitando o princípio arquitetural central
  (dados reais primeiro, LLM só interpreta/explica).
- Nenhuma env var de motor de rota (OSRM) existe — confirma que o `docker-compose.osrm.yml`
  opcional do invariante I4 é trabalho novo, não ajuste de algo existente.

## 7. Não verificado neste passo

- Login/criação de itinerário end-to-end não foi validado rodando o app — o ambiente
  desta sessão não tem Docker instalado, então a validação funcional fica para você rodar
  localmente (ver runbook entregue no chat).
- Testes existentes (`adventures/tests.py`, só 2KB — cobertura provavelmente baixa) não
  foram executados.
