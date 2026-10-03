-- @title Propina como % de la tarifa (pagos con tarjeta)
-- @question P12. Cambia la generosidad de los pasajeros entre anios y servicios?
-- @display bar
-- @x anio
-- @series tipo
-- @y propina_pct_tarifa
-- @colors yellow=#eda100,green=#008300
-- @layout 0,32,12,6
--
-- Indicador: propina total / tarifa total de los viajes pagados con tarjeta.
-- Se limita a tarjeta porque las propinas en efectivo no se registran: usar
-- todos los viajes mezclaria el cambio en las formas de pago con el
-- comportamiento de propina.
SELECT
    year::VARCHAR AS anio,
    taxi_type AS tipo,
    round(100 * sum(tip_amount) / sum(fare_amount), 2)::DOUBLE AS propina_pct_tarifa
FROM trips
WHERE payment_type = 1
  AND fare_amount > 0 AND fare_amount < 1000
  AND tip_amount >= 0
GROUP BY anio, tipo
ORDER BY anio, tipo DESC;
