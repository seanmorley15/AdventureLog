# Plano de Execução — MVP Trilho (P2.5 → P7 + produção)

> Nível de detalhe ABAIXO do blueprint (`docs/hub/30-planos/trilho-blueprint.md`), pronto pra execução sem
> ambiguidade. **Não redecide nada**: sintetiza e detalha decisões já registradas em
> `docs/hub/30-planos/trilho-blueprint.md`, `docs/hub/20-decisoes/001-infra-osrm.md`, `docs/hub/20-decisoes/002-offline-sync.md`,
> `CLAUDE.md` e `docs/hub/40-progresso/PROGRESS.md`. Se este plano conflitar com o blueprint, o blueprint vence
> e este arquivo deve ser corrigido (registrar no Changelog do blueprint se for mutação real).
>
> Gerado em 2026-07-19. Estado real de partida: P0/P1/P2 concluídos (`docs/hub/40-progresso/PROGRESS.md`);
> próximo passo real é **P2.5**. Branch atual `fase-2-offline` existe mas P4 não está em
> andamento — trabalho de P2.5 parte do `main`.

## Ordem de execução (fixada pelo blueprint — NÃO reordenar)

```
P2.5 → P2.6 → P5a → P5b → P6 → P6.5 → 🔒P3 (deploy VPS) → P4 (offline/PWA) → P7 (validação MVP)
```

## Legenda

- `[ ]` sub-tarefa com critério de pronto verificável ao lado (**DoD:**).
- **🔒 GATE HUMANO** — parar e pedir confirmação explícita do Caio antes de executar. Nunca
  executar sozinho, mesmo com o plano detalhado.
- **[RESTRIÇÃO v1]** — simplificação aceita para uso pessoal, registrada inline (não é dívida
  escondida).

## Restrições aceitas do v1 pessoal (onde cada uma se aplica)

| Restrição | Onde se aplica neste plano |
|---|---|
| Single-user: sem multi-tenant, sem concorrência de usuários | P4 (fila de sync assume 1 editor), P5b (sem rate-limit por usuário), P6 (chat sem histórico multi-usuário), P3 (sem HA) |
| Sync offline last-write-wins, sem merge (ADR 002, Decisão 4) | P4 tarefas 4–5 |
| Deploy manual documentado, 1 VPS compartilhada com SecretarIA, sem CI/CD, sem HA | P3 inteiro |
| Custo zero além da VPS (OSRM self-hosted, Overpass público com fair-use, LLM com chave própria e budget explícito) | P5a (fair-use Overpass), P5b/P6 (budget no ADR 003b), P3 (sem serviços pagos novos) |
| Design funcional, sem A/B nem pesquisa de usuário | P6.5 |

## O que NÃO se simplifica (obrigatório em todas as fases)

- **Invariantes I1–I7** (`CLAUDE.md` / blueprint §Invariantes) — checagem ao final de cada fase.
  Em especial: I1 (LLM nunca calcula fato geoespacial — grep de review em P5b/P6), I3
  (SecretarIA no ar após qualquer deploy), I4 (`docker compose up` puro verde), I6 (migração
  versionada), I7 (rota + permissões + CSRF/CORS + `.env.example`).
- **Fora de escopo permanente**: parser de email / OAuth Gmail-Outlook. Não entra nem "simples".
- **Testes "foco" de cada fase** (definidos no blueprint) — obrigatórios, não opcionais.
- Gate `/verify` (ecc:verification-loop) antes de fechar cada PR de fase.
- `docs/hub/40-progresso/PROGRESS.md` atualizado a cada fechamento de passo.

## Pré-voo — do zero absoluto (verificar ANTES de qualquer fase)

Checklist pra qualquer sessão (humana ou agente) partir do zero nesta máquina:

- [ ] **Ambiente local:** Docker Desktop instalado e rodando; repo clonado em
  `C:\Users\Caio Coutinho\source\repos\Trilho`; `.env` existe na raiz (se não: copiar de
  `.env.example` e preencher — `OSRM_URL` já está inventariado lá).
- [ ] **Artefatos OSRM locais:** arquivos `.osrm*` pré-processados existem fora do repo
  (comando de reprocesso e caminho documentados em `docs/hub/50-operacao/osrm.md` — se perdidos, reprocessar
  antes de testar "Otimizar rota"). Sem eles, `docker-compose.osrm.yml` não sobe — e tudo o
  resto continua funcionando (I4), só a otimização fica indisponível.
- [ ] **Comando dev completo:** `docker compose -f docker-compose.dev.yml up -d` (stack pura);
  com OSRM: conferir em `docs/hub/50-operacao/osrm.md` o comando exato de combinação dev+override usado no P2
  (o override foi escrito sobre o compose base — validar que a combinação com o dev compose
  funciona antes de confiar nela no roteiro do P2.5).
- [ ] **Credenciais por fase** (só quando a fase chegar, mas saber desde já que serão exigidas):
  `gh auth status` ok (issues/PRs — P2.5 em diante); chave LLM própria (P5b/P6 — gate 5b.0);
  SSH na VPS + acesso ao console Hetzner + acesso ao DNS do domínio (P3).
- [ ] **Baseline verde:** `docker compose -f docker-compose.dev.yml exec server python manage.py test adventures routing`
  → 23/23 (ADR 001 §7). Se baseline quebrada, consertar ANTES de iniciar a fase.

## Protocolo de sessão (herdado do blueprint §Protocolo entre sessões)

- 1 fase = 1 PR (P2.5/P2.6 = micro-PRs). `/verify` antes de fechar. Mensagens de commit em
  português, rodapé `Co-Authored-By` conforme `CLAUDE.md`.
- Encerrar sessão no meio de um passo: `/save-session`. Retomar: `/resume-session`.
- Tier de modelo: **strongest** pra desenho da orquestração (P6.1–6.2), direção visual (P6.5.2)
  e revisões; default (Sonnet) pro resto da execução.
