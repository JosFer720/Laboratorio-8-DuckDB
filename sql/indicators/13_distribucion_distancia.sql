-- @title Distribucion de la distancia del viaje (% de viajes validos)
-- @question P13. Que tan largos son los viajes de cada servicio?
-- @display bar
-- @x rango_millas
-- @series tipo
-- @y pct_viajes
-- @colors yellow=#eda100,green=#008300
-- @layout 12,32,12,6
--
-- Indicador: histograma de distancias en rangos de millas, como porcentaje de
-- los viajes validos de cada tipo. Muestra la forma de la distribucion (cola
-- larga), que el promedio oculta. El prefijo numerico mantiene el orden.
SELECT
    CASE
        WHEN trip_distance < 1 THEN '1. 0-1'
        WHEN trip_distance < 2 THEN '2. 1-2'
        WHEN trip_distance < 3 THEN '3. 2-3'
        WHEN trip_distance < 5 THEN '4. 3-5'
        WHEN trip_distance < 10 THEN '5. 5-10'
        WHEN trip_distance < 20 THEN '6. 10-20'
        ELSE '7. 20+'
    END AS rango_millas,
    taxi_type AS tipo,
    round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY taxi_type), 2)::DOUBLE AS pct_viajes
FROM trips
WHERE trip_distance > 0 AND trip_distance < 100
  AND fare_amount > 0 AND fare_amount < 1000
  AND duration_minutes > 0 AND duration_minutes < 1440
GROUP BY rango_millas, tipo
ORDER BY rango_millas, tipo DESC;
