# ADR 003 — Overpass público + cache local (P5a)

Status: **Aprovado** (2026-07-19), decisão de execução dentro do P5a (blueprint §Passo 5),
sem gate humano (restrição de custo-zero já fixada no plano de execução).

## Contexto

P5a precisa buscar lugares próximos a uma parada (restaurantes, atrações, hospedagem) sem LLM
e sem custo. O CODEMAP §3 já apontou que `adventures/views/recommendations_view.py` consome a
Overpass API pública (`https://overpass-api.de/api/interpreter`) e o Google Places (opcional,
com chave). O app novo `places/` não reescreve esse cliente — reusa
`RecommendationsViewSet.query_overpass` via subclasse (`places/overpass_client.py`), adicionando
só a camada de cache que faltava.

## Decisão 1 — Endpoint público overpass-api.de, sem instância própria

**[RESTRIÇÃO v1]** Fair-use do endpoint público (~2 slots concorrentes por IP, ~10k
queries/dia) é suficiente para uso single-user. Self-host de instância Overpass própria
(container `overpass` com extract regional) fica descartado por ora — custo de RAM/disco
adicional na mesma VPS que já roda SecretarIA + (futuramente) OSRM, sem benefício real no
volume de uso pessoal.

**Reavaliar se:** a IP compartilhada com o SecretarIA começar a levar 429/504 com frequência,
ou o uso deixar de ser single-user.

## Decisão 2 — Cache local com TTL de 14 dias

`OverpassCacheEntry` (`places/models.py`) guarda a resposta já parseada (`payload` JSON) por
chave normalizada (`query_key` = sha256 de categoria + lat/lon arredondados a 4 casas decimais
+ raio). TTL fixo em **14 dias** (`PLACES_OVERPASS_CACHE_TTL_DAYS`, com esse default se a env
var não existir): dados de POI (restaurante, atração) mudam devagar; 14 dias equilibra
frescor razoável com poupar quota de fair-use numa viagem que dura dias.

Coordenadas arredondadas a 4 casas decimais (~11m de precisão) fazem buscas quase idênticas
(mesma parada, jitter de GPS) colidirem na mesma entrada de cache, sem misturar buscas
genuinamente distintas.

**Erros de rede/timeout não são cacheados** — só respostas bem-sucedidas. Assim uma
indisponibilidade temporária da Overpass não fica "presa" servindo erro vazio pelo TTL inteiro;
a próxima busca tenta de novo.

## Decisão 3 — User-Agent identificável

Header `User-Agent: Trilho/0.1 (uso pessoal; contato no repo)` nas queries do `places/`
(distinto do `AdventureLog Server` genérico usado por `recommendations_view.py`), conforme
boa prática de fair-use da Overpass (identificar quem está consultando).

## Não implementado nesta fase

- Instância Overpass própria (ver Decisão 1 — futuro, se necessário).
- Integração com Google Places no `places/` (P5a é escopo Overpass-only; `recommendations_view.py`
  já cobre Google Places separadamente, fora do escopo deste ADR).
