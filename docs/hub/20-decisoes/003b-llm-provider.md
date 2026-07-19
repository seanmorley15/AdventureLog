# ADR 003b — Provedor/modelo LLM pra ranking de recomendações (P5b) 🔒

Status: **Aprovado** (2026-07-19). Modelo `claude-haiku-4-5` (default), budget mensal US$ 5,00
confirmados pelo Caio.

## Contexto

P5b (`docs/hub/30-planos/trilho-mvp-execucao.md` §P5b) precisa de um LLM pra: receber candidatos
da Overpass (P5a, já com tags `cuisine`/`wheelchair`/`opening_hours`/`fee`) + restrições do
usuário → devolver subconjunto ranqueado com justificativa curta, **referenciando só IDs do
input**. Guard-rail I1 obrigatório: todo ID retornado é validado contra o input; ID inexistente
é descartado e logado (backend, não LLM). Distância/coordenada nunca vêm do LLM — reusam
`routing/osrm_client.py`.

Restrição do plano: **custo zero além da VPS** — chave própria do Caio, budget mensal explícito
(tabela de restrições do plano de execução). Este ADR decide provedor, modelo e budget; P6
(assistente) reusa a decisão, não redecide.

## Decisão 1 — Provedor: Anthropic (chave própria)

Single-provider, sem abstração multi-provedor. Justificativa: uso pessoal, sem requisito de
failover entre provedores; Caio já opera no ecossistema Anthropic (Claude Code). Uma
abstração de provedor genérica seria complexidade sem benefício real pro escopo do MVP.

**[RESTRIÇÃO v1]** sem camada de abstração LLM-agnóstica — se algum dia precisar trocar de
provedor, é reescrita pontual do `places/ranking.py`, não um redesenho de arquitetura.

## Decisão 2 — Modelo: Claude Haiku 4.5, com fallback configurável

A tarefa (ranquear ~10-20 candidatos com tags estruturadas contra restrições explícitas, gerar
justificativa curta referenciando IDs) é classificação/ranking sobre contexto pequeno e
bem-formado — não exige raciocínio longo, chain-of-thought ou agentic loop. `claude-haiku-4-5`
(`$1,00 / $5,00` por MTok in/out) é suficiente e é o mais barato da família atual.

**Estimativa de custo por chamada** (pipeline P5b, não o assistente P6):
- Input: ~1.500 tokens (lista de candidatos com tags OSM + restrições + instrução)
- Output: ~400 tokens (subconjunto ranqueado + justificativas curtas)
- Custo por chamada Haiku 4.5: `(1500×1 + 400×5) / 1e6 ≈ US$ 0,0035`
- Custo por chamada Sonnet 5 (opção mais cara, caso Haiku decepcione): `(1500×3 + 400×15) / 1e6 ≈ US$ 0,0105` (preço padrão; há introdutório US$ 2/US$ 10 por MTok até 2026-08-31)

**`LLM_MODEL`** fica configurável via `.env` (5b.1, já previsto no plano) — default
`claude-haiku-4-5`, trocável pra `claude-sonnet-5` sem mudar código caso a qualidade de
ranking não seja boa o bastante na prática (avaliar no 5b.6/5b.7 com casos reais).

Sem thinking/effort elevado: tarefa não é agentic nem exige raciocínio longo — `thinking`
omitido (default) e sem necessidade de `output_config.effort` além do default.

## Decisão 3 — Budget mensal explícito

Estimativa de uso pessoal: viagens ocasionais, não uso diário contínuo. Cenário realista —
20 a 50 chamadas de sugestão por mês (poucas por parada, em dias de planejamento ativo):

| Cenário | Chamadas/mês | Custo Haiku 4.5 | Custo Sonnet 5 (se trocar) |
|---|---|---|---|
| Uso leve | 20 | ~US$ 0,07 | ~US$ 0,21 |
| Uso moderado | 50 | ~US$ 0,18 | ~US$ 0,53 |
| Uso pesado (viagem longa, muitas paradas) | 200 | ~US$ 0,70 | ~US$ 2,10 |

**Proposta de budget mensal: US$ 5,00** — folga generosa acima do cenário pesado mesmo com
Sonnet 5, cobrindo P5b sozinho. P6 (assistente, orquestração com mais chamadas por conversa)
reusa este teto — se P6 aproximar do limite, reabrir este ADR com números medidos (não é gate
novo automático, só reavaliação se o uso real divergir da estimativa).

**Como impor o teto:** sem rate-limit automático por chamada (`[RESTRIÇÃO v1]`, single-user).
Controle é observacional — acompanhar `usage` retornado por chamada (custo real, não estimado)
e revisar a fatura Anthropic mensalmente. Se preferir um limite duro, a Anthropic Console
permite configurar spend limit por chave — registrar aqui se o Caio configurar um.

**✅ Decisão do Caio (2026-07-19):** budget mensal confirmado em **US$ 5,00**. Sem spend limit
duro configurado na Console por ora — controle observacional (ver acima).

## Decisão 4 — Guard-rail I1 (reafirmação, não redecisão)

Já especificado no plano (5b.2) — este ADR não altera, só referencia: backend valida todo ID
retornado pelo LLM contra a lista de candidatos do input; ID inexistente é descartado e
logado, nunca exibido. LLM recebe **somente** a lista de candidatos + restrições — nunca gera
endereço, coordenada, distância ou horário como fato. Teste anti-alucinação (5b.6) usa LLM
mockado devolvendo ID falso → assert de descarte.

## Não implementado nesta fase

- Abstração multi-provedor (Decisão 1) — só Anthropic.
- Rate-limit por chamada/usuário (Decisão 3) — controle observacional, não imposição automática.
- Web search qualitativa (5b.4) — só se couber na sessão de P5b, senão registrado como não
  implementado (não bloqueante do MVP, já previsto no plano).

---

**APROVADO (2026-07-19)** — modelo `claude-haiku-4-5`, budget US$ 5,00/mês. Liberado pra
executar 5b.1→5b.8 na branch `fase-3b-ranking`.
