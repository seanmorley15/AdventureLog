# Blueprint — Trilho: fork do AdventureLog rumo a recursos do Wanderlog

> Plano de construção multi-sessão. Cada passo é auto-contido: um agente novo consegue executá-lo
> sem ler os passos anteriores. Gerado em 2026-07-18 com o modelo mais forte (planejamento);
> execução recomendada com Sonnet, exceto onde marcado.

---

## 0. Contexto global (ler antes de qualquer passo)

**Objetivo.** Forkar o [AdventureLog](https://github.com/seanmorley15/AdventureLog) (v0.12.1,
GPL-3.0) e evoluí-lo na direção de recursos do Wanderlog: rota multi-parada otimizada, modo
offline, recomendação de lugares com restrições e assistente de IA. Projeto pessoal, uso
ocasional, sem infraestrutura cara.

**Stack confirmada no repositório oficial** (verificada em 2026-07-18):
- Backend: Django + Django REST Framework + PostGIS + AllAuth (dir `backend/`)
- Frontend: SvelteKit + TailwindCSS + DaisyUI + svelte-maplibre (dir `frontend/`)
- Orquestração: `docker-compose.yml` (prod), `docker-compose.dev.yml` (dev), `docker-compose-traefik.yaml`
- Ignorar qualquer referência de terceiros a "React + Node" — é incorreta.

**Infra.** VPS Hetzner já em uso hospedando o SecretarIA. O Trilho coexiste nela — nunca a
substitui. Todo deploy tem como invariante "SecretarIA continua no ar".

**Princípio arquitetural central (aplicar em toda decisão técnica).**
Dados reais + algoritmo determinístico fazem o trabalho pesado. O LLM só interpreta intenção,
aplica julgamento qualitativo sobre restrições e explica o resultado. **Nunca** deixar o LLM
calcular ou inventar dado factual/geoespacial (distância, endereço, coordenada, horário de
funcionamento) que deveria vir de uma API estruturada (OSRM, Overpass, PostGIS).

**Fora de escopo (não implementar em hipótese alguma).**
Importação automática de reservas via email (parser de email, OAuth Gmail/Outlook).

**Critério de MVP pronto.**
"Consigo usar o Trilho numa viagem real, offline, do início ao fim" — deploy funcional na VPS
Hetzner, coexistindo com o SecretarIA. Não basta rodar localmente em dev.

**Licença.** AdventureLog é GPL-3.0. O fork permanece GPL-3.0; manter LICENSE e atribuição.

### Invariantes (verificar ao final de TODO passo)

- I1. LLM nunca é fonte de cálculo geoespacial ou fato verificável de lugar (grep por chamadas de
  LLM que retornem distância/coordenada é parte do review de cada PR das fases 3–4).
- I2. Testes do algoritmo de otimização (Fase 1) permanecem verdes.
- I3. Após qualquer deploy, SecretarIA responde normalmente (health check documentado no Passo 3).
- I4. `docker compose up` **puro** do repo continua funcionando após cada fase. Serviços novos
  que dependem de artefatos fora do repo (OSRM e seus arquivos pré-processados) vivem em
  override opcional (`docker-compose.osrm.yml`), nunca no compose principal; o backend degrada
  graciosamente quando a variável do serviço (ex.: `OSRM_URL`) não está setada.
- I5. Fora de escopo continua fora de escopo.
- I6. Toda fase que altera schema entrega migração Django versionada (`makemigrations` +
  `migrate` limpo), e o deploy (Passo 3 e seguintes) aplica `migrate` explicitamente.
- I7. Todo endpoint novo entra com: rota registrada no `urls.py`, `permission_classes`
  (autenticado + dono do recurso) e CSRF/CORS conferidos conforme o modo de fetch
  (server-side SvelteKit vs. chamada direta do browser). Variável de ambiente nova entra no
  `.env.example` com default seguro/opcional e no inventário de env vars do `docs/deploy.md`.

