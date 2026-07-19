# Design — Fase 2: Modo offline / PWA

Data: 2026-07-19. Branch: `fase-2-offline`. Blueprint: Passo 4
(`docs/hub/30-planos/trilho-blueprint.md`). Decisões de arquitetura: `docs/hub/20-decisoes/002-offline-sync.md`
(ler antes deste doc — contém o raciocínio completo).

## Objetivo

Levar o itinerário no bolso sem sinal: abrir o app instalado offline, ver o
roteiro completo (paradas, ordem, notas), reordenar paradas e editar notas
offline, sincronizar ao voltar a rede.

## Escopo

**Dentro**: shell PWA instalável; leitura offline do itinerário completo
(snapshot IndexedDB); edição offline de reorder de itinerário e texto de
nota; fila de mutações + sync com LWW; indicador de estado online/offline +
pendências; mitigação de eviction iOS.

**Fora** (limitação conhecida, não pendência esquecida): tiles de mapa
offline; criar/editar/deletar location/lodging/transportation/checklist
offline; push notification.

## Arquitetura

### 1. Shell PWA

`@vite-pwa/sveltekit` (compatível com SvelteKit 2 / Vite 5 / Svelte 4, stack
confirmada em `frontend/package.json`). Gera manifest (nome "Trilho", ícone,
`display: standalone`) e service worker com cache de assets do app shell
(JS/CSS gerados pelo build). `navigator.storage.persist()` chamado uma vez no
boot (`+layout.svelte` raiz ou hook equivalente); resultado guardado em store
Svelte lida pelo `<OfflineIndicator>`.

### 2. Rota client-render + snapshot

`frontend/src/routes/collections/[id]/+page.ts` (novo) com
`export const ssr = false` e um `load` universal que:
1. Se `navigator.onLine`, tenta `fetch('/api/collections/{id}/')` client-side
   (mesmo endpoint que `+page.server.ts` já usa, mesma forma de resposta).
   Em sucesso, grava o `collection` completo (já inclui array `itinerary`,
   confirmado em `CollectionItineraryPlanner.svelte:64`) em IndexedDB via
   `idb` ou `idb-keyval`, chave `collection:{id}`.
2. Se offline ou o fetch falhar, lê `collection:{id}` da IndexedDB. Se não
   houver snapshot, mostra estado vazio explicando que é preciso abrir esta
   viagem pelo menos uma vez online.

`frontend/src/routes/collections/[id]/+page.server.ts` existente é removido
— substituído pelo load universal acima (não coexistem: SvelteKit prioriza
`+page.ts` quando `ssr = false`, o `+page.server.ts` antigo ficaria morto).
As `actions` de delete que hoje vivem em `+page.server.ts` migram para
chamada client-side direta ao endpoint proxy (`fetch('/api/collections/{id}',
{method: 'DELETE'})`), já que `actions` de formulário dependem de SSR.

### 3. Fila de mutações offline

Store IndexedDB nova, `pending_mutations`: lista de
`{id, type: 'reorder' | 'note_edit', payload, timestamp, endpoint, method}`.

- **Reorder**: intercepta o fluxo já existente em
  `CollectionItineraryPlanner.svelte` (`fetch('/api/itineraries/reorder/')`,
  linhas ~120 e ~1115). Quando `!navigator.onLine`, em vez de chamar a rede:
  aplica a nova ordem otimisticamente no estado local (`days`/`collection`),
  enfileira a mutação, atualiza contador do `<OfflineIndicator>`.
- **Nota**: mesmo padrão em `NoteModal.svelte` (`fetch('/api/notes/{id}',
  {method: 'PATCH'})`, linha ~100). Aplica o texto novo localmente, enfileira.
- **Replay**: listener do evento `online` do browser (+ tentativa ao ganhar
  foco da aba) percorre `pending_mutations` em ordem de timestamp, refaz cada
  fetch contra o mesmo endpoint client-side de sempre (cookie de sessão do
  browser continua válido — Decisão 2 do ADR 002). Sucesso remove da fila;
  falha (ex.: 401 por sessão expirada) mantém na fila e sinaliza erro no
  indicador, sem apagar a mutação pendente.
- **Idempotência**: reorder é PATCH idempotente por natureza (a ordem final é
  o payload, reaplica sem efeito colateral). Nota é PATCH full-object
  idempotente pelo mesmo motivo. Não precisa de dedupe além de "processar em
  ordem e não repetir a mesma entrada da fila".

### 4. Indicador de UI

`frontend/src/lib/components/shared/OfflineIndicator.svelte` (novo,
componente isolado por I5/paralelismo P4∥P5 do blueprint — não edita
componentes de parada existentes). Mostra: bolinha verde/cinza
online/offline; contador de mutações pendentes; aviso de storage não
persistido.

### 5. Mitigação iOS

Coberta na arquitetura acima (re-grava snapshot a cada load online bem
sucedido — passo 2.1; aviso textual no indicador — passo 4). Teste real de
eviction (>7 dias) não é verificável nesta fase, fica para o Passo 7.

## Testes (foco cirúrgico, não cobertura ampla)

- Fila de mutações: enqueue offline → replay ao voltar online → fila vazia;
  replay com falha de rede mantém item na fila; ordem de replay respeita
  timestamp.
- LWW: duas mutações da mesma nota com timestamps diferentes → a de
  timestamp maior é a que persiste após ambas replayed.
- Service worker: registra; asset conhecido serve do cache em segunda visita
  (teste de integração leve, não perseguir cobertura de todo o shell).

Não testar: UI do `<OfflineIndicator>` pixel a pixel, tiles de mapa (fora de
escopo), fluxos de criar/deletar item offline (fora de escopo).

## Verificação (do blueprint, Passo 4)

Teste manual roteirizado: abrir itinerário → modo avião → fechar/reabrir app
instalado → itinerário completo visível → editar nota → reordenar parada →
voltar rede → ambas sincronizadas. Testes automatizados de sync verdes.
Validação em produção fica pendente até o deploy (P3, pausado — ver mutação
do blueprint 2026-07-19).

## Fora de escopo — não implementar

Tiles de mapa offline. CRUD offline além de reorder/nota. Push notification.
Merge de conflito (LWW cobre tudo). Qualquer parser de email (I5, fora de
escopo do projeto inteiro).
