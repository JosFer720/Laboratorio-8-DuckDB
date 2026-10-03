-- @title Comparacion anual (meses comunes a todos los anios)
-- @question P7. Como cambian volumen, precio, distancia, duracion y propina de un anio a otro?
-- @display table
-- @layout 0,13,24,7
--
-- Indicador: tabla resumen por tipo de taxi y anio. Para que la comparacion
-- sea justa solo se consideran los meses publicados en TODOS los anios
-- descargados (el anio en curso esta incompleto); el conjunto de meses se
-- calcula a partir de los datos, por lo que la consulta no cambia cuando la
-- TLC publica meses nuevos. Los promedios usan solo viajes validos; el
-- volumen y el cambio porcentual usan todos los viajes.
WITH meses_comunes AS (
    SELECT taxi_type, month
    FROM trips
    GROUP BY taxi_type, month
    HAVING count(DISTINCT year) = (SELECT count(DISTINCT year) FROM trips)
),
base AS (
    SELECT t.*
    FROM trips t
    JOIN meses_comunes m USING (taxi_type, month)
),
resumen AS (
    SELECT
        taxi_type,
        year,
        min(month) AS mes_inicial,
        max(month) AS mes_final,
        count(*) AS viajes,
        avg(fare_amount) FILTER (WHERE trip_distance > 0 AND trip_distance < 100
            AND fare_amount > 0 AND fare_amount < 1000
            AND duration_minutes > 0 AND duration_minutes < 1440) AS tarifa,
        avg(trip_distance) FILTER (WHERE trip_distance > 0 AND trip_distance < 100
            AND fare_amount > 0 AND fare_amount < 1000
            AND duration_minutes > 0 AND duration_minutes < 1440) AS distancia,
        avg(duration_minutes) FILTER (WHERE trip_distance > 0 AND trip_distance < 100
            AND fare_amount > 0 AND fare_amount < 1000
            AND duration_minutes > 0 AND duration_minutes < 1440) AS duracion,
        100 * sum(tip_amount) FILTER (WHERE payment_type = 1 AND fare_amount > 0
            AND fare_amount < 1000)
            / sum(fare_amount) FILTER (WHERE payment_type = 1 AND fare_amount > 0
            AND fare_amount < 1000) AS propina_pct_tarjeta
    FROM base
    GROUP BY taxi_type, year
)
SELECT
    taxi_type AS tipo,
    year::VARCHAR AS anio,
    mes_inicial || '-' || mes_final AS meses,
    viajes::BIGINT AS viajes,
    round(100.0 * (viajes / lag(viajes) OVER (PARTITION BY taxi_type ORDER BY year) - 1), 1)::DOUBLE
        AS cambio_viajes_pct,
    round(tarifa, 2)::DOUBLE AS tarifa_promedio_usd,
    round(distancia, 2)::DOUBLE AS distancia_promedio_millas,
    round(duracion, 1)::DOUBLE AS duracion_promedio_min,
    round(propina_pct_tarjeta, 1)::DOUBLE AS propina_pct_tarifa_tarjeta
FROM resumen
ORDER BY tipo DESC, anio;
