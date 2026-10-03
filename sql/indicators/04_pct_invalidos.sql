-- @title Viajes que no pasan la regla de viaje valido (%)
-- @question P4. Que proporcion de los registros no es confiable para calcular promedios?
-- @display scalar
-- @layout 18,4,6,3
--
-- Indicador de calidad: porcentaje de viajes con distancia, tarifa o
-- duracion fuera de la regla de viaje valido. Indica cuanto filtran los
-- indicadores que calculan promedios.
SELECT round(100.0 * count_if(NOT (
           trip_distance > 0 AND trip_distance < 100
           AND fare_amount > 0 AND fare_amount < 1000
           AND duration_minutes > 0 AND duration_minutes < 1440
       )) / count(*), 2)::DOUBLE AS pct_invalidos
FROM trips;
