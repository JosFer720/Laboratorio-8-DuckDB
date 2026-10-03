-- @title Total de viajes
-- @question P1. Cual es el volumen total de viajes registrado en el periodo descargado?
-- @display scalar
-- @layout 0,4,6,3
--
-- Indicador: numero de viajes (todas las filas de trips, incluidas las que
-- no pasan la regla de viaje valido) para todos los anios y tipos de taxi.
-- Es el tamano del conjunto de datos y la base de los demas indicadores.
SELECT count(*)::BIGINT AS viajes
FROM trips;
