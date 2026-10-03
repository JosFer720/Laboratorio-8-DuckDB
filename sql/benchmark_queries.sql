-- Consultas del benchmark Parquet vs tabla DuckDB.
--
-- scripts/benchmark.py ejecuta cada consulta dos veces con el mismo texto:
--   * contra una vista `trips` definida sobre los archivos Parquet
--     (el mismo SELECT de sql/create_tables.sql), y
--   * contra la tabla materializada `trips` de la base DuckDB.
-- Por eso todas las consultas leen unicamente de `trips`.
--
-- Cada consulta empieza con una linea "-- @query <id> | <descripcion>".
-- Los valores decimales se redondean para que los resultados de ambas
-- estrategias puedan compararse (la suma en paralelo de dobles puede variar en
-- las ultimas cifras). Cubren los tipos de operacion mas comunes del analisis:
-- conteo, agregacion por grupos, filtros, extraccion de fechas, percentiles y
-- consultas selectivas.

-- @query q1_conteo | Conteo total de viajes (recorre una sola columna de metadatos)
SELECT count(*) AS viajes
FROM trips;

-- @query q2_viajes_por_mes | Viajes por tipo de taxi, anio y mes
SELECT taxi_type, year, month, count(*) AS viajes
FROM trips
GROUP BY taxi_type, year, month
ORDER BY taxi_type, year, month;

-- @query q3_promedios | Distancia, tarifa y propina promedio por tipo de taxi (viajes validos)
SELECT
    taxi_type,
    round(avg(trip_distance), 4) AS distancia_promedio,
    round(avg(fare_amount), 4) AS tarifa_promedio,
    round(avg(tip_amount), 4) AS propina_promedio
FROM trips
WHERE trip_distance > 0 AND trip_distance < 100
  AND fare_amount > 0 AND fare_amount < 1000
GROUP BY taxi_type
ORDER BY taxi_type;

-- @query q4_actividad_por_hora | Viajes e ingreso total por hora del dia
SELECT
    hour(pickup_datetime) AS hora,
    count(*) AS viajes,
    round(sum(total_amount), 2) AS ingreso_total
FROM trips
GROUP BY hora
ORDER BY hora;

-- @query q5_formas_de_pago | Viajes y propina promedio por forma de pago
SELECT
    payment_type,
    count(*) AS viajes,
    round(avg(tip_amount), 4) AS propina_promedio
FROM trips
GROUP BY payment_type
ORDER BY viajes DESC, payment_type;

-- @query q6_zonas_origen | Las 10 zonas de origen con mas viajes
SELECT pu_location_id, count(*) AS viajes, round(avg(total_amount), 4) AS monto_promedio
FROM trips
GROUP BY pu_location_id
ORDER BY viajes DESC, pu_location_id
LIMIT 10;

-- @query q7_percentiles | Percentiles de la tarifa por tipo de taxi (viajes validos)
SELECT
    taxi_type,
    quantile_cont(fare_amount, 0.5) AS mediana,
    quantile_cont(fare_amount, 0.95) AS p95,
    quantile_cont(fare_amount, 0.99) AS p99
FROM trips
WHERE fare_amount > 0 AND fare_amount < 1000
GROUP BY taxi_type
ORDER BY taxi_type;

-- @query q8_atipicos | Viajes atipicos: distancia > 100 millas o duracion invalida
SELECT
    taxi_type,
    count_if(trip_distance > 100) AS distancia_mayor_100,
    count_if(duration_minutes <= 0) AS duracion_invalida,
    count_if(total_amount < 0) AS monto_negativo
FROM trips
GROUP BY taxi_type
ORDER BY taxi_type;

-- @query q9_consulta_selectiva | Viajes yellow de enero con pago en efectivo y mas de 20 millas
SELECT count(*) AS viajes, round(avg(total_amount), 4) AS monto_promedio
FROM trips
WHERE taxi_type = 'yellow'
  AND month = 1
  AND payment_type = 2
  AND trip_distance > 20 AND trip_distance < 100;
