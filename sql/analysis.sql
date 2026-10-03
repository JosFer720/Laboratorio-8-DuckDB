-- Analisis exploratorio de los viajes de taxi de Nueva York.
--
-- Requisito: haber ejecutado scripts/create_database.py, que crea la tabla
-- `trips` en data/processed/taxi.duckdb. Ejecucion:
--   python scripts/run_sql.py sql/analysis.sql --db data/processed/taxi.duckdb
--
-- Columnas de `trips`: taxi_type, year, month (del nombre del archivo),
-- vendor_id, pickup_datetime, dropoff_datetime, passenger_count,
-- trip_distance, pu_location_id, do_location_id, payment_type, fare_amount,
-- tip_amount, tolls_amount, total_amount, duration_minutes.
--
-- Definicion de "viaje valido" (se usa donde se calculan promedios):
--   0 < trip_distance < 100 millas, 0 < fare_amount < 1000 USD y
--   0 < duration_minutes < 1440 (menos de 24 horas).
-- Se justifica con docs/data_quality.md: los extremos (distancias de cientos
-- de miles de millas, tarifas negativas, duraciones negativas) son errores de
-- captura, reembolsos o cancelaciones que distorsionan cualquier promedio.
--
-- Comparabilidad entre anios: 2024 y 2025 tienen 12 meses y 2026 solo los
-- meses que la TLC ya publico. Las comparaciones anuales se limitan a los
-- "meses comunes": los meses presentes en TODOS los anios descargados, que se
-- calculan a partir de los datos (no con un mes fijo), o se expresan como
-- proporciones, para no comparar un anio completo contra uno parcial. Asi las
-- consultas siguen siendo validas cuando la TLC publica meses nuevos o se
-- agrega otro anio. Las consultas sin esta restriccion lo indican.

-- ===========================================================================
-- P1. Cuantos viajes se realizan por mes?
-- ===========================================================================
-- Objetivo: ver estacionalidad y tendencia. Fuente: trips (todos los viajes).
SELECT
    taxi_type,
    year,
    month,
    count(*) AS viajes
FROM trips
GROUP BY taxi_type, year, month
ORDER BY taxi_type, year, month;

-- Comparacion anual homogenea (solo los meses comunes a todos los anios),
-- con el cambio porcentual respecto del anio anterior.
WITH meses_comunes AS (
    SELECT month
    FROM trips
    GROUP BY month
    HAVING count(DISTINCT year) = (SELECT count(DISTINCT year) FROM trips)
)
SELECT
    taxi_type,
    year,
    min(month) AS mes_inicial,
    max(month) AS mes_final,
    count(*) AS viajes_meses_comunes,
    round(100.0 * (count(*) / lag(count(*)) OVER (PARTITION BY taxi_type ORDER BY year) - 1), 1)
        AS cambio_vs_anio_anterior_pct
FROM trips
WHERE month IN (SELECT month FROM meses_comunes)
GROUP BY taxi_type, year
ORDER BY taxi_type, year;

-- ===========================================================================
-- P2. Cual es la distancia promedio? P3. Cual es la tarifa promedio?
-- ===========================================================================
-- Objetivo: caracterizar el viaje tipico. Solo viajes validos.
SELECT
    taxi_type,
    year,
    count(*) AS viajes_validos,
    round(avg(trip_distance), 2) AS distancia_promedio_millas,
    round(median(trip_distance), 2) AS distancia_mediana_millas,
    round(avg(fare_amount), 2) AS tarifa_promedio_usd,
    round(median(fare_amount), 2) AS tarifa_mediana_usd,
    round(avg(total_amount), 2) AS monto_total_promedio_usd,
    round(avg(duration_minutes), 1) AS duracion_promedio_min
FROM trips
WHERE trip_distance > 0 AND trip_distance < 100
  AND fare_amount > 0 AND fare_amount < 1000
  AND duration_minutes > 0 AND duration_minutes < 1440
GROUP BY taxi_type, year
ORDER BY taxi_type, year;