- Nunca sincronizar `upstream` automaticamente; avaliar `git fetch upstream` manualmente ao fim
  de cada fase.

## Recomendação de modelos por fase (Claude Code e Codex)

Regra do blueprint: **strongest** pra decisão de arquitetura/infra/direção e revisões;
**default** pra execução de código. Mapeamento concreto (nomes vigentes em 2026-07; se a CLI
oferecer versão mais nova do mesmo tier, usar a mais nova):

| Fase / atividade | Claude Code | Codex (OpenAI) | Por quê |
|---|---|---|---|
| P2.5 — auditoria + micro-fixes | Sonnet | gpt-5.1-codex (reasoning médio) | Execução mecânica: roteiro, testes, fixes pequenos |
| P2.5 — triagem bloqueante vs. backlog | Opus | gpt-5.1-codex-max (reasoning alto) | Julgamento do que trava uso real |
| P2.6 — features pequenas | Sonnet | gpt-5.1-codex | Código bem delimitado, 1 PR por item |
| P5a — Overpass + cache | Sonnet | gpt-5.1-codex | Cliente HTTP + model + testes, padrão claro |
| P5b.0 — ADR 003b (provedor/budget LLM) 🔒 | Opus (ou Fable, se disponível) | gpt-5.1-codex-max | Trade-off real de custo/qualidade — decisão, não código |
| P5b — pipeline + guard-rail I1 + UI | Sonnet; review do prompt/guard-rail com Opus | gpt-5.1-codex | Implementação; guard-rail merece revisão strongest |
| P6.1–6.2 — desenho da orquestração | Opus/Fable (blueprint: strongest) | gpt-5.1-codex-max | Contrato de ferramentas e loop — erro aqui custa caro |
| P6.3–6.6 — implementação + testes | Sonnet | gpt-5.1-codex | Execução sobre desenho fechado |
| P6.5.1–6.5.2 — direção visual | Opus/Fable (strongest) + skills `frontend-design`/`ui-ux-pro-max` | gpt-5.1-codex-max | Decisão estética única, aplicada em tudo depois |
| P6.5.4 — aplicar tela a tela | Sonnet | gpt-5.1-codex | Trabalho repetitivo com direção já aprovada |
| P3 — deploy VPS 🔒 | Opus (strongest — infra compartilhada, I3) | gpt-5.1-codex-max | Irreversível, VPS compartilhada; sempre assistido |
| P4 — offline/PWA | Sonnet; review da lógica fila/LWW/idempotência com Opus | gpt-5.1-codex; review com -max | Sync é o ponto mais sutil do MVP |
| P7 — validação MVP | Sonnet | gpt-5.1-codex | Checklist manual + micro-fixes |
| Revisões de PR (`/verify` e code review) | Opus | gpt-5.1-codex-max | Blueprint: revisões sempre strongest |

Nota: no Claude Code, trocar com `/model`; no Codex CLI, `--model` / config. Reasoning effort
no Codex: `high` onde a tabela diz -max, `medium` no resto.

## Como executar — prompts prontos por fase

Modo de operação sugerido: **1 fase por vez, em sessão limpa**, colando o prompt da fase.
Nunca encadear duas fases num prompt só (contexto degrada e o gate `/verify` de uma fase é
pré-condição da próxima). Template geral:

> Leia `docs/hub/30-planos/trilho-mvp-execucao.md` (seções Pré-voo + a fase alvo) e os docs que ela
> referencia. Execute as sub-tarefas NA ORDEM, marcando cada checkbox ao concluir com o DoD
> atingido. PARE e me pergunte em todo 🔒 GATE HUMANO. Só declare a fase finalizada quando:
> (1) todo DoD da fase cumprido; (2) critério de pronto da fase atingido; (3) invariantes
> I1–I7 checados; (4) `/verify` verde; (5) `docs/hub/40-progresso/PROGRESS.md` atualizado. Se travar em algo
> fora do plano, registre no doc e me pergunte — não improvise decisão nova.

Prompts por fase (colar um por sessão):

1. **P2.5** — "Execute o P2.5 do `docs/hub/30-planos/trilho-mvp-execucao.md` (sub-tarefas 2.5.1→2.5.6).
   Só finalize quando: roteiro manual reexecutado sem bloqueante aberto, suíte
   `adventures routing` verde, todas as anomalias viraram issues triadas e
   `docs/hub/40-progresso/PROGRESS.md` marca P2.5 concluído."
2. **P2.6** — "Execute o P2.6 (2.6.1→2.6.3) sobre as issues `backlog-p26`. 1 PR por feature,
   `/verify` antes do próximo item. Só finalize quando: todo PR do lote mergeado verde e o
   corte de linha do backlog restante estiver registrado."
3. **P5a** — "Execute o P5a (5a.1→5a.7), branch `fase-3a-overpass`. Só finalize quando: busca
   repetida idêntica não bater na Overpass (teste provando cache hit), `migrate` limpo em
   banco zerado, suítes `places adventures routing` verdes e PR mergeado com `/verify`."
4. **P5b** — "Prepare o ADR 003b (5b.0) e PARE pra minha aprovação 🔒. Depois do meu OK:
   execute 5b.1→5b.8, branch `fase-3b-ranking`. Só finalize quando: teste anti-alucinação
   (ID falso descartado) verde, nenhum lugar exibido sem correspondência na Overpass, review
   I1 do diff limpo e PR mergeado com `/verify`."
5. **P6** — "Desenhe o contrato de ferramentas e o loop (6.1–6.2) com modelo strongest, depois
   execute 6.3→6.8, branch `fase-4-assistente`. Só finalize quando: teste de orquestração com
   LLM mockado verde (ferramentas certas na ordem certa), guard-rail anti-fato-inventado
   disparando em teste, e2e manual batendo com os endpoints isolados e PR mergeado com
   `/verify`."
