-- @title Velocidad promedio en Manhattan por hora (mph, yellow)
-- @question P11. Cambio la velocidad de los viajes dentro de Manhattan entre anios (congestion)?
-- @display line
-- @x hora
-- @series anio
-- @y velocidad_mph
-- @colors 2024=#2a78d6,2025=#eb6834,2026=#1baf7a
-- @layout 12,26,12,6
--
-- Indicador: velocidad media (distancia / duracion) de los viajes yellow
-- validos que empiezan y terminan en Manhattan, por hora de recogida y anio.
-- Es una medida indirecta de congestion: desde el 5 de enero de 2025 Nueva
-- York cobra un peaje de congestion para entrar al sur de Manhattan.
-- Requiere la tabla zones (catalogo de zonas de la TLC).
SELECT
    hour(t.pickup_datetime) AS hora,
    t.year::VARCHAR AS anio,
    round(avg(t.trip_distance / (t.duration_minutes / 60.0)), 2)::DOUBLE AS velocidad_mph
FROM trips t
JOIN zones zo ON zo.location_id = t.pu_location_id
JOIN zones zd ON zd.location_id = t.do_location_id
WHERE t.taxi_type = 'yellow'
  AND zo.borough = 'Manhattan' AND zd.borough = 'Manhattan'
  AND year(t.pickup_datetime) = t.year
  AND t.trip_distance > 0 AND t.trip_distance < 100
  AND t.fare_amount > 0 AND t.fare_amount < 1000
  AND t.duration_minutes > 1 AND t.duration_minutes < 1440
GROUP BY hora, anio
ORDER BY hora, anio;
