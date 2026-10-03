# Consultas de exploracion sobre Parquet

Documentacion de las consultas de [`sql/exploration.sql`](../sql/exploration.sql).
Se ejecutan con:

```bash
docker compose exec -T lab python scripts/run_sql.py sql/exploration.sql
```

Todas leen los archivos Parquet directamente, sin importarlos a una tabla. Los
resultados corresponden a los datos descargados el 2 de octubre de 2026 (2024
completo y 2026 de enero a agosto; ver [`data_quality.md`](data_quality.md)).

## Que significa consultar directamente un archivo Parquet

`read_parquet('ruta/*.parquet')` convierte los archivos en una fuente de datos
que DuckDB trata como si fuera una tabla, pero sin cargar nada previamente: la
consulta se ejecuta leyendo los archivos en el momento. Parquet es un formato
columnar y comprimido que guarda metadatos (numero de filas, minimos y maximos
por bloque) en el propio archivo. Por eso, cuando el volumen es grande:

- **solo se leen las columnas que la consulta usa** y no las 20 del archivo;
- **se omiten bloques completos** que los filtros descartan segun sus minimos y
  maximos;
- **un `count(*)` se responde con los metadatos**, sin leer los datos;
- **no hay paso de importacion**: el archivo recien descargado ya se puede
  consultar, y los archivos no ocupan espacio duplicado;
- **los archivos se leen en paralelo** y la memoria no tiene que alojar todo el
  conjunto (aqui hay mas de 70 millones de filas).

La limitacion es que cada consulta vuelve a abrir, descomprimir y decodificar
los archivos; el [benchmark](benchmark.md) cuantifica ese costo.

## Consultas

| # | Objetivo | Fuente | Resultado obtenido | Decision tomada |
| --- | --- | --- | --- | --- |
| 1 | Cantidad de archivos disponibles (`glob`) | `data/raw/{yellow,green}/*/*.parquet` | 20 archivos por tipo (12 de 2024 y 8 de 2026) | No faltan meses publicados: 2026 llega hasta agosto porque la TLC aun no publica septiembre en adelante |
| 2 | Cantidad de registros, total y por archivo | igual | 70,873,075 yellow y 997,332 green; ningun mes vacio ni incompleto | Se usa `union_by_name` en todas las lecturas por el cambio de columnas entre anios |
| 3 | Columnas y tipos (`DESCRIBE`) | igual | 21 columnas yellow y 22 green al unir 2024 y 2026 (los archivos de 2024 tienen 19 y 20); tipos `INTEGER`, `BIGINT`, `DOUBLE`, `TIMESTAMP`, `VARCHAR`; las marcas de tiempo se llaman `tpep_*` en yellow y `lpep_*` en green | Yellow y green se consultan por separado y se normalizan despues al crear la tabla `trips` |
| 4 | Muestra de 10 registros (`LIMIT 10`) | igual | Registros con aspecto normal; algunas columnas de cargos adicionales (`Airport_fee`, `ehail_fee`) vienen vacias | La tabla `trips` conserva solo las columnas que usa el analisis y excluye esos cargos adicionales |
| 5 | Calidad yellow: nulos, distancias cero, montos negativos, duraciones invalidas, extremos (por anio) | `data/raw/yellow/*/*.parquet` | Sin nulos en campos clave; 952,231 distancias cero y 371,683 duraciones no positivas en 2026; montos negativos en 609,344 (2024) y 161,835 (2026) | No se borran filas; se define "viaje valido" para los promedios (ver `data_quality.md`) |
| 6 | Calidad green, mismos controles | `data/raw/green/*/*.parquet` | Mismos tipos de problema en menor escala (por ejemplo 34,574 distancias cero en 2024) | Se aplica la misma regla de viaje valido a ambos tipos |

Cada consulta tiene su texto SQL, con comentarios, en el archivo
`sql/exploration.sql`, en la seccion del mismo numero (las secciones 2 a 6 incluyen
una consulta por tipo de taxi).
