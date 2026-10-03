-- Exploracion inicial de los viajes de taxi de 2026.
-- Ejecute este archivo desde la raiz del proyecto despues de descargar los
-- datos. Las rutas son relativas a esa ubicacion.
--
-- union_by_name permite leer conjuntamente meses cuya lista u orden de
-- columnas haya cambiado. Yellow y Green se consultan por separado porque
-- usan nombres distintos para las marcas de tiempo.

-- ---------------------------------------------------------------------------
-- 1. Archivos disponibles
-- ---------------------------------------------------------------------------
-- glob() permite revisar la descarga sin abrir los archivos Parquet.
SELECT
    'yellow' AS taxi_type,
    count(*) AS file_count
FROM glob('data/raw/yellow/2026/*.parquet')

UNION ALL

SELECT
    'green' AS taxi_type,
    count(*) AS file_count
FROM glob('data/raw/green/2026/*.parquet')
ORDER BY taxi_type;

-- ---------------------------------------------------------------------------
-- 2. Cantidad de registros
-- ---------------------------------------------------------------------------
SELECT
    'yellow' AS taxi_type,
    count(*) AS record_count
FROM read_parquet(
    'data/raw/yellow/2026/*.parquet',
    union_by_name = true
)

UNION ALL

SELECT
    'green' AS taxi_type,
    count(*) AS record_count
FROM read_parquet(
    'data/raw/green/2026/*.parquet',
    union_by_name = true
)
ORDER BY taxi_type;

-- El desglose por archivo ayuda a detectar meses vacios o incompletos.
SELECT
    filename,
    count(*) AS record_count
FROM read_parquet(
    'data/raw/yellow/2026/*.parquet',
    filename = true,
    union_by_name = true
)
GROUP BY filename
ORDER BY filename;

SELECT
    filename,
    count(*) AS record_count
FROM read_parquet(
    'data/raw/green/2026/*.parquet',
    filename = true,
    union_by_name = true
)
GROUP BY filename
ORDER BY filename;

-- ---------------------------------------------------------------------------
-- 3. Columnas y tipos inferidos desde los Parquet
-- ---------------------------------------------------------------------------
DESCRIBE SELECT *
FROM read_parquet(
    'data/raw/yellow/2026/*.parquet',
    union_by_name = true
);

DESCRIBE SELECT *
FROM read_parquet(
    'data/raw/green/2026/*.parquet',
    union_by_name = true
);

-- ---------------------------------------------------------------------------
-- 4. Muestras de registros
-- ---------------------------------------------------------------------------
SELECT *
FROM read_parquet(
    'data/raw/yellow/2026/*.parquet',
    union_by_name = true
)
LIMIT 10;

SELECT *
FROM read_parquet(
    'data/raw/green/2026/*.parquet',
    union_by_name = true
)
LIMIT 10;

-- ---------------------------------------------------------------------------
-- 5. Calidad inicial: Yellow Taxi
-- ---------------------------------------------------------------------------
-- Los umbrales de atipicos son reglas de revision, no filtros definitivos.
-- Se reportan conteos para no perder filas durante esta exploracion inicial.
SELECT
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
    'data/raw/yellow/2026/*.parquet',
    union_by_name = true
);

-- Rangos observados para contextualizar los conteos anteriores.
SELECT
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
    'data/raw/yellow/2026/*.parquet',
    union_by_name = true
);

-- ---------------------------------------------------------------------------
-- 6. Calidad inicial: Green Taxi
-- ---------------------------------------------------------------------------
SELECT
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
    'data/raw/green/2026/*.parquet',
    union_by_name = true
);

SELECT
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
    'data/raw/green/2026/*.parquet',
    union_by_name = true
);
