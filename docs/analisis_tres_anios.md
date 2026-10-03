# Análisis conjunto de 2024, 2025 y 2026

Este documento junta lo que se ve cuando se miran los tres años al mismo tiempo.
El código, las gráficas y los resultados completos están en
[`notebooks/evolucion_2024_2026.ipynb`](../notebooks/evolucion_2024_2026.ipynb),
y los indicadores del tablero se explican en [`indicadores.md`](indicadores.md).

Los datos son 121.2 millones de viajes. 2024 y 2025 están completos, y de 2026
solo hay de enero a agosto, porque la TLC publica cada mes con algunas semanas de
retraso. Para que las comparaciones entre años sean justas, se usan solo los meses
que existen en los tres años (enero a agosto). Los promedios usan solo los viajes
válidos, que son los que tienen una distancia, una tarifa y una duración
razonables. La regla exacta está en [`data_quality.md`](data_quality.md).

## Cómo cambiaron los indicadores

| Indicador | 2024 | 2025 | 2026 | Consulta |
| --- | ---: | ---: | ---: | --- |
| Viajes yellow, enero a agosto (millones) | 26.39 | 31.56 | 29.70 | `sql/indicators/07_comparacion_anual.sql` |
| Cambio contra el año anterior, yellow | | +19.6 % | -5.9 % | la misma |
| Viajes green, enero a agosto (miles) | 443 | 398 | 337 | la misma |
| Cambio contra el año anterior, green | | -10.3 % | -15.3 % | la misma |
| Parte de green en el total de viajes | 1.58 % | 1.20 % | 1.12 % | notebook, sección 1 |
| Tarifa promedio yellow, enero a agosto (USD) | 19.54 | 19.58 | 21.30 | `07_comparacion_anual.sql` |
| Tarifa promedio green, enero a agosto (USD) | 17.88 | 18.02 | 17.16 | la misma |
| Distancia promedio green (millas) | 2.93 | 3.11 | 3.31 | la misma |
| Pago flexible o sin anotar, yellow | 9.9 % | 23.8 % | 26.0 % | `09_mezcla_pagos.sql` |
| Pago sin anotar, green | 3.7 % | 8.4 % | 14.5 % | la misma |
| Propina con tarjeta, yellow (% de la tarifa) | 21.9 % | 21.9 % | 21.5 % | `12_propina_tarjeta.sql` |
| Velocidad en Manhattan de 7 a 19 h, yellow (millas por hora) | 8.62 | 8.68 | 8.57 | `11_velocidad_manhattan.sql` |
| Viajes yellow que pagan el peaje de congestión | 0 % | 65 % a 73 % | 66 % a 77 % | notebook, sección 5 (directo sobre Parquet) |
| Viajes yellow inválidos | 3.6 % | 9.4 % | 5.0 % | `15_calidad_mensual.sql` |
| Viajes con duración cero de la empresa `vendor_id` 7 | 230 | 535,901 | 367,120 | notebook, sección 4 |

## Cambios y patrones que aparecen al ver los tres años juntos

### 1. Los viajes yellow llegaron a su punto más alto en 2025 y bajaron en 2026

En los meses comunes, los viajes yellow crecieron 19.6 % de 2024 a 2025 y luego
bajaron 5.9 % en 2026. Antes de tener 2025, al comparar solo 2024 con 2026, parecía
que yellow crecía de forma continua (12.6 %). El año del medio muestra otra
historia, con un máximo en 2025 y una caída después. Green, en cambio, pierde
viajes todos los años (10.3 % y 15.3 % menos), y su parte en el total baja de
1.58 % a 1.12 % de los viajes.

### 2. El precio de yellow subió de golpe en diciembre de 2025

La tarifa promedio de yellow estuvo casi igual en 2024 y 2025 (19.5 y 19.6 dólares
de enero a agosto) y subió a 21.3 dólares en 2026, o sea, 8.8 % más. Al mirar la
serie mes a mes se ve que el salto ocurre en diciembre de 2025. Ese mes la tarifa
mediana pasa de 14.2 a 17.0 dólares y el precio mediano por milla pasa de 7.2 a 7.7
dólares. Como también sube el precio por milla, el aumento no se debe a que los
viajes sean más largos. Puede ser un ajuste de tarifas, pero los datos no dicen la
causa. La caída de viajes yellow en 2026 ocurre al mismo tiempo que esta subida de
precio. Green no sube sus precios, y su tarifa promedio incluso baja aunque sus
viajes son cada vez más largos.