-- ===========================================================================
-- P4. Que diferencias existen entre taxis amarillos y verdes?
-- ===========================================================================
-- Objetivo: comparar volumen, tamano del viaje, propina y ocupacion.
SELECT
    taxi_type,
    count(*) AS viajes_validos,
    round(avg(trip_distance), 2) AS distancia_promedio,
    round(avg(fare_amount), 2) AS tarifa_promedio,
    round(avg(tip_amount), 2) AS propina_promedio,
    round(100 * sum(tip_amount) / sum(fare_amount), 2) AS propina_pct_de_tarifa,
    round(avg(duration_minutes), 1) AS duracion_promedio_min,
    round(avg(passenger_count), 2) AS pasajeros_promedio,
    round(avg(trip_distance / (duration_minutes / 60.0)), 1) AS velocidad_promedio_mph
FROM trips
WHERE trip_distance > 0 AND trip_distance < 100
  AND fare_amount > 0 AND fare_amount < 1000
  AND duration_minutes > 0 AND duration_minutes < 1440
GROUP BY taxi_type
ORDER BY taxi_type;

-- Zonas de origen mas frecuentes por tipo de taxi (ids de zona TLC).
SELECT taxi_type, pu_location_id, viajes
FROM (
    SELECT
        taxi_type,
        pu_location_id,
        count(*) AS viajes,
        row_number() OVER (PARTITION BY taxi_type ORDER BY count(*) DESC) AS posicion
    FROM trips
    GROUP BY taxi_type, pu_location_id
)
WHERE posicion <= 5
ORDER BY taxi_type, posicion;

-- ===========================================================================
-- P5. Como varia la actividad por hora y por dia de la semana?
-- ===========================================================================
-- Objetivo: identificar horas pico. Se usa la fecha de recogida y se excluyen
-- los viajes con fechas fuera del anio del archivo (errores de reloj).
-- Se expresa como porcentaje del total del tipo de taxi.
SELECT
    taxi_type,
    hour(pickup_datetime) AS hora,
    count(*) AS viajes,
    round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY taxi_type), 2) AS pct_del_tipo
FROM trips
WHERE year(pickup_datetime) = year
GROUP BY taxi_type, hora
ORDER BY taxi_type, hora;

-- Dia de la semana (0 = domingo ... 6 = sabado).
SELECT
    taxi_type,
    dayofweek(pickup_datetime) AS dia_semana,
    count(*) AS viajes,
    round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY taxi_type), 2) AS pct_del_tipo
FROM trips
WHERE year(pickup_datetime) = year
GROUP BY taxi_type, dia_semana
ORDER BY taxi_type, dia_semana;

-- ===========================================================================
-- P6. Que formas de pago se utilizan mas?
-- ===========================================================================
-- payment_type: 0 = tarifa flexible / no registrada, 1 = tarjeta, 2 = efectivo,
-- 3 = sin cargo, 4 = disputa, 5 = desconocido, NULL = no reportado.
-- Objetivo: ver la mezcla de pagos y su evolucion entre anios (todos los meses).
SELECT
    taxi_type,
    year,
    payment_type,
    count(*) AS viajes,
    round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY taxi_type, year), 2) AS pct,
    round(avg(tip_amount), 2) AS propina_promedio
FROM trips
GROUP BY taxi_type, year, payment_type
ORDER BY taxi_type, year, viajes DESC;

-- ===========================================================================
-- P7. Que valores atipicos aparecen?
-- ===========================================================================
-- Objetivo: cuantificar errores por anio. Los conteos no eliminan filas.
SELECT
    taxi_type,
    year,
    count(*) AS viajes,
    count_if(trip_distance = 0) AS distancia_cero,
    count_if(trip_distance > 100) AS distancia_mayor_100,
    count_if(fare_amount < 0) AS tarifa_negativa,
    count_if(total_amount < 0) AS monto_negativo,
    count_if(total_amount > 1000) AS monto_mayor_1000,
    count_if(duration_minutes <= 0) AS duracion_no_positiva,
    count_if(duration_minutes > 1440) AS duracion_mayor_24h,
    count_if(year(pickup_datetime) <> year) AS fecha_fuera_del_anio,
    round(100.0 * count_if(
        trip_distance = 0 OR fare_amount <= 0 OR duration_minutes <= 0
        OR trip_distance >= 100 OR fare_amount >= 1000 OR duration_minutes >= 1440
    ) / count(*), 2) AS pct_excluido_como_invalido