6. **P6.5** — "Faça auditoria de UI e proposta de direção visual (6.5.1–6.5.2) e PARE pra
   minha aprovação 🔒. Depois do meu OK: aplique tela a tela (6.5.4→6.5.6), branch
   `fase-design-remap`. Só finalize quando: todas as telas na nova direção, suítes de
   P2/P5/P6 verdes (zero regressão) e PR mergeado com `/verify`."
7. **P3** 🔒 — "Fase inteira assistida: me apresente as decisões dos gates 3.0 e 3.1 (incluindo
   o conflito mem_limit 2g vs. ~3,0 GB) e NÃO toque na VPS sem meu OK por passo. Só finalize
   quando: Trilho em HTTPS no subdomínio, otimização de rota funcionando EM PRODUÇÃO,
   SecretarIA respondendo (I3), RAM medida registrada no ADR 001 §3 e `docs/hub/50-operacao/deploy.md`
   reprodutível."
8. **P4** — "Execute o P4 (4.0→4.8), branch `fase-2-offline`, seguindo o ADR 002 sem redecidir.
   Só finalize quando: roteiro manual offline completo (modo avião → reabrir → editar →
   sincronizar) passando, suíte de sync verde (fila, LWW, idempotência, sessão expirada),
   validado também em produção e PR mergeado com `/verify`."
9. **P7** — "Execute o P7 (7.1→7.5) contra produção. Só finalize quando: checklist de
   validação completo sem bloqueante aberto, invariantes I1–I7 auditados, RAM real vs. ADR
   001 conferida e tag `v1.0-mvp` criada. O teste de eviction (7.2) pode ficar agendado com
   data marcada sem travar a tag, se o celular não for iPhone."

---

## P2.5 — Auditoria: bugs e gaps da base AdventureLog

**Branch:** micro-PRs a partir do `main` (ex.: `fix/p25-<slug>`). Sem PR gordo.
**Referências:** blueprint §Passo 2.5, `docs/hub/10-contexto/CODEMAP.md`.

### Sub-tarefas

- [ ] **2.5.1 Subir stack local dev.**
  Comando: `docker compose -f docker-compose.dev.yml up -d` (Docker Desktop).
  **DoD:** `web`, `db`, `server` de pé; frontend responde HTTP 200, backend responde em `/api/`.
- [ ] **2.5.2 Roteiro manual completo**, anotando cada quebra em
  `docs/hub/40-progresso/auditoria-p25.md` (arquivo novo, temporário — vira insumo das issues):
  login → criar collection → criar itinerário (dia + itens) → adicionar 5+ paradas → editar/
  reordenar drag-and-drop → mapa (`CollectionMap.svelte`) → **Otimizar rota** (feature P2, com
  override `docker-compose.osrm.yml` de pé) → confirmar/descartar nova ordem → notas/checklists
  → logout/login de novo → persistência após `docker compose restart`.
  **DoD:** roteiro executado de ponta a ponta; toda anomalia anotada com passo de reprodução.
- [ ] **2.5.3 Suíte de testes existente.**
  Comando: `docker compose -f docker-compose.dev.yml exec server python manage.py test adventures routing`
  (baseline conhecida: 23/23 verdes em 2026-07-19, ADR 001 §7). Frontend: rodar `npm run check`
  em `frontend/` (não há suíte de testes de UI herdada — registrar isso, não inventar uma).
  **DoD:** resultado registrado em `docs/hub/40-progresso/auditoria-p25.md`; falhas pré-existentes não
  relacionadas à Fase 1 listadas separadamente.
- [ ] **2.5.4 Triagem em issues no fork** (via `gh issue create`), com labels `bloqueante` e
  `backlog-p26`.
  Critério de bloqueante: impede uso diário real (perda de dado, tela quebrada, fluxo principal
  interrompido). Cosmético → `backlog-p26`.
  **DoD:** toda anomalia do 2.5.2/2.5.3 tem issue; nenhuma anotação órfã.
- [ ] **2.5.5 Corrigir bloqueantes** — 1 micro-PR por bloqueante, cada um com teste de regressão
  quando o bug for de lógica (padrão a seguir: correção de `itinerary_view.py` citada no ADR 001
  §7). Gate `/verify` por PR.
  **DoD:** zero issues `bloqueante` abertas; suíte 2.5.3 verde após cada merge.
- [ ] **2.5.6 Atualizar `docs/hub/10-contexto/CODEMAP.md`** se a auditoria revelar estrutura não documentada;
  atualizar `docs/hub/40-progresso/PROGRESS.md` (P2.5 → Concluído).
  **DoD:** commits de docs no main.

**Critério de pronto da fase:** roteiro 2.5.2 reexecutado sem bloqueante; suíte verde;
backlog triado em issues.
**Rollback:** reverter micro-PRs individualmente (`git revert`).

---

## P2.6 — Features de baixo esforço (testadas, 1 PR cada)

**Branch:** 1 branch curta por feature (`feat/p26-<slug>`).
**Escopo:** definido pelas issues `backlog-p26` do P2.5 — **não fixado aqui de propósito**
(blueprint §Passo 2.6). Este plano define o protocolo, não a lista.

### Sub-tarefas

- [ ] **2.6.1 Priorizar backlog por esforço** (menor primeiro). Registrar ordem escolhida no
  corpo de um issue-épico `P2.6` ou em `docs/hub/40-progresso/PROGRESS.md`.
  **DoD:** lista ordenada existe e está referenciada.
- [ ] **2.6.2 Loop por feature:** implementar → teste isolado da feature (backend: Django test;
  frontend: `npm run check` + smoke manual) → `/verify` → PR → merge → registrar em
  `docs/hub/40-progresso/PROGRESS.md`. Nunca acumular 2 features não testadas.
  **DoD por item:** PR mergeado com gate verde.
