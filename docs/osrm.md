# OSRM self-hosted — pré-processamento e operação

Ver `docs/adr/001-infra-osrm.md` para a decisão de dimensionamento (por que a
Itália inteira foi reprovada, por que a combinação nord-ovest+nord-est+centro
foi escolhida para a viagem atual, e os riscos aceitos na VPS de 4 GB).

## Por que isso não sobe com `docker compose up` puro

Os arquivos `.osrm*` pré-processados (resultado de `osrm-extract` +
`osrm-partition` + `osrm-customize`) não vivem neste repositório — são
binários grandes (ver ADR 001, ordem de GB) e dependem da região escolhida
para cada viagem. Por isso o serviço `osrm` vive em
`docker-compose.osrm.yml`, um override **opcional**, nunca no compose
principal (invariante I4). `docker compose up` sem esse override continua
funcionando normalmente, sem o serviço OSRM.

## Pré-processar um extract (rodar localmente ou na VPS, fora do `up` normal)

1. Baixar o(s) `.pbf` da região necessária do Geofabrik. Exemplo para a
   combinação usada na viagem atual (Roma/Florença → centro; Milão →
   nord-ovest; Bolonha → nord-est):

   ```bash
   mkdir -p osrm-data && cd osrm-data
   curl -LO https://download.geofabrik.de/europe/italy/nord-ovest-latest.osm.pbf
   curl -LO https://download.geofabrik.de/europe/italy/nord-est-latest.osm.pbf
   curl -LO https://download.geofabrik.de/europe/italy/centro-latest.osm.pbf
   ```

2. Se a região cobrir mais de um arquivo (como acima), mesclar com
   `osmium merge` (pacote `osmium-tool`) antes de processar:

   ```bash
   osmium merge nord-ovest-latest.osm.pbf nord-est-latest.osm.pbf centro-latest.osm.pbf \
     -o region.osm.pbf
   ```

3. Rodar o pipeline oficial do OSRM via Docker (perfil `car`, algoritmo MLD):

   ```bash
   docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/region.osm.pbf
   docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-partition /data/region.osrm
   docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-customize /data/region.osrm
   ```

   **Meça o pico de RAM/disco de cada etapa** (`docker stats --no-stream`
   em outro terminal, ou `/usr/bin/time -v` se rodar sem Docker) e atualize
   a Seção 3 do `docs/adr/001-infra-osrm.md` com os números reais — a
   estimativa registrada lá hoje é pública (wiki do Project-OSRM), não
   medida neste projeto.

4. Copiar só os arquivos `region.osrm*` resultantes (não os `.pbf` de
   origem) para a VPS, no caminho relativo esperado pelo
   `docker-compose.osrm.yml` (`./osrm-data`).

## Subir o serviço

```bash
docker compose -f docker-compose.yml -f docker-compose.osrm.yml up -d
```

E no `.env`:
```
OSRM_URL=http://osrm:5000
```

Sem essa variável (ou com o serviço fora do ar), a feature "otimizar rota"
fica indisponível — o resto do Trilho continua funcionando normalmente
(invariante I4; comportamento coberto por `routing/tests.py` e
`adventures/tests.py::ItineraryOptimizeEndpointTests`).

## Cadência de re-extract

Manual, sob demanda — antes de uma viagem nova que cubra uma região ainda
não processada, ou se os dados do OpenStreetMap da região atual estiverem
visivelmente desatualizados. Sem automação agendada nesta fase; reavaliar
se o uso crescer.

## Limite conhecido do `/table`

O endpoint `/table` do OSRM tem um teto padrão de 100 coordenadas por
chamada (`--max-table-size`). `routing/osrm_client.py` levanta
`OSRMUnavailableError` acima desse limite em vez de truncar silenciosamente
— um dia de itinerário real não deve chegar perto desse número.
