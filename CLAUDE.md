# CLAUDE.md — Trilho

Fonte de verdade estática para qualquer sessão (humana ou agente) neste repo. Não duplica
`docs/hub/30-planos/trilho-blueprint.md` nem `docs/hub/10-contexto/CODEMAP.md` — só referencia.

## Stack

Ver `docs/hub/10-contexto/CODEMAP.md` para mapa real de apps/modelos/rotas. Resumo: Django/DRF/PostGIS
(`backend/`) + SvelteKit/TS (`frontend/`), orquestrado via `docker-compose*.yml` na raiz.
Fork do [AdventureLog](https://github.com/seanmorley15/AdventureLog) (GPL-3.0) — manter
LICENSE e atribuição.

## Princípio arquitetural central

Dados reais + algoritmo determinístico fazem o trabalho pesado. O LLM só interpreta intenção,
aplica julgamento qualitativo sobre restrições e explica o resultado. **Nunca** deixar o LLM
calcular ou inventar dado factual/geoespacial (distância, endereço, coordenada, horário de
funcionamento) que deveria vir de API estruturada (OSRM, Overpass, PostGIS). Detalhe completo:
`docs/hub/30-planos/trilho-blueprint.md` §"Princípio arquitetural central" e invariante I1.

## Fora de escopo (permanente)

Importação automática de reservas via email (parser de email, OAuth Gmail/Outlook). Não
implementar em hipótese alguma — nem disfarçado de "só um import simples".

## Invariantes (I1–I7)

Verificar ao final de todo passo do blueprint. Resumo — detalhe completo em
`docs/hub/30-planos/trilho-blueprint.md` §"Invariantes":

- **I1.** LLM nunca é fonte de cálculo geoespacial ou fato verificável de lugar.
- **I2.** Testes do algoritmo de otimização (Fase 1) permanecem verdes.
- **I3.** Após qualquer deploy, SecretarIA (outro serviço na mesma VPS) responde normalmente.
- **I4.** `docker compose up` puro do repo continua funcionando após cada fase; serviços que
  dependem de artefatos fora do repo (ex.: OSRM) vivem em override opcional.
- **I5.** Fora de escopo continua fora de escopo.
- **I6.** Toda fase que altera schema entrega migração Django versionada.
- **I7.** Todo endpoint novo entra com rota registrada, `permission_classes` corretas e
  CSRF/CORS conferidos; variável de ambiente nova entra no `.env.example`.

## Convenções de commit/branch

- Branch por fase (`fase-1-rota`, `fase-2-offline`, `fase-3a-overpass`, `fase-3b-ranking`,
  `fase-4-assistente`, ...), PR contra o `main` do fork.
- Mensagens de commit em português.
- Rodapé `Co-Authored-By: Claude <noreply@anthropic.com>` (ou variante do modelo usado) nos
  commits gerados por agente.
- Remote `upstream` aponta para `seanmorley15/AdventureLog` — nunca sincronizar automaticamente,
  avaliar `git fetch upstream` manualmente ao fim de cada fase.

## Hub de contexto (`docs/hub/`)

Toda a documentação viva do projeto mora em `docs/hub/`, separada por tipo:
`10-contexto/` (codemap), `20-decisoes/` (ADRs), `30-planos/` (blueprint + plano de execução),
`40-progresso/` (estado vivo), `50-operacao/` (runbooks). Índice: `docs/hub/00-INDEX.md`.

**Regra de auto-alimentação (obrigatória):** todo fechamento de sub-tarefa/fase atualiza
`docs/hub/40-progresso/` E `docs/hub/00-INDEX.md` no mesmo commit. Documento novo entra no hub
com linha correspondente no índice — nunca solto em `docs/` ou na raiz.

## Estado vivo do progresso

Não duplicado aqui — ver `docs/hub/40-progresso/PROGRESS.md`, atualizado a cada fechamento de Passo do blueprint.
Para o plano completo (passos, ordem de execução, ADRs, changelog de mutações): consultar sempre
`docs/hub/30-planos/trilho-blueprint.md` primeiro — não recriar planejamento do zero.