- [ ] **2.6.3 Corte de linha:** quando o restante do backlog custar mais que ~1 sessão por item,
  parar — o resto fica como backlog pós-MVP. Registrar o corte em `docs/hub/40-progresso/PROGRESS.md`.
  **DoD:** decisão de corte explícita, sem itens "meio feitos".

**Critério de pronto da fase:** todo PR do lote mergeado com `/verify` verde; backlog restante
explicitamente adiado.
**Rollback:** reverter o PR individual da feature problemática.

---

## P5a — Fase 3, parte A: backend Overpass + cache (sem LLM)

**Branch:** `fase-3a-overpass`. **Referências:** blueprint §Passo 5, `docs/hub/10-contexto/CODEMAP.md` §3.

**Achado do CODEMAP a respeitar:** `adventures/views/recommendations_view.py` (29 KB) JÁ
consome Overpass e calcula `quality_score` determinístico. P5a **não duplica** isso — extrai/
reusa a lógica de consulta num app novo com cache, em vez de escrever cliente do zero.

### Sub-tarefas

- [ ] **5a.1 App novo `backend/server/places/`** (convenção 1-app-por-domínio, igual `routing/`):
  `__init__.py`, `apps.py`, `models.py`, `overpass_client.py`, `services.py`, `views.py`,
  `urls.py`, `tests.py`. Registrar em `INSTALLED_APPS` (`main/settings.py`) e montar rotas em
  `main/urls.py` sob `/api/`.
  **DoD:** `python manage.py check` limpo com o app instalado.
- [ ] **5a.2 Cliente Overpass** em `places/overpass_client.py`: queries por categoria + raio em
  torno de uma parada; `[timeout:25]` obrigatório na query; `User-Agent` identificável
  (ex.: `Trilho/0.1 (uso pessoal; contato no repo)`); backoff/retry com limite; timeout de
  socket. Avaliar extrair o que `recommendations_view.py` já faz em vez de reescrever.
  **[RESTRIÇÃO v1]** endpoint público overpass-api.de com fair-use (~2 slots/IP, ~10k
  queries/dia) é suficiente pra single-user; instância própria só se o uso crescer (registrar
  no ADR 003).
  **DoD:** chamada real a overpass-api.de retorna candidatos pra 1 parada de teste; erro de
  rede não derruba o app (feature indisponível, HTTP 503 controlado).
- [ ] **5a.3 Cache local** em `places/models.py`: model `OverpassCacheEntry` (query normalizada
  → payload JSON + `fetched_at` + TTL em dias) + normalização determinística de query
  (ordenar params, arredondar coordenadas). Migração versionada (I6):
  `python manage.py makemigrations places && python manage.py migrate`.
  **DoD:** busca repetida idêntica NÃO bate na Overpass (assert por log/contador em teste);
  `migrate` roda limpo em banco zerado.
- [ ] **5a.4 Endpoint DRF** (ex.: `GET /api/places/nearby/?stop=<id>&category=...&radius=...`)
  cumprindo I7: rota no `urls.py`, `permission_classes` autenticado + dono do recurso, CSRF
  conforme modo de fetch (proxy Node, ver ADR 002 contexto).
  **DoD:** 403 pra não-dono; 200 com candidatos pra dono.
- [ ] **5a.5 `docs/hub/20-decisoes/003-overpass.md`**: limites de fair-use, TTL escolhido, opção futura de
  instância própria.
  **DoD:** ADR commitado.
- [ ] **5a.6 Testes (foco da fase, obrigatórios):** cache hit/miss/TTL expirado, normalização
  de query (mesma busca com params em ordem diferente → mesma chave), `migrate` limpo.
  Comando: `python manage.py test places`.
  **DoD:** suíte `places` verde + suítes `adventures routing` seguem verdes (I2).
- [ ] **5a.7 Fechar:** `/verify` → PR `fase-3a-overpass` → merge → `docs/hub/40-progresso/PROGRESS.md`.

**Rollback:** feature isolada em `places/` — reverter PR não afeta rota nem resto do app;
migração revertível com `python manage.py migrate places zero` antes do revert.

---

## P5b — Fase 3, parte B: ranking LLM + UI

**Branch:** `fase-3b-ranking`. **Pré-requisito bloqueante:** ADR 003b aprovado (gate abaixo).

### Sub-tarefas

- [ ] **5b.0 🔒 GATE HUMANO — ADR `docs/hub/20-decisoes/003b-llm-provider.md`.** Trade-off real: provedor,
  modelo, custo estimado por chamada e **budget mensal explícito** (chave própria do Caio).
  Preparar o ADR com opções e recomendação; **aguardar aprovação do Caio antes de qualquer
  código de P5b**. P6 reusa este ADR.
  **DoD:** ADR com status "Aprovado" e decisão do usuário registrada.
- [ ] **5b.1 Env vars** `LLM_API_KEY` / `LLM_MODEL` no `.env.example` (opcionais, default
  ausente = feature indisponível com degradação graciosa — I4/I7).
  **DoD:** app sobe sem as vars; endpoint de ranking retorna erro controlado sem elas.
- [ ] **5b.2 Pipeline de recomendação** (em `places/services.py` ou `places/ranking.py`):
  parada + restrições → candidatos do P5a (com tags OSM: `cuisine`, `wheelchair`,
  `opening_hours`, `fee`) → LLM recebe SOMENTE lista de candidatos + restrições → retorna
  subconjunto ranqueado + justificativa curta **referenciando IDs do input**.
  **Guard-rail I1 (obrigatório):** backend valida todo ID retornado contra o input; ID
  inexistente → descartado e logado. LLM nunca gera lugar, endereço, coordenada ou distância.
  Distância parada→candidato: reusar `routing/osrm_client.py` `/table` com `sources=0`
  (1 origem × M destinos) — nunca o LLM.
  **DoD:** teste com LLM mockado devolvendo ID falso → item descartado.