### Protocolo entre sessões

- Cada fase = 1 PR. Gate de `/verify` (ecc:verification-loop) antes de considerar a fase fechada.
- Ao encerrar sessão no meio de um passo: `/save-session`. Ao retomar: `/resume-session`.
- Modelos: **Opus** para os passos marcados `[tier: strongest]` (decisões de arquitetura/infra) e
  para revisões; **Sonnet** para execução dos demais.
- Git: fork no GitHub do usuário, branch por fase (`fase-1-rota`, `fase-2-offline`, ...), PR
  contra o `main` do fork. Manter remote `upstream` apontando para seanmorley15/AdventureLog.

### Grafo de dependências

```
P0 (bootstrap) → P1 (pesquisa/gate infra) → P2 (Fase 1: rota) → P3 (deploy v0 na VPS)
                                                                   ├→ P4 (Fase 2: offline/PWA)
                                                                   └→ P5a → P5b (Fase 3: recomendações)   [P4 ∥ P5]
P2 + P5b → P6 (Fase 4: assistente)
P4 + P6 → P7 (validação MVP em viagem real)
```

**P6 depende de P2 e P5, NÃO de P4** — o assistente orquestra otimizador e recomendações;
offline é ramo paralelo que só bloqueia o P7.

**Paralelismo P4 ∥ P5 com ressalva:** é paralelo no backend/lógica, mas ambos tocam os
componentes Svelte da tela de parada/itinerário (P4: indicador offline + hidratação IndexedDB;
P5b: painel de sugestões). Se rodar em paralelo, isolar em componentes novos
(`<OfflineIndicator>`, `<StopSuggestionsPanel>`) sem editar o mesmo bloco do componente de
parada, ou serializar o merge do frontend. Para dev solo em sessões sequenciais, a ordem
P4 → P5 é a recomendada (offline é pré-requisito do critério de MVP; recomendações não são).

---

## Passo 0 — Bootstrap: clonar e rodar o AdventureLog local

**[tier: default | serial | sem PR — commit direto no main do fork]**

**Context brief.** A pasta do projeto (`Trilho/`) está vazia. O AdventureLog é um monorepo com
`backend/` (Django/DRF/PostGIS), `frontend/` (SvelteKit) e três docker-composes na raiz. Nada
pode ser planejado em cima de suposição: este passo coloca o sistema rodando e produz um codemap
real.

**Tarefas.**
1. Criar fork `Trilho` no GitHub a partir de seanmorley15/AdventureLog (manter GPL-3.0).
2. Clonar o fork na pasta do projeto; adicionar remote `upstream`.
3. Copiar `.env.example` → `.env`, ajustar variáveis mínimas, subir com
   `docker compose -f docker-compose.dev.yml up` (fallback: `docker-compose.yml`).
4. Validar: login, criar uma collection/itinerário com 3+ locais, ver no mapa.
5. Gerar codemap curto (`docs/CODEMAP.md` do fork): apps Django existentes, modelos principais
   (Location/Adventure, Collection/Itinerary, Visit), rotas DRF, estrutura de rotas SvelteKit,
   como o frontend fala com o backend (proxy? fetch direto?), onde vive o mapa (svelte-maplibre).
6. Rebranding mínimo: nome "Trilho" no frontend (título/logo). Nada além disso — não gastar
   sessão com estética.

**Verificação.** App abre no browser, itinerário criado persiste após restart dos containers,
`docs/CODEMAP.md` existe e cita arquivos reais.

**Saída.** Fork rodando local + codemap. `/save-session`.

**Rollback.** Trivial — apagar containers/volumes e re-clonar.

---

## Passo 1 — Gate de pesquisa: a VPS comporta isso? (search-first)

**[tier: strongest | serial | go/no-go — nenhum código antes deste passo fechar]**

