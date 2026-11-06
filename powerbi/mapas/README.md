# Mapas do relatório

## `zonas_tlc.json`: as 263 zonas de táxi de Nova York (TopoJSON)

Usado pelo visual **Mapa de formas (Shape Map)** do Power BI. A chave é `LocationID`, que casa com `dim_zona[zona_id]` (e com `dim_zona_destino[zona_destino_id]`).

| Item | Valor |
|---|---|
| Fonte | TLC, página "TLC Trip Record Data", link "Taxi Zone Shapefile": `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip` |
| Versão da fonte | `Last-Modified: 19/02/2026`, 1.022.574 bytes, SHA-256 `f6d71191…5adf17` (baixado em 05/11/2026) |
| Sistema de coordenadas da fonte | NAD83 / State Plane New York Long Island (FIPS 3104), em pés norte-americanos (lido no `.prj`) |
| Ferramenta | `mapshaper@0.7.95` via `npx` (versão fixada; publicada em 22/10/2026) |
| Resultado | 263 formas, uma por `LocationID` (1 a 263, sem repetição), WGS84, 131.523 bytes |
| Atributos | `LocationID`, `zone`, `borough` |
| Prévia | `docs/validacao/img/fase-4-mapa-zonas-previa.png` |

As zonas 264 ("Unknown") e 265 ("Outside of NYC") existem na `dim_zona`, mas não têm forma: não aparecem no mapa, como esperado.

### Como refazer

Baixe e descompacte o zip numa pasta **fora do repositório** e rode, a partir de outra pasta:

```bash
npx -y mapshaper@0.7.95 <pasta>/taxi_zones/taxi_zones.shp \
  -proj wgs84 \
  -clean \
  -simplify 10% keep-shapes \
  -filter-fields LocationID,zone,borough \
  -rename-layers zonas \
  -o powerbi/mapas/zonas_tlc.json format=topojson
```

| Etapa | Por quê |
|---|---|
| `-proj wgs84` | A fonte está em pés (valores perto de 1.000.000); o Shape Map precisa de latitude e longitude |
| `-clean` | A fonte tem 777 frestas e sobreposições finas entre zonas vizinhas (largura de até 17 m). Sem a limpeza, a simplificação deixa 96 cruzamentos de linha sem reparo; com ela, nenhum. Também deixa o arquivo menor (248 KB → 132 KB), porque fronteiras vizinhas passam a ser uma linha só |
| `-simplify 10% keep-shapes` | Mantém 10% dos pontos removíveis; `keep-shapes` impede que zonas pequenas sumam (a ilha da 103 fica com 0,06 km²) |
| `-filter-fields` | Só a chave e dois atributos de rótulo |

### Conferências feitas (05/11/2026)

- 263 registros na fonte e no resultado; 263 `LocationID` distintas, de 1 a 263. Na versão de fevereiro de 2026 não há zona repetida (versões antigas tinham, segundo fontes secundárias): não foi preciso unir pedaços.
- Caixa de coordenadas: longitude de −74,256 a −73,700; latitude de 40,496 a 40,915.
- Testes de simplificação (sem `-clean`): 5% → 209 KB e 56 cruzamentos; 10% → 248 KB e 96; 20% → 322 KB e 136; sem simplificar → 852 KB.
- Avisos do `npm` sobre dependências antigas do mapshaper (`geographiclib`, `prebuild-install`): a ferramenta roda só localmente, sobre um arquivo público da TLC.