- [ ] **5b.3 Endpoint DRF** (ex.: `POST /api/places/suggest/`) cumprindo I7.
  **[RESTRIÇÃO v1]** sem rate-limit por usuário (single-user).
  **DoD:** rota + permissões + CSRF conferidos.
- [ ] **5b.4 Web search qualitativa (opcional):** só se couber na sessão; camada complementar
  qualitativa (evento, greve), nunca fonte de endereço/coordenada/distância (I1). Se não
  couber, registrar como não implementado no ADR 003b — não é bloqueante do MVP.
- [ ] **5b.5 Frontend `<StopSuggestionsPanel>`** — componente NOVO e isolado em
  `frontend/src/lib/components/` (padrão dos componentes de `collections/`), na tela da parada:
  filtros de restrição, lista ranqueada com justificativa, botão "adicionar como parada" em
  1 clique persistindo **snapshot** (nome, lat/lon, categoria) — não referência viva ao OSM id.
  **DoD:** fluxo manual completo: filtrar → sugerir → adicionar → parada aparece no itinerário
  e no mapa.
- [ ] **5b.6 Testes (foco):** anti-alucinação (5b.2) com LLM mockado; pipeline com Overpass
  mockada; suítes anteriores verdes (I2).
  **DoD:** `python manage.py test places` verde.
- [ ] **5b.7 Review I1:** grep no diff por chamadas de LLM retornando
  distância/coordenada/horário como fato + leitura do prompt final.
  **DoD:** nenhum número geoespacial originado de texto do modelo.
- [ ] **5b.8 Fechar:** `/verify` → PR → merge → `docs/hub/40-progresso/PROGRESS.md`.

**Critério de pronto da fase (blueprint):** busca repetida não bate na Overpass; nenhum lugar
exibido sem correspondência na resposta da Overpass.
**Rollback:** reverter PR — painel de UI e pipeline isolados, não afeta P5a nem rota.

---

## P6 — Fase 4: assistente de IA / orquestração

**Branch:** `fase-4-assistente`. **Depende de:** P2 (otimizador) + P5 (recomendações).
**Referências:** blueprint §Passo 6; ADR 003b (provedor/budget — reusar, não redecidir).

### Sub-tarefas

- [ ] **6.1 Contrato de ferramentas** (tool calling) sobre serviços existentes — nenhuma
  ferramenta nova de cálculo:
  `optimize_route(itinerary_id, constraints)` → endpoint P2;
  `suggest_places(stop_id, restrictions)` → pipeline P5b;
  `web_search_qualitative(query)` → só se 5b.4 existir, senão omitir.
  Local sugerido: novo app `backend/server/assistant/` (mesma convenção de app por domínio).
  **DoD:** contrato documentado em `docs/hub/20-decisoes/004-assistente.md` (esboço) antes do loop.
- [ ] **6.2 Endpoint de chat** com loop de orquestração: intenção → plano de chamadas →
  execução → resposta explicada citando dados retornados. **Transporte: não-streaming sob
  WSGI/gunicorn** (decisão default do blueprint, registrar no ADR 004; só migrar pra ASGI/SSE
  se a latência incomodar na prática — se isso acontecer, vira 🔒 GATE HUMANO por ser trade-off
  de infra). Cumprir I7.
  **[RESTRIÇÃO v1]** sem histórico multi-usuário; conversa por sessão simples.
  **DoD:** rota registrada, permissões, CSRF; resposta síncrona funcional.
- [ ] **6.3 Guard-rails codificados (I1):** números de distância/tempo na resposta vêm de
  payload estruturado das ferramentas (propagados, não parafraseados de texto livre); recusa
  responder fato de lugar sem candidato Overpass no contexto.
  **DoD:** teste unitário do guard-rail dispara com resposta sintética inventando número.
- [ ] **6.4 `docs/hub/20-decisoes/004-assistente.md`:** só o que muda vs. 003b (custo por conversa do loop;
  decisão de transporte).
  **DoD:** ADR commitado.
- [ ] **6.5 UI de chat simples** dentro da tela do itinerário (componente novo, padrão do
  CODEMAP §4 pra fetch via proxy `/api`).
  **DoD:** conversa e2e manual funciona na tela.
- [ ] **6.6 Testes (foco):** loop com LLM mockado — intenção sintética → ferramentas certas na
  ordem certa; guard-rail anti-fato-inventado. Suítes anteriores verdes (I2).
  **DoD:** `python manage.py test assistant` verde.
- [ ] **6.7 Verificação e2e manual (blueprint):** "manhã otimizada" em linguagem natural →
  assistente chama recs + otimizador → resposta bate com o que os endpoints retornam isolados.
- [ ] **6.8 Fechar:** review I1 no diff → `/verify` → PR → merge → `docs/hub/40-progresso/PROGRESS.md`.

**Rollback:** assistente é camada sobre APIs existentes — reverter PR remove só o chat.

---

## P6.5 — Remapeamento de design/UI

**Branch:** `fase-design-remap`. **Referências:** blueprint §Passo 6.5; skills
`frontend-design` / `ui-ux-pro-max` pra direção visual.
**[RESTRIÇÃO v1]** direção visual funcional — sem A/B, sem pesquisa de usuário, sem perseguir
acabamento de produto comercial.

### Sub-tarefas

- [ ] **6.5.1 Auditoria da UI atual:** inventário de telas/rotas (`frontend/src/routes/`) e
  componentes herdados (`frontend/src/lib/components/`), inconsistências, restos de
  "AdventureLog" (CODEMAP §5: `+layout.svelte` 88/91, `Navbar.svelte` 206–207, `config.ts`,
  `brand/`, `favicon.png`, `settings.py` linha 239).
  **DoD:** inventário em `docs/hub/20-decisoes/direcao-visual.md` (seção "estado atual").