### 3. La forma de pagar cambió en 2025, pero la propina se mantuvo

La categoría de tarifa flexible o pago sin anotar pasó de 9.9 % a 23.8 % de los
viajes yellow en 2025 y siguió en 26.0 % en 2026. Green fue por el mismo camino,
pero más despacio. Aun así, la propina con tarjeta se quedó en cerca de 22 % de la
tarifa los tres años. Si se compararan las propinas sin separar la forma de pago,
parecería que la gente empezó a dejar menos propina, y eso sería una conclusión
falsa.

### 4. Los problemas en los datos tienen fecha de inicio y de fin

La empresa con `vendor_id` 7 anota todos sus viajes con duración cero, y empezó a
aparecer a finales de 2024 y a crecer en 2025. Con solo 2024 y 2026 parecía que el
problema había empezado en 2026. Por otro lado, la empresa con `vendor_id` 2 anotó
muchas tarifas negativas con un total positivo durante 2025, y eso dejó de pasar en
diciembre de 2025. Por estos dos casos, el porcentaje de viajes yellow inválidos
subió de 3.6 % a 9.4 % y después bajó a 5.0 %. Si la regla para limpiar los datos se
hubiera pensado mirando un solo año, no habría previsto ninguno de los dos.

### 5. El peaje de congestión aparece en los datos, pero no cambia la velocidad

La columna `cbd_congestion_fee`, que guarda el cobro del peaje para entrar al sur
de Manhattan, existe desde enero de 2025. Desde entonces, unos 7 de cada 10 viajes
yellow pagan ese cargo, que es de 0.75 dólares por viaje. Pero la velocidad
promedio de los taxis dentro de Manhattan durante el día no cambió, y se mantuvo en
unas 8.6 millas por hora los tres años.

## Consultas utilizadas

Además de los archivos de `sql/indicators/` que aparecen en la tabla, el notebook
usa estas consultas.

```sql
-- Parte de green en el total de viajes, por año
SELECT year, round(100.0 * count_if(taxi_type = 'green') / count(*), 2) AS pct_green
FROM trips GROUP BY year ORDER BY year;

-- Precio mediano por viaje y por milla, mes a mes (yellow, viajes válidos)
SELECT make_date(year, month, 1) AS periodo,
       round(median(fare_amount), 2) AS tarifa_mediana,
       round(median(fare_amount / trip_distance) FILTER (WHERE trip_distance >= 0.5), 2) AS usd_por_milla_mediana
FROM trips
WHERE taxi_type = 'yellow'
  AND trip_distance > 0 AND trip_distance < 100 AND fare_amount > 0 AND fare_amount < 1000
  AND duration_minutes > 0 AND duration_minutes < 1440
GROUP BY periodo ORDER BY periodo;

-- Problemas de captura por mes (yellow)
SELECT make_date(year, month, 1) AS periodo,
       count_if(vendor_id = 7) AS viajes_vendor_7,
       count_if(duration_minutes <= 0) AS duracion_no_positiva,
       count_if(fare_amount < 0 AND total_amount >= 0) AS tarifa_negativa_total_positivo
FROM trips WHERE taxi_type = 'yellow' GROUP BY periodo ORDER BY periodo;

-- Peaje de congestión, directo sobre Parquet porque la columna no existe en 2024
SELECT regexp_extract(filename, 'tripdata_(\d{4}-\d{2})', 1) AS periodo,
       count(*) AS viajes,
       round(100.0 * count_if(cbd_congestion_fee > 0) / count(*), 1) AS pct_con_peaje,
       round(avg(cbd_congestion_fee) FILTER (WHERE cbd_congestion_fee > 0), 2) AS peaje_promedio_usd
FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true, filename = true)
WHERE cbd_congestion_fee IS NOT NULL
GROUP BY periodo ORDER BY periodo;
```
