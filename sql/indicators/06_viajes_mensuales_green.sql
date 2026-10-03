-- @title Viajes por mes - Green (miles)
-- @question P6. Como evoluciona la demanda mensual de taxis verdes y como se compara entre anios?
-- @display line
-- @x mes
-- @series anio
-- @y viajes_miles
-- @colors 2024=#2a78d6,2025=#eb6834,2026=#1baf7a
-- @layout 12,7,12,6
--
-- Indicador: igual que el anterior para green, en su propia escala.
SELECT
    month AS mes,
    year::VARCHAR AS anio,
    round(count(*) / 1000.0, 1)::DOUBLE AS viajes_miles
FROM trips
WHERE taxi_type = 'green'
GROUP BY month, year
ORDER BY mes, anio;
