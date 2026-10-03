# Consultas de exploración sobre Parquet

Este documento explica las consultas de [`sql/exploration.sql`](../sql/exploration.sql), que son la primera
exploración de los datos. Todas leen los archivos Parquet directamente, sin cargarlos antes en una tabla. Se
ejecutan con este comando.

```bash
docker compose exec -T lab python scripts/run_sql.py sql/exploration.sql
```

Los resultados que aparecen aquí corresponden a los datos descargados el 2 de octubre de 2026, que son 2024 y 2025
completos y 2026 de enero a agosto. Más detalles sobre los problemas de calidad están en
[`data_quality.md`](data_quality.md). Las consultas no cambiaron al agregar 2024 ni 2025, porque buscan los archivos
con el comodín `*/*.parquet`, que incluye cualquier carpeta de año.

## Qué significa consultar directamente un archivo Parquet

Parquet es un formato de archivo para guardar tablas grandes. Guarda los datos por columnas y comprimidos, y además
guarda información sobre su propio contenido, como cuántas filas tiene y cuál es el valor más chico y el más grande
de cada bloque de datos. Con `read_parquet('ruta/*.parquet')`, DuckDB trata uno o muchos archivos como si fueran una
tabla, pero sin cargar nada antes. Cada consulta lee los archivos en el momento en que se ejecuta.

Esto ayuda mucho cuando hay muchos datos. DuckDB solo lee las columnas que la consulta usa, de las cerca de 20 que tiene
cada archivo. También se salta bloques completos cuando sus valores no pueden cumplir el filtro, y responde un
`count(*)` usando la información guardada en el archivo, sin leer los datos. No hay que esperar a importar nada, un
archivo recién descargado ya se puede consultar y los datos no se guardan dos veces. DuckDB además lee varios
archivos al mismo tiempo y no necesita meter en la memoria los más de 120 millones de filas.

La desventaja es que cada consulta tiene que volver a abrir, descomprimir y leer los archivos. El
[benchmark](benchmark.md) mide cuánto cuesta eso comparado con una tabla de DuckDB.

## Las consultas

Cada consulta se hace por separado para yellow y para green, porque los dos tipos de taxi nombran distinto las
columnas de fecha. Yellow las llama `tpep_pickup_datetime` y `tpep_dropoff_datetime`, y green las llama
`lpep_pickup_datetime` y `lpep_dropoff_datetime`.

### 1. Cantidad de archivos disponibles

El objetivo es saber si están todos los archivos que se esperaban. Usa `glob()`, que lista los archivos que
coinciden con una ruta sin abrirlos. Los archivos fuente son `data/raw/yellow/*/*.parquet` y
`data/raw/green/*/*.parquet`.

```sql
-- glob() permite revisar la descarga sin abrir los archivos Parquet.
SELECT
    'yellow' AS taxi_type,
    count(*) AS file_count
FROM glob('data/raw/yellow/*/*.parquet')

UNION ALL

SELECT
    'green' AS taxi_type,
    count(*) AS file_count
FROM glob('data/raw/green/*/*.parquet')
ORDER BY taxi_type;
```

El resultado fue de 32 archivos por tipo de taxi, 12 de 2024, 12 de 2025 y 8 de 2026. Con esto se decidió que no
faltaba ningún mes publicado. 2026 llega hasta agosto porque la TLC todavía no publica septiembre en adelante, y el
script de descarga reporta esos meses como no publicados.

### 2. Cantidad de registros, en total y por archivo

El objetivo es saber cuántos viajes hay y revisar que ningún mes venga vacío o con muy pocos registros. Las
consultas leen los mismos archivos de la consulta 1. La primera cuenta el total de cada tipo de taxi y las otras
dos cuentan los registros de cada archivo, usando `filename = true` para saber de qué archivo viene cada fila.

```sql
SELECT
    'yellow' AS taxi_type,
    count(*) AS record_count
FROM read_parquet(
    'data/raw/yellow/*/*.parquet',
    union_by_name = true
)

UNION ALL

SELECT
    'green' AS taxi_type,
    count(*) AS record_count
FROM read_parquet(
    'data/raw/green/*/*.parquet',
    union_by_name = true
)
ORDER BY taxi_type;

-- El desglose por archivo ayuda a detectar meses vacios o incompletos.
SELECT
    filename,
    count(*) AS record_count
FROM read_parquet(
    'data/raw/yellow/*/*.parquet',
    filename = true,
    union_by_name = true
)
GROUP BY filename
ORDER BY filename;

SELECT
    filename,
    count(*) AS record_count
FROM read_parquet(
    'data/raw/green/*/*.parquet',
    filename = true,
    union_by_name = true
)
GROUP BY filename
ORDER BY filename;
```

