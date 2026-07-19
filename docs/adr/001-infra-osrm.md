# ADR 001 — Infraestrutura do OSRM self-hosted na VPS Hetzner

Status: **Passo 1/2 fechado. Passo 3 (deploy na VPS) pausado — achado novo: a VPS não tem Docker instalado. Decisão do usuário: seguir 100% local em Docker até o Trilho estar funcionando e correto; infra de produção só entra depois disso.**

## Contexto

O blueprint (`plans/trilho-blueprint.md`, Passo 1) já decidiu usar OSRM self-hosted via Docker
para a matriz de distâncias/durações da Fase 1 (otimização de rota multi-parada), em vez de
Google Routes. Este ADR registra o dimensionamento real desse serviço na VPS Hetzner que já
hospeda o SecretarIA, e a decisão go/no-go antes de qualquer deploy em produção.

## 1. Specs da VPS (fornecidas pelo usuário via console Hetzner, 2026-07-19)

| Item | Valor |
|---|---|
| vCPU | 2 |
| RAM total | 4 GB |
| Disco local | 40 GB |
| Uso atual reportado no console | 3,37 (unidade não confirmada — provavelmente GB de disco; **não confirma consumo de RAM nem consumo específico do SecretarIA**) |
| Tráfego | 0/20 TB |
| Preço | €5,49/mês |

### 1.1 Uso real medido (2026-07-19, SSH direto na VPS, SecretarIA no ar)

```
$ free -h
               total        used        free      shared  buff/cache   available
Mem:           3.7Gi       1.1Gi       386Mi       5.5Mi       2.5Gi       2.6Gi
Swap:             0B          0B          0B

$ df -h /
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        38G  8.1G   28G  23% /

$ docker stats --no-stream
bash: docker: command not found
```

**Achado que muda o plano: a VPS não tem Docker instalado.** SecretarIA roda direto via systemd
(sem container — `sqlite-web` via `pipx`, ver `SecretarIA/scripts/local/README.md`). `docker stats`
não pôde ser coletado porque não há Docker no host — não é uma falha de coleta, é ausência real do
runtime que todo o plano de deploy do Trilho (Passo 3, `docker-compose.osrm.yml`) pressupõe.

Leitura dos números disponíveis: 1,1 GiB "used" + 2,5 GiB "buff/cache" (recuperável sob pressão) em
3,7 GiB totais — folga real depende de quanto do buff/cache é elástico, não dá pra cravar sem medir
com o Trilho (e o OSRM) realmente rodando ali. Disco: 28 GiB livres, folgado para os extracts da
Seção 2/3 mesmo sem otimizar.

**Decisão do usuário (2026-07-19)**: não instalar Docker nem tocar na VPS agora. Desenvolvimento e
validação do Trilho seguem 100% locais (Docker Desktop), até a Fase 1 estar funcionando e correta.
Decisão de infra de produção (instalar Docker nessa VPS vs. upgrade de plano vs. VPS separada) fica
para depois, com o projeto já validado — não é mais um pré-requisito para fechar o Passo 1/2.

## 2. Escopo geográfico

Viagem real confirmada pelo usuário: **Itália — Roma, Florença, Milão, Bolonha**, com necessidade
de rota também **entre cidades** (não só dentro de cada uma).