FROM trips
GROUP BY taxi_type, year
ORDER BY taxi_type, year;

-- Distribucion de la tarifa de viajes validos: la cola larga explica por que
-- la mediana y el promedio difieren.
-- Los percentiles se piden en UNA llamada con una lista: cada quantile_cont
-- guarda en memoria todos los valores de su grupo, y seis llamadas separadas
-- (la version original) necesitaban seis copias. Con 2024+2026 (72 M de filas)
-- cabia en memoria; al agregar 2025 (121 M) el proceso se quedaba sin memoria
-- en un contenedor de 8 GB.
WITH percentiles AS (
    SELECT
        taxi_type,
        quantile_cont(fare_amount, [0.05, 0.25, 0.50, 0.75, 0.95, 0.99]) AS p
    FROM trips
    WHERE fare_amount > 0 AND fare_amount < 1000
    GROUP BY taxi_type
)
SELECT
    taxi_type,
    round(p[1], 2) AS p05,
    round(p[2], 2) AS p25,
    round(p[3], 2) AS p50,
    round(p[4], 2) AS p75,
    round(p[5], 2) AS p95,
    round(p[6], 2) AS p99
FROM percentiles
ORDER BY taxi_type;

-- Duraciones no positivas en yellow por mes: localiza cuando aparecen.
SELECT
    year,
    month,
    count(*) AS viajes,
    count_if(duration_minutes <= 0) AS duracion_no_positiva,
    round(100.0 * count_if(duration_minutes <= 0) / count(*), 2) AS pct
FROM trips
WHERE taxi_type = 'yellow'
GROUP BY year, month
ORDER BY year, month;

-- Origen del salto: duraciones no positivas por anio y proveedor (vendor_id).
-- Un proveedor (7, que aparece a fines de 2024) concentra casi todos los casos
-- de 2025 y 2026, por lo que es un problema de captura de ese proveedor y no un
-- cambio real en los viajes.
SELECT
    year,
    vendor_id,
    count(*) AS viajes,
    count_if(duration_minutes <= 0) AS duracion_no_positiva,
    round(100.0 * count_if(duration_minutes <= 0) / count(*), 2) AS pct
FROM trips
WHERE taxi_type = 'yellow'
GROUP BY year, vendor_id
ORDER BY year, vendor_id;

-- ===========================================================================
-- P8. Hallazgos de comparacion entre anios (meses comunes)
-- ===========================================================================
-- Propina y tarifa de viajes con tarjeta, para separar el efecto de la mezcla
-- de formas de pago del efecto del precio.
SELECT
    taxi_type,
    year,
    round(avg(fare_amount), 2) AS tarifa_promedio,
    round(avg(tip_amount) FILTER (WHERE payment_type = 1), 2) AS propina_promedio_tarjeta,
    round(avg(tip_amount), 2) AS propina_promedio_todos,
    round(100.0 * count_if(payment_type = 1) / count(*), 2) AS pct_tarjeta,
    round(100.0 * count_if(payment_type = 0 OR payment_type IS NULL) / count(*), 2)
        AS pct_pago_no_registrado
FROM trips
WHERE month IN (
        SELECT month FROM trips GROUP BY month
        HAVING count(DISTINCT year) = (SELECT count(DISTINCT year) FROM trips)
    )
  AND trip_distance > 0 AND trip_distance < 100
  AND fare_amount > 0 AND fare_amount < 1000
  AND duration_minutes > 0 AND duration_minutes < 1440
GROUP BY taxi_type, year
ORDER BY taxi_type, year;
