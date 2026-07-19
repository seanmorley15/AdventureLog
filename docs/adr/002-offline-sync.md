# ADR 002 — Estratégia de offline/PWA e sync de mutações

Status: **Aprovado** (2026-07-19), antes de qualquer código da Fase 2 (Passo 4 do blueprint).

## Contexto

O AdventureLog/Trilho usa SvelteKit com SSR: a tela de itinerário
(`/collections/[id]`) carrega dados via `+page.server.ts`, que roda `fetch` no
processo Node do servidor (não no browser), usando o cookie `sessionid` do
request original. Investigação confirmou que isso vai além da página: **toda
chamada de API feita pelo client-side também passa pelo proxy Node**
(`frontend/src/routes/api/[...path]/+server.ts`), que reconstrói o token CSRF
e o cookie de sessão a cada request antes de repassar ao Django. Instalar o
plugin PWA sozinho não resolve — sem o servidor Node acessível, nem a página
renderiza nem as mutações passam.

## Decisão 1 — Shell offline: mesma URL, `ssr = false`

`/collections/[id]` passa a ser client-rendered (`export const ssr = false`
em `+page.ts` novo, substituindo o load atual de `+page.server.ts` por um load
universal que roda no browser). Justificativa:

- Mesma URL que o usuário já usa/favorita — nenhum link quebrado, nenhuma tela
  duplicada de itinerário para manter em paridade.
- SEO não importa aqui: é tela autenticada, atrás de login.
- Load universal client-side pode checar `navigator.onLine` e cair para
  hidratação via IndexedDB quando offline, sem depender do Node estar de pé.

Alternativa recusada: rota dedicada `/collections/[id]/offline`. Isolaria o
risco, mas duplicaria lógica de exibição do itinerário — descartado por
violar YAGNI e o princípio de não duplicar fonte de verdade da UI.

## Decisão 2 — Autenticação da fila de mutações offline

**Sessão-cookie via o mesmo proxy `/api/...` já existente — sem token DRF
novo.** Raciocínio: "estar online" e "o proxy Node estar acessível" são a
mesma condição prática nesta arquitetura (o app é servido pelo próprio Node
que hospeda o proxy). Logo, a fila de mutações enfileiradas offline pode ser
replayed, ao reconectar, contra os mesmos endpoints client-side
(`fetch('/api/itineraries/reorder/')`, `fetch('/api/notes/{id}', {method:
'PATCH'})`) que a UI já usa quando online — o cookie de sessão do browser
segue válido e é reenviado normalmente pelo proxy.

Alternativa recusada: token DRF guardado em IndexedDB para bypassar o proxy e
falar direto com o Django. Rejeitada por adicionar uma segunda forma de auth
só para o caminho offline, sem necessidade real — o cookie já resolve porque
online implica proxy acessível.

## Decisão 3 — Escopo do MVP offline (decisão do usuário, 2026-07-19)

- **Dentro do escopo**: leitura completa do itinerário offline (snapshot via
  IndexedDB do objeto `collection`, que já inclui `itinerary` — achado do
  `docs/CODEMAP.md` §4); edição offline de **reorder de itinerário** e
  **texto de nota**, com fila de mutações e sync ao reconectar.
- **Fora do escopo** (registrado como limitação conhecida, não esquecimento):
  cache de tiles de mapa offline (tela cai para lista sem mapa quando sem
  sinal); criar/editar/deletar location/lodging/transportation/checklist
  offline (só reorder + nota); push notification.

Justificativa: tiles de mapa offline (bounding box, zoom levels, quota do
browser) e CRUD completo offline (IDs temporários, delete de item criado
offline) são complexidade real desproporcional ao ganho para "uso pessoal,
ocasional" — reorder + nota cobre o caso de uso real em viagem ("mudei a
ordem", "anotei algo") sem abrir superfície de conflito maior.

## Decisão 4 — Resolução de conflito: last-write-wins (LWW)

Já decidida no blueprint (Passo 4, tarefa 3), registrada aqui por completude.
Cada mutação enfileirada carrega um timestamp local (momento da ação do
usuário, não do replay). No replay, se o servidor retornar 409/conflito de
versão — não há checagem de versão no backend atual, então na prática o PATCH
simplesmente sobrescreve — o último replay vence, sem merge de campos. Motivo
suficiente para uso pessoal/ocasional: uma única pessoa edita o próprio
itinerário; o caso de dois dispositivos editando o mesmo campo offline ao
mesmo tempo é raro e o custo de implementar merge não se paga.

## Decisão 5 — Mitigação de eviction no iOS/WebKit

WebKit pode despejar IndexedDB/Cache Storage após ~7 dias sem uso do site.
Mitigação: `navigator.storage.persist()` chamado no boot (resultado logado);
re-gravação do snapshot **a cada carregamento online bem-sucedido** (não só
na primeira vez); aviso textual no `<OfflineIndicator>` quando
`navigator.storage.persisted()` retorna `false` — "abra o app com internet
antes de viajar". Teste de eviction real (instalar, >7 dias sem abrir, reabrir
offline) fica para o Passo 7 (validação MVP), não é verificável nesta fase.

## Ressalva de push notification (iOS)

Fora de escopo desta fase (Decisão 3). Se entrar no futuro, push em PWA no
iOS é limitado — não prometer paridade com Android.