**Context brief.** Decisão já tomada: Distance Matrix via **OSRM self-hosted** (Docker), não
Google Routes — zero fricção de cartão/cota. Mas "gratuito" ≠ "sem custo de infra": OSRM com
extract de país único e algoritmo MLD tipicamente exige 2–4 GB de RAM (extract do Brasil é maior
que a média europeia — verificar número real, não assumir). A VPS Hetzner já hospeda o SecretarIA.
Este passo decide se tudo cabe ANTES de escrever qualquer código da Fase 1.

**Tarefas.** (usar skill `ecc:search-first` / pesquisa web para specs e requisitos atuais)
1. Auditar a VPS: modelo Hetzner, vCPU, RAM total, disco total/livre; consumo real atual do
   SecretarIA (`docker stats`, `free -h`, `df -h`). Registrar números no ADR.
2. Dimensionar OSRM para a região de uso real (perguntar ao usuário: Brasil inteiro? um estado?
   país da próxima viagem?). **Não confiar na faixa "2–4 GB" de extracts europeus — MEDIR:**
   rodar `osrm-extract` + `osrm-partition` + `osrm-customize` do extract escolhido **em máquina
   local** (esse é o caminho default; a VPS só recebe os arquivos processados), anotando pico de
   RAM de cada etapa, tamanho em disco dos arquivos `.osrm*` resultantes (Brasil inteiro pode
   ocupar dezenas de GB) e RSS do `osrm-routed` em runtime com MLD. Preferir extract de
   estado/região a Brasil inteiro, salvo necessidade real da viagem.
3. Somar: OSRM runtime + Django + PostGIS + SvelteKit + SecretarIA — **RAM e disco**. Margem
   mínima de 20% em ambos.
4. Decidir e registrar em `docs/adr/001-infra-osrm.md`:
   - **Cabe** → prosseguir.
   - **Não cabe** → escolher explicitamente: upgrade de plano Hetzner (custo/mês), extract menor
     (estado/região em vez de país), pré-processamento offline + runtime enxuto, ou plano B
     (ex.: OSRM sob demanda só durante viagens). Não prosseguir sem decisão registrada.
5. Ler o `docker-compose.yml` oficial do AdventureLog e o codemap do Passo 0; esboçar onde o
   serviço OSRM entra no compose e onde o cliente OSRM entra no backend Django (novo app
   `routing/`? serviço em app existente?). Registrar o esboço no mesmo ADR.

**Verificação.** `docs/adr/001-infra-osrm.md` existe, contém números medidos (não estimados) da
VPS e decisão explícita go/no-go com alternativa escolhida se "no-go".

**Saída.** Gate liberado (ou plano B decidido). `/save-session`.

**Rollback.** N/A (passo só de pesquisa).

---

## Passo 2 — Fase 1: otimização de rota multi-parada (PR #1)

**[tier: default (Sonnet) | serial | branch `fase-1-rota`]**

**Context brief.** O AdventureLog já tem itinerários (collections) com locais ordenados manualmente
e mapa via svelte-maplibre. Falta: "otimize a ordem das minhas paradas". Arquitetura decidida:
OSRM self-hosted fornece a matriz de distâncias/durações (endpoint `/table`); um algoritmo
determinístico em Python (nearest neighbor para solução inicial + 2-opt para refinamento) resolve
o TSP aproximado por cima da matriz. Nenhum LLM envolvido nesta fase. Consultar
`docs/adr/001-infra-osrm.md` para a decisão de dimensionamento e o esboço de integração.

**Tarefas.**
1. Adicionar serviço `osrm` em **override opcional** `docker-compose.osrm.yml` (imagem oficial
   `osrm/osrm-backend`, MLD), subido com `-f docker-compose.yml -f docker-compose.osrm.yml` —
   NUNCA no compose principal, pois os arquivos `.osrm*` pré-processados não estão no repo e
   `docker compose up` puro tem de continuar verde (I4). Documentar em `docs/osrm.md` o comando
   de pré-processamento e a cadência de re-extract (manual, sob demanda antes de viagem nova em
   região não coberta).