El resultado fue de 119,595,677 viajes yellow y 1,588,707 viajes green. Por archivo, los meses de yellow van de
2,964,624 a 4,591,845 viajes y los de green de 37,373 a 61,003, sin ningún mes vacío. Como las columnas cambian de un
año a otro, se decidió leer siempre con `union_by_name = true`. Esa opción junta los archivos por el nombre de cada
columna y deja vacías las columnas que no existen en un archivo, en lugar de dar error.

### 3. Columnas y tipos de datos

El objetivo es conocer qué columnas trae cada tipo de taxi y de qué tipo es cada una, por ejemplo número entero,
número con decimales, fecha o texto. Usa `DESCRIBE`, que muestra la estructura de la consulta sin leer los datos, y
lee los mismos archivos de las consultas anteriores.

```sql
DESCRIBE SELECT *
FROM read_parquet(
    'data/raw/yellow/*/*.parquet',
    union_by_name = true
);

DESCRIBE SELECT *
FROM read_parquet(
    'data/raw/green/*/*.parquet',
    union_by_name = true
);
```

Al juntar los tres años hay 21 columnas en yellow y 22 en green. Los archivos de 2024 tienen 19 y 20, porque
`cbd_congestion_fee` aparece en enero de 2025 y `request_source` en junio de 2026. Los tipos son `INTEGER`, `BIGINT`,
`DOUBLE`, `TIMESTAMP` y `VARCHAR`, y las columnas de fecha tienen nombres distintos en cada tipo de taxi. Por eso se
decidió consultar yellow y green por separado, y después unirlos con los mismos nombres de columna al crear la tabla
`trips`.

### 4. Muestra de registros

El objetivo es ver cómo se ven los datos de verdad, fila por fila. Toma 10 registros de cada tipo de taxi con
`LIMIT 10`, de los mismos archivos.

```sql
SELECT *
FROM read_parquet(
    'data/raw/yellow/*/*.parquet',
    union_by_name = true
)
LIMIT 10;

SELECT *
FROM read_parquet(
    'data/raw/green/*/*.parquet',
    union_by_name = true
)
LIMIT 10;
```

Los registros se ven normales, con fechas, distancias y montos razonables. Pero ya en la muestra aparecen cosas
raras, como un viaje con 0 pasajeros y otro de 0.04 millas que duró un minuto. Algunas columnas de cargos extra
vienen vacías, por ejemplo `ehail_fee` en green. Con esto se decidió que la tabla `trips` guarde solo las columnas
que usa el análisis y deje fuera esos cargos extra.

### 5. Revisión inicial de calidad para yellow

El objetivo es medir, por año, cuántos registros tienen problemas. Cuenta valores vacíos en las columnas
importantes, distancias de cero o negativas, tarifas y montos negativos, viajes que terminan antes de empezar,
distancias de más de 100 millas, duraciones de más de 24 horas y montos de más de 1,000 dólares. La segunda consulta
muestra el valor más chico y el más grande de distancia, tarifa, monto y duración. Lee `data/raw/yellow/*/*.parquet`
y saca el año del nombre de cada archivo.

```sql
-- Los umbrales de atipicos son reglas de revision, no filtros definitivos.
-- Se reportan conteos para no perder filas durante esta exploracion inicial.
SELECT
    regexp_extract(filename, 'tripdata_([0-9]{4})', 1) AS year,
    count(*) AS total_records,
    count_if(VendorID IS NULL) AS null_vendor_id,
    count_if(tpep_pickup_datetime IS NULL) AS null_pickup_datetime,
    count_if(tpep_dropoff_datetime IS NULL) AS null_dropoff_datetime,
    count_if(PULocationID IS NULL) AS null_pickup_location_id,
    count_if(DOLocationID IS NULL) AS null_dropoff_location_id,
    count_if(trip_distance IS NULL) AS null_trip_distance,
    count_if(fare_amount IS NULL) AS null_fare_amount,
    count_if(total_amount IS NULL) AS null_total_amount,
    count_if(trip_distance = 0) AS zero_distance,
    count_if(trip_distance < 0) AS negative_distance,
    count_if(fare_amount < 0) AS negative_fare_amount,
    count_if(total_amount < 0) AS negative_total_amount,
    count_if(
        tpep_pickup_datetime IS NOT NULL
        AND tpep_dropoff_datetime IS NOT NULL
        AND tpep_dropoff_datetime <= tpep_pickup_datetime
    ) AS invalid_duration,
    count_if(trip_distance > 100) AS distance_over_100_miles,
    count_if(
        tpep_pickup_datetime IS NOT NULL
        AND tpep_dropoff_datetime IS NOT NULL
        AND date_diff(
            'second',
            tpep_pickup_datetime,
            tpep_dropoff_datetime
        ) > 86400
    ) AS duration_over_24_hours,
    count_if(total_amount > 1000) AS total_amount_over_1000
FROM read_parquet(
    'data/raw/yellow/*/*.parquet',
    union_by_name = true,
    filename = true
)
GROUP BY year
ORDER BY year;

-- Rangos observados para contextualizar los conteos anteriores.
SELECT
    regexp_extract(filename, 'tripdata_([0-9]{4})', 1) AS year,
    min(trip_distance) AS min_trip_distance,
    max(trip_distance) AS max_trip_distance,
    min(fare_amount) AS min_fare_amount,
    max(fare_amount) AS max_fare_amount,
    min(total_amount) AS min_total_amount,
    max(total_amount) AS max_total_amount,
    min(date_diff(
        'second',
        tpep_pickup_datetime,
        tpep_dropoff_datetime
    )) AS min_duration_seconds,
    max(date_diff(
        'second',
        tpep_pickup_datetime,
        tpep_dropoff_datetime
    )) AS max_duration_seconds
FROM read_parquet(
    'data/raw/yellow/*/*.parquet',
    union_by_name = true,
    filename = true
)
GROUP BY year
ORDER BY year;
```

