-- @title Viajes por hora del dia (% de los viajes de cada tipo)
-- @question P10. En que horas se concentra la demanda de cada servicio?
-- @display line
-- @x hora
-- @series tipo
-- @y pct_viajes
-- @colors yellow=#eda100,green=#008300
-- @layout 0,26,12,6
--
-- Indicador: distribucion de los viajes por hora de recogida, como porcentaje
-- del total de cada tipo (asi se comparan dos servicios de tamanos muy
-- distintos en una sola escala). Se excluyen las fechas fuera del anio del
-- archivo (errores de reloj).
SELECT
    hour(pickup_datetime) AS hora,
    taxi_type AS tipo,
    round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY taxi_type), 2)::DOUBLE AS pct_viajes
FROM trips
WHERE year(pickup_datetime) = year
GROUP BY hora, tipo
ORDER BY hora, tipo;