2. Backend: módulo `routing/` com
   - cliente OSRM (`/table` para matriz N×N; tratar erro/timeout — OSRM fora do ar ou
     `OSRM_URL` ausente não pode derrubar o resto do app: feature "otimizar" apenas indisponível.
     Atenção: `/table` tem `max-table-size` default 100 coordenadas por chamada; para 1 origem ×
     M destinos usar `sources=0` numa chamada só);
   - `optimize_order(matrix, fixed_start=None, fixed_end=None) -> list[int]`: nearest neighbor
     + 2-opt, puro e determinístico (sem I/O — testável isolado);
   - endpoint DRF `POST /api/itineraries/{id}/optimize/` que lê as paradas, chama OSRM, roda o
     algoritmo e retorna a nova ordem + duração total estimada (sem persistir; persistir só com
     confirmação do usuário via PATCH existente de reordenação). Cumprir I7: rota registrada,
     permissão de dono do itinerário, CSRF conforme modo de fetch.
3. Frontend: botão "Otimizar rota" na tela do itinerário → preview da nova ordem no mapa +
   duração antes/depois → confirmar/descartar.
4. **Testes (foco desta fase, conforme decidido):** cobertura no `optimize_order` em si —
   casos com N paradas conhecidas e resultado esperado (ex.: 4 pontos em quadrado, ordem ótima
   conhecida; caso com início fixo; caso degenerado N≤2; matriz assimétrica). Teste do endpoint
   com OSRM mockado. NÃO buscar cobertura ampla do resto do sistema.

**Verificação.** `pytest` do módulo routing verde; com OSRM local no ar, otimizar um itinerário
real de 5+ paradas retorna **permutação válida das N paradas** cuja duração = soma das arestas
da matriz OSRM na ordem proposta, e em ao menos 1 caso real a duração otimizada ≤ a manual;
`docker compose up` **puro** (sem o override OSRM) continua verde. Gate `/verify` antes do merge.

**Saída.** PR #1 mergeado no main do fork. `/save-session`.

**Rollback.** Reverter o PR. OSRM é serviço isolado no compose — removê-lo não afeta o core.

---

## Passo 3 — Deploy v0 na VPS Hetzner (coexistindo com SecretarIA)

**[tier: default | serial | sem PR de código — infra + docs]**

**Context brief.** Critério de MVP exige deploy real, não localhost. A VPS já roda o SecretarIA;
o Passo 1 confirmou que os recursos comportam a soma. Deploy cedo (logo após a primeira feature)
para que cada fase seguinte seja validada em produção, não só em dev.

**Tarefas.**
1. Levantar como o SecretarIA está servido (reverse proxy existente? Traefik? Nginx? Caddy?
   portas ocupadas?). Integrar o Trilho ao mesmo proxy — não subir um segundo proxy conflitante.
   O repo oferece `docker-compose-traefik.yaml` como referência se Traefik já for o caso.
2. Subir Trilho (backend + frontend + PostGIS + OSRM) em subdomínio próprio com HTTPS.
3. Copiar para a VPS os arquivos OSRM já pré-processados (se a decisão do Passo 1 foi
   pré-processar fora da VPS).
4. Script/checklist de deploy reprodutível em `docs/deploy.md` (incluindo backup do Postgres —
   o repo tem `backup.sh` como base — e passo explícito de `python manage.py migrate` a cada
   deploy, I6; manter aqui o inventário de variáveis de ambiente novas, I7).
5. Health checks documentados: URL do Trilho responde; URL do SecretarIA responde; uso de RAM
   pós-deploy registrado no `docs/deploy.md` para comparar com a previsão do ADR 001.

**Verificação.** Otimizar um itinerário no Trilho **em produção**; SecretarIA segue no ar (I3);
RAM da VPS com margem ≥ a prevista no ADR.

