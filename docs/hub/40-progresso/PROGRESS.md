# PROGRESS.md — Trilho

Tracking vivo do blueprint (`docs/hub/30-planos/trilho-blueprint.md`). Atualizar a cada fechamento de Passo.
Ordem de execução real (pós-mutação 2026-07-19) — ver blueprint §"Grafo de dependências" para
justificativa completa da ordem.

| Passo | Descrição | Status | Última atualização | Commit/PR |
|---|---|---|---|---|
| P0 | Bootstrap: clonar e rodar AdventureLog local | Concluído | 2026-07-18 | ver `docs/hub/10-contexto/CODEMAP.md` |
| P1 | Gate de pesquisa: VPS comporta OSRM? | Concluído | 2026-07-18 | `docs/hub/20-decisoes/001-infra-osrm.md` |
| P2 | Fase 1: otimização de rota multi-parada | Concluído | 2026-07-19 | `4639236` (branch `fase-1-rota`, merge) |
| P2.5 | Auditoria: bugs e gaps do AdventureLog base | Concluído | 2026-07-19 | [PR #3](https://github.com/Caio-Coutinho01/Trilho/pull/3) (mergeado) |
| P2.6 | Features de baixo esforço (testadas) | Concluído | 2026-07-19 | [PR #4](https://github.com/Caio-Coutinho01/Trilho/pull/4) (mergeado, squash) |
| P5a | Fase 3A: backend Overpass + cache (sem LLM) | Concluído | 2026-07-19 | branch `fase-3a-overpass` (PR a abrir) |
| P5b | Fase 3B: ranking LLM + UI de recomendação | Não iniciado | 2026-07-19 | — |
| P6 | Fase 4: assistente de IA / orquestração | Não iniciado | 2026-07-19 | — |
| P6.5 | Remapeamento de design/UI do site inteiro | Não iniciado | 2026-07-19 | — |
| P3 | Deploy v0 na VPS Hetzner | Pausado (decisão 2026-07-19 — Docker não instalado na VPS; dev segue local até MVP fechar) | 2026-07-19 | `docs/hub/20-decisoes/001-infra-osrm.md` §1.1 |
| P4 | Fase 2: modo offline / PWA | Não iniciado (branch `fase-2-offline` já criada localmente) | 2026-07-19 | `docs/hub/20-decisoes/002-offline-sync.md` (design), sem PR ainda |
| P7 | Validação do MVP: viagem real (dry-run) | Não iniciado | 2026-07-19 | — |

## Notas

- 2026-07-19: P5a fechado. App novo `backend/server/places/` (cache Overpass, sem LLM), reusando
  `RecommendationsViewSet.query_overpass` (`adventures/views/recommendations_view.py`) via
  subclasse em `places/overpass_client.py` — não duplica cliente Overpass do zero (achado do
  CODEMAP §3). Cache `OverpassCacheEntry` com TTL de 14 dias (`docs/hub/20-decisoes/003-overpass.md`),
  chave normalizada (lat/lon arredondados, ordem de params irrelevante). Endpoint
  `GET /api/places/nearby/` (`IsAuthenticated` + dono da `Location`). Suíte `places` (11 testes,
  incluindo cache hit/miss/TTL) + `adventures routing` seguem verdes: 37/37. Env var opcional
  `PLACES_OVERPASS_CACHE_TTL_DAYS` documentada no `.env.example` (I7).
- 2026-07-19: P2.6 fechado com 1 único item de backlog (`backlog-p26`): issue #2 (reverse
  geocode retornando "Arcinazzo Romano" pra Roma centro — substring match sem word-boundary em
  `match_locality`, `backend/server/adventures/geocoding.py`). Corrigido em
  [PR #4](https://github.com/Caio-Coutinho01/Trilho/pull/4), 2 testes de regressão novos,
  suíte `adventures routing` 26/26 verde. Corte de linha (2.6.3): backlog `backlog-p26` zerou
  após esse item — nada adiado.
- 2026-07-19: `main` local estava sem `docs/hub/` (só existia em `fase-2-offline`, commits
  `11167e9`+`5414742`+`7615d20`) — fast-forward puro (`fase-2-offline` era só `main` + 2
  commits de doc, sem divergência) feito localmente pra destravar o protocolo de
  auto-alimentação do P2.5. `origin/main` segue 2 commits atrás do `main` local (não
  sincronizado ainda).
- Branch atual do repo (nesta sessão): `fase-2-offline` — criada mas P4 não é o próximo passo na
  ordem reordenada; próximo passo real é P2.5. Não implica que P4 esteja em andamento.
- Estados possíveis: não iniciado / em andamento / bloqueado / concluído / pausado.
- Este arquivo não substitui o blueprint — para contexto de *por que* cada passo existe ou mudou
  de ordem, ver `docs/hub/30-planos/trilho-blueprint.md` §"Changelog do plano".