No hay valores vacíos en las columnas importantes. Los viajes con duración cero o negativa son 13,510 en 2024,
546,304 en 2025 y 371,683 en 2026, y los montos negativos son 609,344, 973,721 y 161,835. Los extremos muestran
errores claros, como distancias de casi 400 mil millas. Se decidió no borrar ninguna fila y definir una regla de
viaje válido para calcular los promedios, que se explica en `data_quality.md`.

### 6. Revisión inicial de calidad para green

El objetivo y los controles son los mismos de la consulta 5, aplicados a `data/raw/green/*/*.parquet`.

```sql
SELECT
    regexp_extract(filename, 'tripdata_([0-9]{4})', 1) AS year,
    count(*) AS total_records,
    count_if(VendorID IS NULL) AS null_vendor_id,
    count_if(lpep_pickup_datetime IS NULL) AS null_pickup_datetime,
    count_if(lpep_dropoff_datetime IS NULL) AS null_dropoff_datetime,
    count_if(PULocationID IS NULL) AS null_pickup_location_id,
    count_if(DOLocationID IS NULL) AS null_dropoff_location_id,
    count_if(trip_distance IS NULL) AS null_trip_distance,
    count_if(fare_amount IS NULL) AS null_fare_amount,
    count_if(total_amount IS NULL) AS null_total_amount,
    count_if(trip_distance = 0) AS zero_distance,
    count_if(trip_distance < 0) AS negative_distance,
    count_if(fare_amount < 0) AS negative_fare_amount,
    count_if(total_amount < 0) AS negative_total_amount,
    count_if(
        lpep_pickup_datetime IS NOT NULL
        AND lpep_dropoff_datetime IS NOT NULL
        AND lpep_dropoff_datetime <= lpep_pickup_datetime
    ) AS invalid_duration,
    count_if(trip_distance > 100) AS distance_over_100_miles,
    count_if(
        lpep_pickup_datetime IS NOT NULL
        AND lpep_dropoff_datetime IS NOT NULL
        AND date_diff(
            'second',
            lpep_pickup_datetime,
            lpep_dropoff_datetime
        ) > 86400
    ) AS duration_over_24_hours,
    count_if(total_amount > 1000) AS total_amount_over_1000
FROM read_parquet(
    'data/raw/green/*/*.parquet',
    union_by_name = true,
    filename = true
)
GROUP BY year
ORDER BY year;

SELECT
    regexp_extract(filename, 'tripdata_([0-9]{4})', 1) AS year,
    min(trip_distance) AS min_trip_distance,
    max(trip_distance) AS max_trip_distance,
    min(fare_amount) AS min_fare_amount,
    max(fare_amount) AS max_fare_amount,
    min(total_amount) AS min_total_amount,
    max(total_amount) AS max_total_amount,
    min(date_diff(
        'second',
        lpep_pickup_datetime,
        lpep_dropoff_datetime
    )) AS min_duration_seconds,
    max(date_diff(
        'second',
        lpep_pickup_datetime,
        lpep_dropoff_datetime
    )) AS max_duration_seconds
FROM read_parquet(
    'data/raw/green/*/*.parquet',
    union_by_name = true,
    filename = true
)
GROUP BY year
ORDER BY year;
```

Aparecen los mismos tipos de problemas, pero en menor cantidad. Por ejemplo, hay 34,574, 24,438 y 12,212 viajes con
distancia cero en 2024, 2025 y 2026. Se decidió aplicar a green la misma regla de viaje válido que a yellow.