**Saída.** Trilho v0 público (para o usuário). `/save-session`.

**Rollback.** `docker compose down` do stack Trilho na VPS restaura o estado anterior; SecretarIA
não compartilha containers com o Trilho.

---

## Passo 4 — Fase 2: modo offline / PWA (PR #2)

**[tier: default | paralelizável com P5 | branch `fase-2-offline`]**

**Context brief.** O objetivo do produto: levar o roteiro no bolso sem sinal. SvelteKit no
frontend; usar `@vite-pwa/sveltekit` (ou equivalente compatível com a versão de SvelteKit/Vite do
repo — confirmar versão antes de instalar). "Adicionar à tela de início" já resolve o pedido de
"app sem loja de aplicativos" — não é entrega separada. Escopo offline: **ler** o itinerário
completo (paradas, ordem, notas, mapa da região) e **editar** campos simples, com sync ao voltar
a rede. Consultar `docs/CODEMAP.md` (Passo 0) para o modelo de auth e como o frontend busca dados.

**RISCO CENTRAL DA FASE (resolver antes de escrever o service worker):** o AdventureLog usa
SvelteKit com SSR — telas que carregam dados via `+page.server.ts`/`hooks.server.ts` (fetch
server-side com cookie de sessão AllAuth) **não renderizam sem o servidor Node**. Instalar o
plugin PWA não resolve isso sozinho.

**Tarefas.**
0. Mapear no CODEMAP se as telas de itinerário usam `+page.server.ts` (SSR) ou `+page.ts`
   (universal/client). Se SSR com fetch server-side: definir estratégia de shell offline —
   rota client-rendered dedicada para o itinerário (`ssr = false`), `navigateFallback` no
   service worker, e hidratação a partir do IndexedDB em vez do `load` server-side. Definir
   também **como a fila de mutações se autentica** no replay direto do browser contra o DRF:
   sessão-cookie com chamada direta ao `/api` (conferir CSRF/`SessionAuthentication` e
   CORS/same-origin) OU token DRF guardado no IndexedDB. Registrar as duas decisões em
   `docs/adr/002-offline-sync.md` ANTES de qualquer código desta fase.
1. Service worker via `@vite-pwa/sveltekit`: cache de assets (shell do app) + manifest PWA
   (ícone, nome Trilho, standalone). Chamar `navigator.storage.persist()` no boot e registrar o
   resultado — **iOS/WebKit despeja IndexedDB/Cache Storage após ~7 dias sem uso do site**, o
   que pode apagar o roteiro no meio da viagem. Mitigação obrigatória: re-hidratar o snapshot a
   cada acesso online + aviso na UI "abra o app com internet antes de viajar".
2. IndexedDB para dados do itinerário: ao abrir um itinerário online, persistir snapshot completo
   (paradas ordenadas, notas, checklists, coordenadas). Estratégia de tiles de mapa offline:
   avaliar cache de tiles da região do itinerário (bounding box) com limite de armazenamento; se
   inviável no tempo da fase, degradar para lista/ordem sem mapa e registrar como limitação.
3. Fila de mutações offline + sync ao reconectar. **Resolução de conflito: last-write-wins**,
   decidida agora e registrada em `docs/adr/002-offline-sync.md` (incluir: por que LWW é
   suficiente para uso pessoal/ocasional, e qual o comportamento quando o mesmo campo foi editado
   nos dois lados — vence o timestamp mais novo, sem merge).
4. Indicador de estado na UI: offline/online, pendências de sync.
5. **Testes (foco):** lógica de sync offline→online (fila de mutações, LWW, idempotência de
   replay) — os pontos que não dá pra validar só olhando a tela. Testar service worker no limite
   do razoável (registro + cache hit de asset); não perseguir cobertura de UI.

**Ressalva iOS (registrar no ADR 002).** Push notification em PWA no iOS é limitado. Se o grupo
de uso for majoritariamente iPhone, não prometer paridade com Android; o MVP não depende de push.

