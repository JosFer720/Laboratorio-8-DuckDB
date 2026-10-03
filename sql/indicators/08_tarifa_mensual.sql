-- @title Tarifa promedio por mes (USD, viajes validos)
-- @question P8. Como evoluciona el precio del viaje en el tiempo?
-- @display line
-- @x periodo
-- @series tipo
-- @y tarifa_promedio_usd
-- @colors yellow=#eda100,green=#008300
-- @layout 0,20,12,6
--
-- Indicador: fare_amount promedio por mes (sin propina ni recargos), serie
-- continua de los tres anios. Ambos tipos comparten la escala en USD.
SELECT
    make_date(year, month, 1) AS periodo,
    taxi_type AS tipo,
    round(avg(fare_amount), 2)::DOUBLE AS tarifa_promedio_usd
FROM trips
WHERE trip_distance > 0 AND trip_distance < 100
  AND fare_amount > 0 AND fare_amount < 1000
  AND duration_minutes > 0 AND duration_minutes < 1440
GROUP BY periodo, tipo
ORDER BY periodo, tipo;