- [ ] **6.5.2 Proposta de direção visual:** paleta, tipografia, componentes-chave, logo/nome
  Trilho — registrada em `docs/hub/20-decisoes/direcao-visual.md` com mocks/descrição por tela
  principal.
- [ ] **6.5.3 🔒 GATE HUMANO — aprovação da direção visual pelo Caio ANTES de aplicar em
  qualquer tela.** Sem aprovação, nada de CSS em massa.
  **DoD:** aprovação explícita registrada no doc de design.
- [ ] **6.5.4 Aplicar tela por tela**, em commits pequenos por área (navbar/layout → collections
  → itinerário → mapa → sugestões → chat → settings), repetindo o roteiro de verificação de
  P2/P5/P6 como regressão manual após cada área.
  **DoD por área:** tela na nova direção + fluxo funcional intacto.
- [ ] **6.5.5 Testes (foco):** suítes automatizadas de P2/P5/P6 verdes (nenhuma regressão
  funcional); smoke visual manual de cada tela.
  **DoD:** `python manage.py test adventures routing places assistant` verde;
  `npm run check` limpo.
- [ ] **6.5.6 Fechar:** `/verify` → PR → merge → `docs/hub/40-progresso/PROGRESS.md`.

**Rollback:** reverter PR de design não afeta lógica de backend das fases anteriores.

---

## P3 — Deploy v0 na VPS Hetzner 🔒

**Sem PR de código — infra + docs. Referências:** blueprint §Passo 3; ADR 001 (specs reais,
risco de RAM, mitigações obrigatórias §5).

> **🔒 GATE HUMANO GLOBAL DA FASE: nenhuma ação nesta VPS sem confirmação explícita do Caio,
> passo a passo.** A VPS é compartilhada com o SecretarIA (I3) e as ações são
> irreversíveis/compartilhadas. Este plano prepara tudo; a execução é assistida.

**[RESTRIÇÃO v1]** deploy manual documentado; sem CI/CD; sem HA; sem SLA. 1 VPS só.

### Sub-tarefas

- [ ] **3.0 🔒 GATE — decisão de infra pendente do ADR 001 §7:** instalar Docker na VPS atual
  (4 GB RAM, reavaliando folga real da §1.1 contra runtime Docker + OSRM) **vs.** upgrade
  CX33 (8 GB, +€1/mês, opção registrada e recusada "por ora") **vs.** outra infra. Atualizar
  ADR 001 com a decisão datada. **Não prosseguir sem decisão do Caio.**
- [ ] **3.1 🔒 GATE — extract OSRM de produção:** manter combinado nord-ovest+nord-est+centro
  (~3,0 GB RAM estimada — risco de OOM documentado no ADR 001 §4) **vs.** extract customizado
  por corredor Milão–Bolonha–Florença–Roma via `osmium extract` (mitigação 3 do ADR 001 §5).
  Qualquer extensão de região futura também é gate (trade-off de RAM real).
  **⚠️ Conflito numérico a resolver NESTE gate:** `docker-compose.osrm.yml` hoje tem
  `mem_limit: 2g`, mas a estimativa do ADR 001 §3 pro extract combinado é ~3,0 GB de runtime —
  com 2g o OSRM seria morto/reiniciado em loop. Decidir em conjunto: extract menor (corredor,
  que caiba em 2g) OU subir o `mem_limit` (o que reabre a conta de RAM total da VPS e
  possivelmente o gate 3.0/upgrade). Registrar a resolução no ADR 001.
- [ ] **3.2 Levantar como o SecretarIA é servido** (ADR 001: systemd direto, sem container;
  proxy reverso? portas?). Comandos read-only via SSH: `systemctl list-units`,
  `ss -tlnp`, config do proxy existente. Integrar o Trilho ao mesmo proxy — nunca subir segundo
  proxy conflitante (referência: `docker-compose-traefik.yaml` só se Traefik já for o caso).
  **DoD:** topologia documentada em `docs/hub/50-operacao/deploy.md` (seção "estado da VPS").
- [ ] **3.3 (pós-gate 3.0) Instalar runtime escolhido** (ex.: Docker Engine + compose plugin)
  **com o Caio acompanhando**; health check do SecretarIA imediatamente após (I3).
  **DoD:** `docker version` ok na VPS; SecretarIA responde.
- [ ] **3.4 Pré-processar OSRM localmente e copiar `.osrm*` pra VPS** (decisão P1: VPS só
  recebe artefatos). Comandos documentados em `docs/hub/50-operacao/osrm.md`. Transferência via
  `rsync`/`scp` pra path fora do repo (ex.: `/opt/trilho/osrm/`).
  **DoD:** arquivos íntegros na VPS (checksum), disco com folga (28 GiB livres, ADR 001 §1.1).
- [ ] **3.4b DNS + env de produção:** criar registro DNS do subdomínio escolhido apontando pra
  VPS; montar `.env` de produção a partir do `.env.example` — no mínimo: `SECRET_KEY` novo
  (nunca o de dev), `DEBUG` desligado, hosts/origens permitidos do Django
  (`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` conforme nomes reais das vars no `settings.py`),
  URL pública do backend pro frontend (`PUBLIC_SERVER_URL`/origin conforme `.env.example`),
  `OSRM_URL` apontando pro container OSRM, credenciais do Postgres exclusivas de produção.
  Conferir firewall da VPS: só 80/443 (+ SSH) expostos; portas internas do compose não
  publicadas pra internet.
  **DoD:** `.env` de produção completo (fora do git); portas conferidas com `ss -tlnp`.