**Verificação.** Teste manual roteirizado: abrir itinerário → modo avião → fechar e reabrir o app
instalado → itinerário completo visível → editar nota → voltar rede → edição sincronizada.
Testes de sync verdes (incluindo replay autenticado após expiração de sessão). `/verify` antes
do merge. Validar também em produção (Passo 3 já no ar).

**Saída.** PR #2 mergeado + deploy atualizado na VPS. `/save-session`.

**Rollback.** Reverter PR; service worker versionado com kill switch: versionamento de cache +
limpeza de caches antigos no `activate` + `self.registration.unregister()` na versão de
emergência. Aceitar que o pior caso (cache corrompido offline) só se resolve ao reconectar.

---

## Passo 5 — Fase 3: recomendação de lugares com restrições (2 PRs: P5a e P5b)

**[tier: default; sub-decisões de ranking com strongest se necessário | paralelizável com P4 (ver ressalva no grafo) | branches `fase-3a-overpass` e `fase-3b-ranking`]**

**Context brief.** "Sugira onde comer perto da parada 3, vegetariano, barato." Arquitetura:
**Overpass API (OpenStreetMap) é a fonte de candidatos** — gratuita, mas com fair-use real do
endpoint público (overpass-api.de: ~2 slots paralelos por IP, ~10k queries e ~1 GB/dia; exigir
`[timeout:25]` na query e User-Agent identificável — e a VPS compartilha IP com o SecretarIA).
O **LLM filtra e ranqueia** os candidatos respeitando restrições do usuário (orçamento, tipo de
comida, mobilidade, tempo). O LLM **nunca gera lugar do zero** — todo item apresentado tem de
existir na resposta da Overpass (I1). Consultar `docs/CODEMAP.md` para o modelo de dados de
parada. Fase dividida em dois PRs para não virar PR gorda.

**Pré-requisito de P5b:** ADR `docs/adr/003b-llm-provider.md` — provedor, modelo, chave própria,
custo estimado por chamada e budget mensal explícito; variáveis `LLM_API_KEY`/`LLM_MODEL` no
`.env.example` (opcionais, I7). O Passo 6 reusa esse ADR.

**Tarefas — P5a (backend Overpass, sem LLM).**
1. Backend `places/`: cliente Overpass com (a) queries por categoria + raio em torno de uma
   parada; (b) **camada de cache local** — model Django + migração versionada (I6): query
   normalizada → resultado + TTL de dias — para não estourar o fair-use em buscas repetidas;
   (c) backoff/retry; registrar em `docs/adr/003-overpass.md` os limites acima e a opção de
   migrar para instância própria se o uso crescer.
2. **Testes (foco):** cache (hit/miss/TTL), normalização de queries, `migrate` roda limpo.

**Tarefas — P5b (ranking LLM + UI).**
3. Pipeline de recomendação: parada + restrições do usuário → candidatos da Overpass (com tags:
   cuisine, wheelchair, opening_hours, fee etc.) → LLM recebe SOMENTE a lista de candidatos e as
   restrições → retorna subconjunto ranqueado + justificativa curta por item, referenciando IDs
   dos candidatos (validar no backend que todo ID retornado existe no input; descartar
   alucinações). Endpoint cumpre I7.
4. Web search como camada complementar **opcional e só qualitativa** (evento temporário, greve,
   exposição sazonal) — nunca fonte primária de endereço/coordenada/distância. Se usar
   multi-agente, apenas para sub-julgamento qualitativo (ex.: um agente avalia orçamento, outro
   sazonalidade) — nunca para cálculo de distância, que vem do OSRM da Fase 1 (reusar o cliente
   `/table` com `sources=0` para 1 parada × M candidatos).
