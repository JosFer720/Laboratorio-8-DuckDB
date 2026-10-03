-- @title Monto promedio por viaje (USD, viajes validos)
-- @question P3. Cuanto paga en promedio un pasajero por viaje?
-- @display scalar
-- @layout 12,4,6,3
--
-- Indicador: promedio de total_amount por viaje valido. Resume el precio que
-- enfrenta el pasajero (incluye recargos y propina, no solo la tarifa).
SELECT round(avg(total_amount), 2)::DOUBLE AS monto_promedio_usd
FROM trips
WHERE trip_distance > 0 AND trip_distance < 100
  AND fare_amount > 0 AND fare_amount < 1000
  AND duration_minutes > 0 AND duration_minutes < 1440;
