-- Materializacion de los viajes de taxi en una tabla DuckDB.
--
-- scripts/create_database.py ejecuta esta sentencia sobre data/processed/taxi.duckdb
-- y scripts/benchmark.py reutiliza el mismo SELECT como vista sobre los Parquet,
-- de modo que ambas estrategias ven exactamente las mismas columnas.
-- Los marcadores $yellow_files y $green_files se sustituyen por las rutas
-- glob de los archivos Parquet; agregar un anio nuevo no requiere editar este
-- archivo, solo descargar sus Parquet.
--
-- Transformaciones aplicadas (no se elimina ninguna fila):
--   * se unifican yellow y green en una sola tabla con la columna taxi_type;
--   * se renombran las marcas de tiempo (tpep_* / lpep_*) a pickup_datetime y
--     dropoff_datetime, y los identificadores a snake_case;
--   * year y month se toman del nombre del archivo (<tipo>_tripdata_AAAA-MM),
--     no de la fecha del viaje, porque hay viajes con fechas fuera de su mes
--     de publicacion;
--   * se fijan los tipos de las columnas, que varian entre meses y anios;
--   * duration_minutes se calcula a partir de las marcas de tiempo.
-- Los valores atipicos o invalidos (distancias cero, montos negativos,
-- duraciones negativas) se conservan para poder analizarlos; las consultas de
-- analisis son las que deciden cuando excluirlos.

CREATE TABLE trips AS
SELECT
    'yellow' AS taxi_type,
    regexp_extract(filename, 'tripdata_(\d{4})-(\d{2})', 1)::SMALLINT AS year,
    regexp_extract(filename, 'tripdata_(\d{4})-(\d{2})', 2)::SMALLINT AS month,
    VendorID::INTEGER AS vendor_id,
    tpep_pickup_datetime AS pickup_datetime,
    tpep_dropoff_datetime AS dropoff_datetime,
    passenger_count::INTEGER AS passenger_count,
    trip_distance::DOUBLE AS trip_distance,
    PULocationID::INTEGER AS pu_location_id,
    DOLocationID::INTEGER AS do_location_id,
    payment_type::INTEGER AS payment_type,
    fare_amount::DOUBLE AS fare_amount,
    tip_amount::DOUBLE AS tip_amount,
    tolls_amount::DOUBLE AS tolls_amount,
    total_amount::DOUBLE AS total_amount,
    date_diff('second', tpep_pickup_datetime, tpep_dropoff_datetime) / 60.0
        AS duration_minutes
FROM read_parquet($yellow_files, union_by_name = true, filename = true)

UNION ALL

SELECT
    'green' AS taxi_type,
    regexp_extract(filename, 'tripdata_(\d{4})-(\d{2})', 1)::SMALLINT AS year,
    regexp_extract(filename, 'tripdata_(\d{4})-(\d{2})', 2)::SMALLINT AS month,
    VendorID::INTEGER AS vendor_id,
    lpep_pickup_datetime AS pickup_datetime,
    lpep_dropoff_datetime AS dropoff_datetime,
    passenger_count::INTEGER AS passenger_count,
    trip_distance::DOUBLE AS trip_distance,
    PULocationID::INTEGER AS pu_location_id,
    DOLocationID::INTEGER AS do_location_id,
    payment_type::INTEGER AS payment_type,
    fare_amount::DOUBLE AS fare_amount,
    tip_amount::DOUBLE AS tip_amount,
    tolls_amount::DOUBLE AS tolls_amount,
    total_amount::DOUBLE AS total_amount,
    date_diff('second', lpep_pickup_datetime, lpep_dropoff_datetime) / 60.0
        AS duration_minutes
FROM read_parquet($green_files, union_by_name = true, filename = true);
