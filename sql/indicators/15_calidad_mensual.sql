-- @title Calidad de datos: viajes invalidos por mes (%)
-- @question P15. La calidad de los registros es estable en el tiempo o cambia con los proveedores?
-- @display line
-- @x periodo
-- @series tipo
-- @y pct_invalidos
-- @colors yellow=#eda100,green=#008300
-- @layout 0,46,24,5
--
-- Indicador: porcentaje mensual de viajes que no pasan la regla de viaje
-- valido. Un salto en la serie senala un cambio en la captura (por ejemplo un
-- proveedor nuevo) y no un cambio real en los viajes.
SELECT
    make_date(year, month, 1) AS periodo,
    taxi_type AS tipo,
    round(100.0 * count_if(NOT (
        trip_distance > 0 AND trip_distance < 100
        AND fare_amount > 0 AND fare_amount < 1000
        AND duration_minutes > 0 AND duration_minutes < 1440
    )) / count(*), 2)::DOUBLE AS pct_invalidos
FROM trips
GROUP BY periodo, tipo
ORDER BY periodo, tipo;
