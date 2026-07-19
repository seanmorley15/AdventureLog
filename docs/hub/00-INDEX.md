# docs/hub — Índice vivo do contexto do Trilho

> Pasta única de contexto do projeto, estilo NotebookLM: fontes separadas por tipo, uma linha
> por fonte aqui. **Protocolo de auto-alimentação:** todo fechamento de sub-tarefa/fase
> atualiza `40-progresso/` E este índice no mesmo commit. Fonte nova no hub sem linha aqui =
> commit incompleto.

## 10-contexto — o que é o projeto

- [CODEMAP.md](10-contexto/CODEMAP.md) — mapa real de apps/modelos/rotas do fork (gerado 2026-07-19; atualizar quando auditoria revelar estrutura nova).

## 20-decisoes — ADRs (decisões com trade-off, imutáveis depois de aprovadas)

- [001-infra-osrm.md](20-decisoes/001-infra-osrm.md) — dimensionamento OSRM na VPS Hetzner; gate P1 fechado; deploy pausado (VPS sem Docker). Pendências pro P3: gates 3.0/3.1.
- [002-offline-sync.md](20-decisoes/002-offline-sync.md) — offline/PWA: shell `ssr=false`, auth via proxy, escopo reorder+nota, LWW, mitigação eviction iOS. Aprovado.
- *(futuros: 003-overpass, 003b-llm-provider 🔒, 004-assistente, direcao-visual 🔒 — criar aqui)*

## 30-planos — planejamento

- [trilho-blueprint.md](30-planos/trilho-blueprint.md) — **fonte de verdade da ordem e das fases**; changelog de mutações no fim.
- [trilho-mvp-execucao.md](30-planos/trilho-mvp-execucao.md) — plano de execução detalhado P2.5→P7 + produção; DoD por sub-tarefa, gates 🔒, modelos recomendados, prompts prontos por fase.
- [2026-07-19-offline-pwa-design.md](30-planos/2026-07-19-offline-pwa-design.md) — spec de design da Fase 2 (offline/PWA), par do ADR 002.
- [trilho-fluxo.html](30-planos/trilho-fluxo.html) / [trilho-fluxo.mermaid](30-planos/trilho-fluxo.mermaid) — diagramas de fluxo.

## 40-progresso — estado vivo

- [PROGRESS.md](40-progresso/PROGRESS.md) — status por passo do blueprint; atualizar a cada fechamento.
- *(futuros: auditoria-p25.md e registros por fase — criar aqui)*

## 50-operacao — runbooks

- [osrm.md](50-operacao/osrm.md) — pré-processamento e subida do OSRM local.
- *(futuro: deploy.md — checklist reprodutível de deploy na VPS, criado no P3)*

## Pendências de convenção (fora do hub)

- Remote `upstream` (seanmorley15/AdventureLog) não configurado neste clone — `CLAUDE.md` pede;
  adicionar com `git remote add upstream https://github.com/seanmorley15/AdventureLog.git`
  antes do primeiro `git fetch upstream` de fim de fase.
