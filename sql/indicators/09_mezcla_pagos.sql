-- @title Formas de pago por anio (% de los viajes)
-- @question P9. Que formas de pago predominan y como cambia la mezcla entre anios?
-- @display bar
-- @x grupo
-- @series forma_pago
-- @y pct
-- @stack normalized
-- @colors Tarjeta=#2a78d6,Efectivo=#eb6834,Flexible / no registrado=#1baf7a,Otro=#eda100
-- @layout 12,20,12,6
--
-- Indicador: participacion de cada forma de pago por tipo de taxi y anio.
-- payment_type: 1 tarjeta, 2 efectivo, 0 tarifa flexible / no registrada,
-- NULL no reportado (se agrupa con 0), 3 sin cargo, 4 disputa, 5 desconocido
-- (3-5 se agrupan como "Otro").
SELECT
    taxi_type || ' ' || year AS grupo,
    CASE
        WHEN payment_type = 1 THEN 'Tarjeta'
        WHEN payment_type = 2 THEN 'Efectivo'
        WHEN payment_type = 0 OR payment_type IS NULL THEN 'Flexible / no registrado'
        ELSE 'Otro'
    END AS forma_pago,
    round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY taxi_type, year), 2)::DOUBLE AS pct
FROM trips
GROUP BY taxi_type, year, forma_pago
ORDER BY taxi_type DESC, year, forma_pago;