5. Frontend: painel `<StopSuggestionsPanel>` (componente novo, isolado) na tela da parada com
   filtros de restrição; adicionar sugestão como parada em 1 clique — persistindo **snapshot**
   dos campos essenciais (nome, lat/lon, categoria) na parada, não referência viva ao OSM id.
6. **Testes (foco):** validação anti-alucinação (LLM retornando ID inexistente → descartado),
   com LLM mockado.

**Verificação.** Busca repetida idêntica não bate na Overpass (log de cache hit); nenhum lugar
exibido sem correspondência na resposta da Overpass; `/verify` antes de cada merge.

**Saída.** PRs #3a e #3b mergeados + deploy (com `migrate`). `/save-session`.

**Rollback.** Feature isolada em `places/` + painel de UI; reverter PR não afeta rota nem offline.

---

## Passo 6 — Fase 4: assistente de IA / orquestração (PR #4)

**[tier: strongest para desenho da orquestração; default para implementação | serial (depende de P2 e P5) | branch `fase-4-assistente`]**

**Context brief.** Última camada: um assistente conversacional que **orquestra** as ferramentas já
construídas. Papel do LLM: interpretar intenção ("tenho só a manhã livre e quero museus baratos
perto do hotel"), decidir quais ferramentas chamar (OSRM/otimizador da Fase 1, Overpass/recs da
Fase 3, web search qualitativa), aplicar julgamento sobre restrições e explicar o resultado em
linguagem natural. Ele NÃO é fonte de cálculo geoespacial nem de fato verificável — essas
responsabilidades já estão nas Fases 1 e 3 (I1).

**Tarefas.**
1. Definir contrato de ferramentas (tool calling) sobre os serviços existentes:
   `optimize_route(itinerary_id, constraints)`, `suggest_places(stop_id, restrictions)`,
   `web_search_qualitative(query)`. Nenhuma ferramenta nova de cálculo.
2. Endpoint de chat no backend com o loop de orquestração: intenção → plano de chamadas →
   execução → resposta explicada citando os dados retornados. **Decisão de transporte registrada
   no ADR 004:** o AdventureLog roda Django sob WSGI/gunicorn — streaming real (SSE) exigiria
   ASGI + `proxy_buffering off` no reverse proxy. Default para uso pessoal: resposta
   não-streaming (mais simples); só migrar para ASGI se a latência incomodar na prática.
   Endpoint cumpre I7.
3. Guard-rails codificados: respostas com números de distância/tempo devem vir de payload de
   ferramenta (propagar valores estruturados, não texto livre do modelo); recusar responder fato
   de lugar sem candidato da Overpass.
4. Reusar provedor/modelo/budget do ADR 003b (P5); registrar em `docs/adr/004-assistente.md`
   só o que muda (custo por conversa do loop de orquestração).
5. UI de chat simples dentro do itinerário. Consultar `docs/CODEMAP.md` para o padrão de
   componentes e fetch do frontend.
6. **Testes (foco):** o loop de orquestração com LLM mockado — dado uma intenção sintética, as
   ferramentas certas são chamadas na ordem certa; guard-rail anti-fato-inventado dispara.

**Verificação.** Cenário e2e manual: pedir em linguagem natural uma manhã otimizada → assistente
chama recs + otimizador → resposta final bate com o que os endpoints retornam isoladamente.
`/verify` antes do merge.

**Saída.** PR #4 mergeado + deploy. `/save-session`.

**Rollback.** Assistente é camada sobre APIs existentes; reverter PR remove só o chat.

---

## Passo 7 — Validação do MVP: viagem real (dry-run)

**[tier: default | serial | sem código novo — checklist + correções pontuais]**

**Context brief.** O critério de pronto não é técnico, é de uso: "consigo usar o Trilho numa
viagem real, offline, do início ao fim". Este passo simula (ou acompanha) uma viagem de verdade
contra a instância de produção na VPS.

