-- @title Zonas de recogida con mas viajes (miles, todos los anios)
-- @question P14. Donde se origina la demanda de taxis?
-- @display row
-- @x zona
-- @y viajes_miles
-- @layout 0,38,24,8
--
-- Indicador: las 10 zonas TLC con mas recogidas (yellow + green), con su
-- distrito. Requiere la tabla zones. La tarjeta ocupa todo el ancho y es alta
-- porque la grafica de filas de Metabase agrupa en "Other" las barras que no
-- caben en la altura disponible y recorta los nombres largos.
SELECT
    z.zone || ' (' || z.borough || ')' AS zona,
    round(count(*) / 1000.0, 1)::DOUBLE AS viajes_miles
FROM trips t
JOIN zones z ON z.location_id = t.pu_location_id
GROUP BY zona
ORDER BY viajes_miles DESC
LIMIT 10;
