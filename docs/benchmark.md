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
  descargados se acumulan: `2024` (41.8 M de filas), `2024+2025` (91.1 M) y
  `2024+2025+2026` (121.2 M). Para cada uno se construye una tabla solo con esos
  anios. El script descubre los anios en `data/raw/`, por lo que el tercer
  conjunto aparecio sin modificar el codigo al descargar 2025.
- **Medicion**: una ejecucion de calentamiento sin medir y luego 3 repeticiones;
  se reporta la **mediana**. Los archivos Parquet quedan en la cache del sistema
  operativo tras el calentamiento, de modo que se mide la velocidad con archivos
  "calientes", no la lectura desde disco frio.
- **Verificacion**: el script compara los resultados de ambas estrategias y
  falla si difieren; en todas las consultas dieron el mismo resultado
  (`same_result = True`).
- **Entorno**: contenedor Docker (14 CPU y 7.7 GB de memoria asignados) en un
  Apple M3 Max, DuckDB 1.5.5.

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

**Cambio en q7 al incorporar 2025.** La version original pedia la mediana, el
p95 y el p99 con tres llamadas a `quantile_cont`. Cada llamada guarda en memoria
todos los valores de su grupo, asi que con 121 M de filas la consulta de
percentiles de `sql/analysis.sql` (seis llamadas) agoto la memoria del
contenedor (codigo de salida 137). Ahora se usa una sola llamada con una lista
de percentiles, `quantile_cont(fare_amount, [0.5, 0.95, 0.99])`, que calcula los
mismos valores con un solo estado. El costo de q7 sigue dominado por el calculo.

## Resultados (segundos, mediana de 3 repeticiones)

| Consulta | 2024 Parquet | 2024 tabla | x | 2024+2025 Parquet | 2024+2025 tabla | x | 3 anios Parquet | 3 anios tabla | x |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| q1 conteo | 0.007 | 0.002 | 4.2 | 0.012 | 0.004 | 3.1 | 0.016 | 0.002 | 6.6 |
| q2 viajes por mes | 0.021 | 0.043 | 0.5 | 0.039 | 0.082 | 0.5 | 0.052 | 0.104 | 0.5 |
| q3 promedios | 0.119 | 0.091 | 1.3 | 0.232 | 0.198 | 1.2 | 0.311 | 0.260 | 1.2 |
| q4 por hora | 0.159 | 0.050 | 3.2 | 0.307 | 0.088 | 3.5 | 0.442 | 0.122 | 3.6 |
| q5 formas de pago | 0.084 | 0.030 | 2.8 | 0.154 | 0.059 | 2.6 | 0.204 | 0.087 | 2.3 |
| q6 zonas de origen | 0.071 | 0.016 | 4.4 | 0.132 | 0.033 | 4.0 | 0.182 | 0.046 | 3.9 |
| q7 percentiles | 1.158 | 1.115 | 1.0 | 2.669 | 2.539 | 1.1 | 3.347 | 3.462 | 1.0 |
| q8 atipicos | 0.259 | 0.071 | 3.6 | 0.549 | 0.155 | 3.5 | 0.723 | 0.223 | 3.2 |
| q9 selectiva | 0.019 | 0.002 | 12.5 | 0.023 | 0.003 | 8.6 | 0.030 | 0.004 | 7.0 |
| **Suma de las 9** | **1.897** | **1.420** | **1.3** | **4.117** | **3.161** | **1.3** | **5.307** | **4.310** | **1.2** |
| Suma sin q7 | 0.739 | 0.305 | 2.4 | 1.448 | 0.622 | 2.3 | 1.960 | 0.848 | 2.3 |

`x` = tiempo con Parquet / tiempo con la tabla (mayor que 1: la tabla es mas
rapida).

Costo de materializar la tabla (`CREATE TABLE trips`, una sola vez): **3.0 s**
para 2024, **6.1 s** para 2024+2025 y **7.8 s** para los tres anios. La base de
los tres anios ocupa 3.4 GB frente a 1.9 GB de Parquet comprimido.

### Corrida anterior (otra maquina, dos conjuntos)

Antes de incorporar 2025 el benchmark se ejecuto en una maquina con 12 hilos con
los conjuntos `2024` y `2024+2026`. Los tiempos absolutos eran entre 3 y 25 veces
mayores (por ejemplo, materializar 2024 tardaba 72.5 s frente a 3.0 s y q4 sobre
Parquet 0.56 s frente a 0.16 s), pero el patron relativo fue el mismo: la tabla ganaba entre 4 y
8 veces en q4, q5, q6 y q8 y hasta 30 veces en q1 y q9, empataba en q2 y q7, y
la ventaja absoluta crecia con el volumen. Esos resultados estan en el historial
de Git de `docs/benchmark_results.csv`.

