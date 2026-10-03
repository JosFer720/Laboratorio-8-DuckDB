-- @title Viajes por mes - Yellow (miles)
-- @question P5. Como evoluciona la demanda mensual de taxis amarillos y como se compara entre anios?
-- @display line
-- @x mes
-- @series anio
-- @y viajes_miles
-- @colors 2024=#2a78d6,2025=#eb6834,2026=#1baf7a
-- @layout 0,7,12,6
--
-- Indicador: viajes por mes, una linea por anio sobre el mismo eje de meses,
-- para comparar estacionalidad y crecimiento. Se grafica yellow y green por
-- separado porque green es ~1 % del volumen de yellow: en un mismo eje la
-- linea green quedaria plana.
SELECT
    month AS mes,
    year::VARCHAR AS anio,
    round(count(*) / 1000.0, 1)::DOUBLE AS viajes_miles
FROM trips
WHERE taxi_type = 'yellow'
GROUP BY month, year
ORDER BY mes, anio;