Mapeamento para a divisão de extracts do Geofabrik (`download.geofabrik.de/europe/italy/`):
- Roma, Florença → região **centro** (Toscana, Umbria, Marche, Lazio)
- Milão → região **nord-ovest** (Piemonte, Liguria, Lombardia, Valle d'Aosta)
- Bolonha → região **nord-est** (Trentino-Alto Adige, Veneto, Friuli-Venezia Giulia, Emilia-Romagna)

Tamanhos reais dos `.pbf` (checados via `curl -I` em 2026-07-19, Geofabrik):

| Extract | Tamanho (.pbf) |
|---|---|
| Itália inteira | 2,06 GiB (2.211.673.275 bytes) |
| nord-ovest | 584.459.384 bytes (~557 MiB) |
| nord-est | 620.003.787 bytes (~591 MiB) |
| centro | 380.540.302 bytes (~363 MiB) |
| sud (não necessário) | 410.502.497 bytes |
| isole (não necessário) | 213.041.333 bytes |
| **Combinado (nord-ovest + nord-est + centro)** | **~1,48 GiB** |

## 3. Estimativa de RAM/disco — **ESTIMADO, NÃO MEDIDO** (decisão do usuário: aceitar esse risco por ora)

O blueprint original pedia medição real (rodar `osrm-extract`/`partition`/`customize` localmente e
anotar picos). Isso não foi possível nesta sessão: o sandbox de execução não tem Docker, não tem
privilégio de root (`sudo` bloqueado por "no new privileges") e só tem 3,9 GB de disco livre —
insuficiente até para o extract combinado. **Decisão do usuário: usar estimativa pública em vez de
medir agora.**

Fonte: [Project-OSRM/osrm-backend wiki — Disk and Memory Requirements](https://github.com/Project-OSRM/osrm-backend/wiki/Disk-and-Memory-Requirements)
(dados de referência: planeta OSM 11/2021, `.pbf` de 61 GiB, perfil `car`, algoritmo MLD;
o próprio wiki afirma que os tamanhos escalam aproximadamente linear com o tamanho do input —
premissa assumida aqui, não confirmada para extracts regionais menores).

Razões observadas (perfil `car`, MLD) e projeção para o extract combinado (1,48 GiB):

| Etapa | Razão sobre o `.pbf` (wiki) | Projeção p/ 1,48 GiB |
|---|---|---|
| `osrm-extract` (disco temporário) | 6,80× | ~10,0 GiB |
| `osrm-partition` (mld, disco temporário) | 3,61× | ~5,3 GiB |
| `osrm-customize` (mld, disco temporário) | 2,85× | ~4,2 GiB |
| Dataset final (`.osrm*`) | 4,92× | ~7,3 GiB |
| **RAM em runtime** (`osrm-routed` carrega o dataset quase inteiro em memória) | ~2,02× | **~3,0 GB** |

## 4. A soma que reprova a Itália inteira e aperta a região combinada

- **Itália inteira**: RAM estimada do OSRM sozinho (~4,2 GB) **já excede o total da VPS (4 GB)**.
  Reprovado sem precisar da soma completa — nem espaço pra Django/Postgres/SvelteKit/SecretarIA.
- **Região combinada (nord-ovest+nord-est+centro)**: RAM estimada do OSRM (~3,0 GB) deixa **~1 GB**
  de folga para sistema operacional + Django + PostGIS + SvelteKit + SecretarIA. **Não atinge a
  margem mínima de 20% exigida pelo blueprint** (Passo 1, tarefa 3) e o risco real é falha por
  OOM — o kernel Linux mata o processo que mais RAM está usando no momento, que pode não ser o
  OSRM.

## 5. Decisão registrada (2026-07-19)

**Usuário optou explicitamente por**: manter a VPS atual (não fazer upgrade agora), testar o
projeto funcionando, e só então decidir sobre upgrade de plano — mesmo com a estimativa acima
apontando risco de OOM.

Alternativa mais barata pesquisada e **recusada por ora** pelo usuário: Hetzner CX33
(4 vCPU, 8 GB RAM, 80 GB disco) por €6,49/mês (~+€1/mês sobre o plano atual) — resolveria o
problema de raiz com folga. Fica registrada como opção pronta para quando o teste mostrar
necessidade.

### Mitigações obrigatórias para aceitar esse risco (a implementar no Passo 2/3, não opcional)

1. **Limite de memória no container do OSRM** via `mem_limit`/`deploy.resources.limits.memory`
   no `docker-compose.osrm.yml`. Isso muda o pior caso de "o kernel mata um container qualquer,
   possivelmente o SecretarIA" para "o Docker mata/reinicia só o container do OSRM" — alinhado
   com I3 (SecretarIA sempre no ar) e I4 (degradação graciosa: sem OSRM, só a feature de
   otimização fica indisponível).
2. **Medir de verdade assim que o OSRM subir** (dev ou VPS): `docker stats --no-stream` durante e
   depois do `osrm-routed` no ar, e atualizar a Seção 3 deste ADR com números reais antes do
   Passo 3 (deploy em produção). A estimativa pública desta seção é só para destravar o Passo 2
   (código), não uma medição válida para produção.
3. Considerar, se o teste real mostrar aperto, um **extract customizado por corredor**
   (bounding box Milão–Bolonha–Florença–Roma via `osmium extract`) em vez dos 3 arquivos
   completos do Geofabrik — provavelmente bem menor que 1,48 GiB, já que exclui Valle d'Aosta,
   Liguria, Trentino, Friuli, Marche e Umbria, que não fazem parte do roteiro. Não implementado
   agora; registrado como próximo passo se o Passo 3 mostrar que não cabe.

## 6. Esboço de integração (compose + Django)

- Serviço `osrm` entra em **override opcional** `docker-compose.osrm.yml`, subido com
  `docker compose -f docker-compose.yml -f docker-compose.osrm.yml up` — nunca no compose
  principal (I4), já que os arquivos `.osrm*` pré-processados não vivem no repo.
- Cliente OSRM entra em um **novo app Django** `backend/server/routing/` (não em `adventures/`,
  para manter a mesma convenção de 1 app por domínio já usada no projeto — ver `docs/CODEMAP.md`
  seção 2). Consome o serviço `osrm` via `OSRM_URL` (env var opcional, ausente = feature
  indisponível, sem derrubar o resto do app).
- O algoritmo de otimização escreve de volta no campo `order` já existente de
  `CollectionItineraryItem` (não precisa de schema novo — achado do `docs/CODEMAP.md` seção 3).

## 7. Gate — status

- [x] VPS: specs estáticas do plano coletadas (console Hetzner).
- [x] VPS: uso real (RAM/disco) com SecretarIA no ar — medido em 2026-07-19, ver Seção 1.1.
      `docker stats` não aplicável — **VPS não tem Docker instalado** (achado novo, ver 1.1).
- [x] Escopo geográfico definido (Roma/Florença/Milão/Bolonha, cobertura intercidades).
- [x] Estimativa de RAM/disco do OSRM (pública, não medida — aceito como tal).
- [x] Decisão de risco registrada explicitamente pelo usuário.
- [x] Esboço de integração no compose/Django.
- [x] Suíte de testes `routing` + `adventures` rodada localmente (Docker Desktop): 23/23 passando
      (1 bug real de validação achado e corrigido em `adventures/views/itinerary_view.py` no
      caminho — view interceptava erro de `date`/`is_global` com chave `error` antes do
      serializer rodar `validate()`, que usa chave `date`; check duplicado removido).
- [x] `docker compose up` puro (sem `docker-compose.osrm.yml`) testado localmente: os 3 serviços
      sobem e respondem (backend HTTP 200, frontend HTTP 200).

**Gate do Passo 1/2: fechado.**

**Passo 3 (deploy na VPS): pausado, não bloqueado por decisão técnica — por escolha do usuário.**
A VPS não ter Docker teria virado um novo item de risco a mitigar (instalar Docker + reavaliar
RAM disponível pro OSRM), mas o usuário optou por não decidir infra de produção agora. Trilho
segue em desenvolvimento/validação 100% local via Docker Desktop. Quando a Fase 1 estiver
funcionando e correta, retomar aqui: decidir entre instalar Docker na VPS atual (reavaliando a
folga de RAM real da Seção 1.1 contra o runtime do Docker + OSRM) ou outra infra, antes de
declarar a Fase 1 "em produção".
