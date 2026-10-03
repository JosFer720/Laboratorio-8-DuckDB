# Benchmark: Parquet directo vs tabla DuckDB

Compara ejecutar las mismas consultas (a) leyendo los archivos Parquet y (b)
sobre la tabla `trips` materializada en DuckDB. Se reproduce con:

```bash
docker compose exec lab python scripts/benchmark.py            # 3 repeticiones por consulta
docker compose exec lab python scripts/benchmark.py --repeat 5
```

Los resultados completos quedan en [`benchmark_results.csv`](benchmark_results.csv).

## Metodologia

- **Tabla materializada**: `scripts/create_database.py` ejecuta
  `sql/create_tables.sql`, que une yellow y green en `trips`, normaliza nombres y
  tipos y agrega `taxi_type`, `year`, `month` y `duration_minutes`.
- **Parquet directo**: el benchmark crea una vista `trips` con *el mismo SELECT*
  sobre `read_parquet(...)`. Asi las consultas son textualmente identicas en
  ambas estrategias y solo cambia donde estan los datos.
- **Conjuntos de datos** (para observar el efecto del volumen): los anios
  descargados se acumulan: `2024` (41.8 M de filas) y `2024+2026` (71.9 M). Para
  cada uno se construye una tabla solo con esos anios.
- **Medicion**: una ejecucion de calentamiento sin medir y luego 3 repeticiones;
  se reporta la **mediana**. Los archivos Parquet quedan en la cache del sistema
  operativo tras el calentamiento, de modo que se mide la velocidad con archivos
  "calientes", no la lectura desde disco frio.
- **Verificacion**: el script compara los resultados de ambas estrategias y
  falla si difieren; en todas las consultas dieron el mismo resultado
  (`same_result = True`).
- **Entorno**: contenedor Docker en una maquina con 12 hilos, DuckDB 1.5.5.

## Consultas

Texto completo en [`sql/benchmark_queries.sql`](../sql/benchmark_queries.sql).

| Id | Que hace | Tipo de operacion |
| --- | --- | --- |
| q1 | Conteo total de viajes | metadatos |
| q2 | Viajes por tipo, anio y mes | agregacion por grupos pequeno |
| q3 | Distancia, tarifa y propina promedio por tipo (viajes validos) | filtros y agregacion |
| q4 | Viajes e ingreso por hora del dia | extraccion de fecha y agregacion |
| q5 | Viajes y propina por forma de pago | agregacion |
| q6 | Top 10 zonas de origen | agregacion y ordenamiento |
| q7 | Percentiles de la tarifa | agregacion costosa (requiere ordenar valores) |
| q8 | Conteo de viajes atipicos | varios `count_if` |
| q9 | Consulta selectiva (yellow, enero, efectivo, mas de 20 millas) | filtros muy selectivos |

## Resultados (segundos, mediana)

| Consulta | 2024: Parquet | 2024: tabla | Veces mas rapida | 2024+2026: Parquet | 2024+2026: tabla | Veces mas rapida |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q1 conteo | 0.059 | 0.003 | 23.8x | 0.095 | 0.003 | 29.8x |
| q2 viajes por mes | 0.147 | 0.128 | 1.1x | 0.143 | 0.166 | 0.9x |
| q3 promedios | 0.431 | 0.218 | 2.0x | 0.923 | 0.349 | 2.6x |
| q4 por hora | 0.562 | 0.088 | 6.4x | 1.008 | 0.219 | 4.6x |
| q5 formas de pago | 0.253 | 0.054 | 4.6x | 0.476 | 0.096 | 5.0x |
| q6 zonas de origen | 0.252 | 0.056 | 4.5x | 0.474 | 0.096 | 4.9x |
| q7 percentiles | 3.679 | 2.881 | 1.3x | 5.414 | 5.199 | 1.0x |
| q8 atipicos | 1.117 | 0.181 | 6.2x | 1.951 | 0.255 | 7.6x |
| q9 selectiva | 0.094 | 0.005 | 17.6x | 0.107 | 0.009 | 12.5x |

Costo de materializar la tabla (`CREATE TABLE trips`, una sola vez): **72.5 s**
para 2024 y **105.7 s** para 2024+2026. La base resultante ocupa 2.1 GB frente a
1.2 GB de Parquet comprimido.

## Analisis

- **La tabla gana casi siempre**, entre 2 y 30 veces, y la diferencia absoluta
  crece con el volumen: en q4 pasa de 0.47 s a 0.79 s de ventaja al agregar 2026.
  Parquet escala de forma aproximadamente lineal con los datos que debe leer
  (q3 pasa de 0.43 s a 0.92 s con 1.7 veces mas filas).
- **Por que gana la tabla**: DuckDB ya almacena las columnas descomprimidas y
  con estadisticas propias, mientras que con Parquet cada consulta debe leer y
  decodificar los archivos y, en esta vista, ademas calcular `year`, `month`,
  `duration_minutes` y las conversiones de tipo para cada fila. La tabla guarda
  esos campos ya calculados.
- **Las mayores ventajas** aparecen en las consultas que tocan pocas columnas o
  muy pocas filas (q1 y q9, hasta 30x) porque la tabla responde con sus
  estadisticas internas o descarta bloques enteros.
- **Casi no hay diferencia** en q2, que solo usa las columnas `year` y `month`
  (derivadas del nombre del archivo, es decir, de metadatos baratos de leer en
  Parquet), ni en q7: calcular percentiles exige ordenar todos los valores y el
  tiempo lo domina el calculo, no la lectura.
- **No hubo diferencias de resultados** entre estrategias; las consultas son
  equivalentes.

## Cuando conviene cada estrategia

**Consultar Parquet directamente** cuando:

- se explora por primera vez o se hacen pocas consultas: no hay costo de carga y
  la respuesta llega en segundos (aqui, de 0.1 a 5 s sobre 72 M de filas);
- los datos cambian a menudo (llegan meses nuevos): basta con descargar el
  archivo, sin reconstruir nada;
- el espacio en disco importa o los archivos los consumen otras herramientas.

**Materializar una tabla** cuando:

- se repiten muchas consultas sobre los mismos datos (tableros, notebooks,
  Metabase), porque el costo de 70 a 110 s se amortiza: la ventaja es de 4.2 s
  por cada pasada de las 9 consultas sobre 2024+2026, es decir, se recupera
  aproximadamente despues de 25 pasadas completas;
- se necesitan columnas derivadas, tipos fijos y una unica version de los datos
  ya limpiados;
- se quiere una sola base que herramientas externas puedan abrir en solo lectura.

En este proyecto se usan ambas: Parquet para la exploracion y la validacion de
cada descarga, y la tabla `trips` para el analisis repetido, los indicadores y el
tablero.

## Limitaciones

- Las mediciones se hicieron en una sola maquina con los archivos en la cache
  del sistema operativo; con disco frio, Parquet seria mas lento en la primera
  consulta.
- La vista sobre Parquet incluye las conversiones del SELECT de
  `create_tables.sql`; leer los Parquet sin esas conversiones seria algo mas
  rapido, pero entonces las consultas no serian equivalentes.
- Con solo dos conjuntos de datos la tendencia con el volumen es indicativa; al
  incorporar 2025 el benchmark agrega un tercer punto sin cambios en el codigo.