**Tarefas.**
1. Roteiro de validação: criar viagem com 2+ dias e 8+ paradas → otimizar rota por dia →
   pedir 2 recomendações com restrição real e adicionar ao roteiro → instalar PWA no celular →
   sair de casa com wifi/4G desligado → seguir o dia inteiro pelo app → editar offline →
   sincronizar ao voltar.
   **Teste de eviction (obrigatório se o celular do grupo for iPhone):** instalar o PWA,
   carregar o roteiro, deixar >7 dias sem abrir, reabrir OFFLINE e confirmar que o roteiro
   persiste (valida o `navigator.storage.persist()` e a mitigação do ADR 002).
2. Registrar toda fricção em issues no fork (não corrigir inline, exceto bug bloqueante).
3. Triage: bloqueantes corrigidos em micro-PRs; o resto vira backlog.
4. Conferir invariantes I1–I5 uma última vez; conferir consumo de RAM da VPS vs. ADR 001.

**Verificação.** Checklist do item 1 completo sem bloqueante aberto. MVP declarado pronto.

**Saída.** Tag `v1.0-mvp` no fork. `/save-session` final.

---

## Anti-padrões a vigiar (do catálogo do blueprint)

- **LLM-como-calculadora:** qualquer distância/coordenada/horário vindo de texto de modelo → bug,
  não feature (I1).
- **Big-bang de infra:** subir OSRM sem o gate do Passo 1 e derrubar o SecretarIA por falta de RAM.
- **Fase gorda:** misturar recomendação (P5) dentro do assistente (P6). São PRs separados.
- **Cobertura pela cobertura:** o acordo de testes é cirúrgico (algoritmo, sync, cache,
  guard-rails), não percentual global.
- **Deriva de escopo:** parser de email volta disfarçado de "só um import simples". Não.
- **Fork órfão:** nunca sincronizar com upstream. Ao fim de cada fase, avaliar `git fetch upstream`
  e rebase/merge seletivo (o AdventureLog é ativo — 24 releases).

## Mutação do plano

Passos podem ser divididos, inseridos, pulados ou abandonados — registrar a mudança neste arquivo
(seção "Changelog do plano" abaixo) com data e motivo, antes de executar a mudança.

### Changelog do plano

- 2026-07-19 — Mutação: P3 (deploy VPS) pausado por decisão do usuário — VPS Hetzner não tem
  Docker instalado (achado real, `docs/adr/001-infra-osrm.md` §1.1). Em vez de instalar Docker
  na VPS agora, desenvolvimento segue 100% local (Docker Desktop) até o MVP estar validado;
  deploy fica para o fim. Grafo original marcava P4/P5 como dependentes de P3 — essa dependência
  é suspensa: P4 e P5 prosseguem com validação local substituindo validação em produção em cada
  fase (item "validar também em produção" de P4 fica pendente até o deploy acontecer). P3
  permanece no plano, movido para depois de P4/P5/P6, antes do P7 (validação MVP), já que o
  critério de MVP exige deploy real.
- 2026-07-18 — v1 gerada (planejamento com modelo strongest).
- 2026-07-18 — v2: revisão adversarial (Opus) aplicada. Críticos corrigidos: (1) conflito
  SSR SvelteKit × offline → tarefa 0 do P4; (2) auth da fila de mutações offline → decisão
  obrigatória no ADR 002; (3) OSRM movido para compose override opcional para preservar I4;
  (4) eviction de storage no iOS (~7 dias) → `storage.persist()` + mitigação + teste no P7.
  Importantes: migrações viram invariante I6; endpoints/env vars viram I7; ADR de provedor LLM
  antecipado para antes do P5b; P5 dividido em P5a/P5b; streaming do chat vira decisão explícita
  (default não-streaming em WSGI); grafo corrigido (P6 depende de P2+P5, não de P4); ressalva de
  colisão de frontend no paralelismo P4∥P5; dimensionamento OSRM Brasil endurecido (medir, não
  estimar; disco incluso); critério de verificação do P2 tornado falsificável.