- [ ] **3.5 Subir stack Trilho** (backend + frontend + PostGIS) + override
  `docker-compose.osrm.yml` **com `mem_limit` no container OSRM já presente no arquivo
  (`mem_limit: 2g` — valor final decidido no gate 3.1)** (mitigação 1 do ADR 001 §5 —
  obrigatória: muda o pior caso de "kernel mata qualquer processo, talvez o SecretarIA" pra
  "Docker reinicia só o OSRM"). Subdomínio próprio com HTTPS no proxy existente.
  **DoD:** Trilho acessível via HTTPS no subdomínio; login funciona.
- [ ] **3.6 `docs/hub/50-operacao/deploy.md` reprodutível:** checklist de deploy manual completo — build/pull,
  `python manage.py migrate` explícito a cada deploy (I6), backup do Postgres (base:
  `backup.sh` do repo) antes de migrar, inventário de TODAS as env vars (I7:
  `OSRM_URL`, `LLM_API_KEY`, `LLM_MODEL`, `GOOGLE_MAPS_API_KEY`, ...), rollback
  (`docker compose down` do stack Trilho — SecretarIA não compartilha containers).
  **DoD:** um segundo deploy do zero seguindo só o doc funciona.
- [ ] **3.7 Health checks + medição real (mitigação 2 do ADR 001 §5):** URL Trilho responde;
  URL SecretarIA responde (I3); `docker stats --no-stream` + `free -h` com tudo no ar →
  **atualizar ADR 001 §3 com números medidos** (a estimativa pública deixa de valer).
  **DoD:** números reais no ADR; margem de RAM ≥ prevista, ou gate 3.0 reaberto (upgrade CX33).
- [ ] **3.8 Verificação da fase (blueprint):** otimizar um itinerário real **em produção**;
  SecretarIA no ar; `docs/hub/40-progresso/PROGRESS.md` atualizado (P3 → Concluído).

**Rollback:** `docker compose down` do stack Trilho restaura o estado anterior da VPS.

---

## P4 — Fase 2: modo offline / PWA

**Branch:** `fase-2-offline` (já criada). **Referências:** blueprint §Passo 4;
**ADR 002 já aprovado — seguir as 5 decisões, não redecidir.**

**[RESTRIÇÃO v1]** Escopo offline fechado pela Decisão 3 do ADR 002: leitura completa do
itinerário + edição de **reorder** e **texto de nota** apenas. Fora: tiles de mapa offline
(cai pra lista), CRUD completo offline, push. LWW sem merge (Decisão 4).

### Sub-tarefas

- [ ] **4.0 Confirmar versões** de SvelteKit/Vite no `frontend/package.json` antes de instalar
  `@vite-pwa/sveltekit` (ou equivalente compatível).
  **DoD:** compatibilidade confirmada por doc oficial do plugin, não por tentativa.
- [ ] **4.1 Shell offline (ADR 002 Decisão 1):** `/collections/[id]` vira client-rendered —
  criar `frontend/src/routes/collections/[id]/+page.ts` com `export const ssr = false` e load
  universal (browser) substituindo o load de `+page.server.ts`; quando offline
  (`navigator.onLine` false ou fetch falha), hidratar do IndexedDB.
  **DoD:** página renderiza com servidor Node derrubado (dados vindos do snapshot).
- [ ] **4.2 Service worker + manifest PWA:** cache do shell (assets), `navigateFallback`,
  manifest (nome Trilho, ícone, standalone). `navigator.storage.persist()` no boot com
  resultado logado (ADR 002 Decisão 5). Versionamento de cache + limpeza no `activate` +
  kill switch preparado (`self.registration.unregister()` na versão de emergência).
  **DoD:** PWA instalável (devtools); asset servido de cache com rede desligada.
- [ ] **4.3 Snapshot IndexedDB:** a cada carregamento online bem-sucedido do itinerário,
  regravar snapshot completo do objeto `collection` (inclui `itinerary` — CODEMAP §4 / ADR 002
  Decisão 3). Não só na primeira vez (mitigação eviction iOS).
  **DoD:** abrir online → modo avião → fechar/reabrir app instalado → itinerário completo
  visível.
- [ ] **4.4 Fila de mutações offline** (reorder + nota): cada mutação com timestamp local do
  momento da ação; replay ao reconectar contra os MESMOS endpoints do proxy `/api/...` com
  sessão-cookie (ADR 002 Decisão 2 — sem token DRF novo). LWW: último replay vence, sem merge
  (Decisão 4). Replay idempotente (reexecutar fila parcialmente enviada não duplica efeito).
  **DoD:** editar nota + reordenar offline → reconectar → estado do servidor reflete as
  edições; replay duplo não corrompe.
- [ ] **4.5 `<OfflineIndicator>`** (componente novo, isolado): estado online/offline, contagem
  de pendências de sync, aviso quando `navigator.storage.persisted()` é `false` — "abra o app
  com internet antes de viajar" (ADR 002 Decisão 5).
  **DoD:** indicador reage a modo avião em tempo real.
- [ ] **4.6 Testes (foco, obrigatórios):** fila de mutações (enfileira/replay/ordem), LWW
  (timestamps concorrentes), idempotência de replay, replay com sessão expirada (falha
  controlada, mutação preservada na fila); service worker no limite do razoável (registro +
  cache hit). Lógica de fila/LWW extraída em módulo puro testável (Vitest).
  **DoD:** suíte de sync verde; suítes backend verdes (I2).
- [ ] **4.7 Verificação manual roteirizada (blueprint):** abrir itinerário → modo avião →
  fechar e reabrir app instalado → itinerário completo → editar nota → voltar rede → edição
  sincronizada. **Validar também em produção** (P3 já no ar — resolve o item pendente da
  mutação 2026-07-19).