## Analisis

- **Ambas estrategias escalan de forma aproximadamente lineal con las filas.**
  De 41.8 M a 121.2 M de filas (2.9 veces) q4 pasa de 0.16 s a 0.44 s con Parquet
  (2.8 veces) y de 0.05 s a 0.12 s con la tabla (2.4 veces). La materializacion
  tambien crece linealmente (3.0, 6.1 y 7.8 s).
- **La tabla gana en casi todo, pero por un margen moderado en esta maquina:**
  de 2.3 a 4.4 veces en las agregaciones (q4, q5, q6, q8) y hasta 12 veces en las
  consultas que la tabla resuelve con estadisticas internas o descartando
  bloques (q1 conteo y q9 selectiva). La ventaja absoluta crece con el volumen:
  sin q7 la tabla ahorra 0.43 s por pasada con 2024 y 1.11 s con los tres anios.
- **Por que gana la tabla**: DuckDB ya almacena las columnas en su formato
  nativo y con estadisticas propias, mientras que con Parquet cada consulta debe
  abrir 64 archivos, decodificarlos y, en esta vista, ademas calcular `year`,
  `month`, `duration_minutes` y las conversiones de tipo para cada fila. La
  tabla guarda esos campos ya calculados.
- **Parquet gana en q2** (0.5x): solo usa `taxi_type`, `year` y `month`, que en la
  vista salen del nombre del archivo y de una constante, es decir, de metadatos
  baratos; en la tabla son columnas que hay que leer de verdad.
- **Empate en q7**: calcular percentiles exige ordenar todos los valores; el
  tiempo lo domina el calculo, no la lectura, y es la consulta que mas crece con
  el volumen (2.9 veces mas datos, 2.9 veces mas tiempo).
- **El hardware importa mas que la estrategia**: la misma consulta fue entre 3 y
  25 veces mas rapida en la maquina nueva, una diferencia mayor que la que hay
  entre Parquet y la tabla en una misma maquina.
- **No hubo diferencias de resultados** entre estrategias; las consultas son
  equivalentes.

## Cuando conviene cada estrategia

**Consultar Parquet directamente** cuando:

- se explora por primera vez o se hacen pocas consultas: no hay costo de carga y
  la respuesta llega en menos de un segundo para la mayoria de las consultas
  (aqui, sobre 121 M de filas);
- los datos cambian a menudo (llegan meses nuevos): basta con descargar el
  archivo, sin reconstruir nada;
- se necesitan columnas que la tabla no materializa, como `cbd_congestion_fee`,
  que solo existe desde 2025 (ver `notebooks/evolucion_2024_2026.ipynb`);
- el espacio en disco importa (la tabla ocupa 1.8 veces mas que los Parquet) o
  los archivos los consumen otras herramientas.

**Materializar una tabla** cuando:

- se repiten muchas consultas sobre los mismos datos (tableros, notebooks,
  Metabase): con los tres anios la tabla ahorra ~1 s por pasada de las 9
  consultas, de modo que los 7.8 s de construccion se recuperan despues de unas
  8 pasadas; en la maquina anterior la cuenta era de unas 25 pasadas;
- se necesitan columnas derivadas, tipos fijos y una unica version de los datos
  ya limpiados;
- se quiere una sola base que herramientas externas puedan abrir en solo lectura
  (Metabase lee `data/processed/taxi.duckdb`).

En este proyecto se usan ambas: Parquet para la exploracion, la validacion de
cada descarga y las columnas nuevas, y la tabla `trips` para el analisis
repetido, los indicadores y el tablero.

## Limitaciones

- Las mediciones se hicieron en una sola maquina con los archivos en la cache
  del sistema operativo; con disco frio, Parquet seria mas lento en la primera
  consulta.
- La vista sobre Parquet incluye las conversiones del SELECT de
  `create_tables.sql`; leer los Parquet sin esas conversiones seria algo mas
  rapido, pero entonces las consultas no serian equivalentes.
- Con tiempos de milisegundos (q1, q9) la variacion entre repeticiones es del
  mismo orden que la diferencia medida; las razones de esas consultas son
  indicativas.
