-- @title Ingreso total (millones de USD, viajes validos)
-- @question P2. Cuanto dinero mueven los viajes de taxi en el periodo?
-- @display scalar
-- @layout 6,4,6,3
--
-- Indicador: suma de total_amount (tarifa, recargos, peajes y propina) en
-- millones de USD. Solo viajes validos, para no mezclar reembolsos (montos
-- negativos) ni errores de captura (montos de cientos de miles de USD).
-- Viaje valido: 0 < trip_distance < 100, 0 < fare_amount < 1000 y
-- 0 < duration_minutes < 1440 (ver docs/data_quality.md).
SELECT round(sum(total_amount) / 1e6, 1)::DOUBLE AS ingreso_millones_usd
FROM trips
WHERE trip_distance > 0 AND trip_distance < 100
  AND fare_amount > 0 AND fare_amount < 1000
  AND duration_minutes > 0 AND duration_minutes < 1440;