- [ ] **4.8 Fechar:** `/verify` → PR #2 → merge → deploy atualizado na VPS (seguindo
  `docs/hub/50-operacao/deploy.md`, com health check I3) → `docs/hub/40-progresso/PROGRESS.md`.

**Rollback:** reverter PR; service worker com kill switch (4.2) — versionamento de cache +
limpeza no `activate` + `unregister()` na versão de emergência. Pior caso (cache corrompido
offline) só se resolve ao reconectar — aceito (blueprint §Passo 4 Rollback).

---

## P7 — Validação do MVP: viagem real (dry-run)

**Sem código novo — checklist + micro-PRs de bloqueante. Referência:** blueprint §Passo 7.

### Sub-tarefas

- [ ] **7.1 Roteiro de validação contra PRODUÇÃO:** criar viagem 2+ dias / 8+ paradas →
  otimizar rota por dia → 2 recomendações com restrição real adicionadas ao roteiro →
  perguntar ao assistente algo que orquestre recs + otimizador → instalar PWA no celular →
  sair com wifi/4G desligado → seguir o dia inteiro pelo app → editar offline → sincronizar
  ao voltar.
  **DoD:** cada item do roteiro executado e registrado.
- [ ] **7.2 Teste de eviction (obrigatório se celular for iPhone):** instalar PWA, carregar
  roteiro, >7 dias sem abrir, reabrir OFFLINE → roteiro persiste (valida
  `storage.persist()` + mitigação ADR 002 Decisão 5). Agendar — item tem espera de calendário
  embutida.
- [ ] **7.3 Fricções em issues** (não corrigir inline, exceto bloqueante). Bloqueantes →
  micro-PRs com `/verify`; resto → backlog pós-MVP.
- [ ] **7.4 Auditoria final de invariantes I1–I7** + RAM real da VPS vs. ADR 001 §3 (medido).
  **DoD:** checklist de invariantes anotado em `docs/hub/40-progresso/PROGRESS.md`.
- [ ] **7.5 Declarar MVP:** tag `v1.0-mvp` no fork; `docs/hub/40-progresso/PROGRESS.md` final; avaliar
  `git fetch upstream` manualmente (convenção CLAUDE.md — nunca sync automático).

**Critério de MVP (blueprint):** "consigo usar o Trilho numa viagem real, offline, do início
ao fim" — contra a instância de produção, não localhost.

---

## Riscos principais (herdados dos ADRs, não novos)

| Risco | Origem | Mitigação já decidida |
|---|---|---|
| OOM na VPS 4 GB com OSRM (~3,0 GB estimado) | ADR 001 §4 | `mem_limit` no container OSRM (3.5) — **hoje 2g < 3,0 GB estimado: conflito resolvido no gate 3.1**; medir real e atualizar ADR (3.7); fallback upgrade CX33 (+€1/mês) já pesquisado |
| Eviction IndexedDB iOS ~7 dias | ADR 002 D5 | `storage.persist()` + regravação a cada acesso online + aviso na UI (4.3/4.5); teste real em 7.2 |
| Fair-use Overpass (IP compartilhado com SecretarIA) | Blueprint P5 | Cache com TTL (5a.3), timeout/UA na query (5a.2) |
| Alucinação de lugar pelo LLM | I1 | Validação de ID contra input (5b.2), guard-rail numérico (6.3), grep de review (5b.7/6.8) |
| Custo de LLM sem teto | Restrição custo-zero | Budget mensal explícito no ADR 003b (gate 5b.0) |

---

## Proposta anexa — reorganização da documentação (🔒 aguarda confirmação)

Pedido do Caio: concentrar contexto numa pasta única, estilo NotebookLM (fontes separadas por
tipo, auto-alimentada a cada comando/fechamento de passo). Proposta (NÃO executada — envolve
mover/apagar arquivos):

```
docs/hub/                       ← pasta única de contexto (o "notebook")
  00-INDEX.md                   ← índice vivo: 1 linha por fonte + estado (auto-alimentado)
  10-contexto/                  ← o que é o projeto (CODEMAP, princípios)
  20-decisoes/                  ← ADRs (docs/hub/20-decisoes/* movidos pra cá)
  30-planos/                    ← blueprint + este plano (plans/* movidos pra cá)
  40-progresso/                 ← PROGRESS.md + auditorias (ex.: auditoria-p25.md)
  50-operacao/                  ← osrm.md, deploy.md (quando existir)
```

Protocolo de auto-alimentação: todo fechamento de sub-tarefa/fase atualiza `40-progresso/` e o
`00-INDEX.md` no mesmo commit — regra a adicionar no `CLAUDE.md` se aprovado.

Candidatos a remoção/limpeza (verificados em 2026-07-19; confirmar item a item mesmo assim):
- `docs/hub/30-planos/` — artefatos de skill de sessões anteriores; candidato a remover.
- `plans/trilho-fluxo.html` / `plans/trilho-fluxo.mermaid` — diagramas; mover pro hub ou remover
  se supersedidos pelo blueprint.
- `backend/server/scheduler.log` — log versionado no git (3,2 KB); candidato a `.gitignore` +
  remoção do índice. É herança do upstream — conferir antes se o upstream o rastreia (evitar
  ruído em futuros diffs contra `upstream`).
- `backend/server/adventurelog.txt` — banner ASCII do upstream, inofensivo; **manter** (mexer só
  gera ruído de diff com o upstream).

**Atenção:** `CLAUDE.md` referencia caminhos atuais (`docs/hub/30-planos/trilho-blueprint.md`,
`docs/hub/40-progresso/PROGRESS.md`, `docs/hub/10-contexto/CODEMAP.md`) — mover exige atualizar `CLAUDE.md` e todas as
referências cruzadas nos próprios docs no mesmo commit.

---

**AGUARDANDO CONFIRMAÇÃO** — nada deste plano será executado (nem a reorganização de pastas,
nem código de P2.5) antes do OK explícito.
