# Calidad de los datos

Resultados obtenidos el 2 de octubre de 2026 al ejecutar `sql/exploration.sql`
sobre los archivos descargados: 2024 completo (12 meses) y 2026 de enero a
agosto. Son una fotografia del conjunto disponible en esa fecha y deben volver
a calcularse cuando la NYC TLC publique meses nuevos.

## Cobertura

| Tipo de taxi | Anio | Archivos | Registros |
| --- | --- | ---: | ---: |
| Yellow | 2024 | 12 | 41,169,720 |
| Yellow | 2026 | 8 | 29,703,355 |
| Green | 2024 | 12 | 660,218 |
| Green | 2026 | 8 | 337,114 |

Los campos clave revisados (`VendorID`, fechas, ubicaciones, distancia, tarifa
y monto total) no presentan valores nulos en ningun anio. Si hay nulos en
`payment_type` (green) y en `passenger_count` (ver abajo).

## Cambios de esquema entre anios

Los archivos de 2026 incluyen columnas que no existen en 2024
(`cbd_congestion_fee`, presente en todas las filas, y `request_source`, que
solo tiene valor en una parte de ellas: 2.9 M de las 29.7 M de yellow). Por eso las consultas leen con `union_by_name = true`: DuckDB une
los archivos por nombre de columna y rellena con `NULL` las que faltan en un
archivo, en lugar de fallar por columnas distintas.

## Problemas observados

| Control | Yellow 2024 | Yellow 2026 | Green 2024 | Green 2026 |
| --- | ---: | ---: | ---: | ---: |
| Distancia igual a cero | 776,305 | 952,231 | 34,574 | 12,212 |
| Distancia negativa | 0 | 0 | 0 | 0 |
| Tarifa negativa | 731,024 | 157,364 | 2,144 | 999 |
| Monto total negativo | 609,344 | 161,835 | 2,174 | 1,023 |
| Duracion menor o igual a cero | 13,510 | 371,683 | 662 | 234 |
| Distancia mayor a 100 millas | 1,613 | 1,223 | 235 | 72 |
| Duracion mayor a 24 horas | 230 | 263 | 0 | 4 |
| Monto total mayor a 1,000 USD | 43 | 49 | 1 | 1 |

Rangos observados (muestran errores de captura evidentes):

| | Yellow 2024 | Yellow 2026 | Green 2024 | Green 2026 |
| --- | ---: | ---: | ---: | ---: |
| Distancia maxima (millas) | 398,608.6 | 328,522.2 | 233,972.4 | 179,830.9 |
| Tarifa minima (USD) | -2,261.2 | -2,555.2 | -450.0 | -500.0 |
| Tarifa maxima (USD) | 335,544.4 | 7,045.0 | 1,422.6 | 1,676.7 |
| Duracion minima (s) | -85,623 | -18,031,051 | -1,896 | -41,220 |
| Duracion maxima (s) | 586,051 | 1,029,925 | 86,392 | 147,382 |

Ademas, hay viajes con fecha de recogida fuera del anio de su archivo (por
ejemplo 2001, 2002 o 2008): 56 y 17 viajes yellow, y 20 y 14 green, en 2024 y
2026. Son errores del reloj del taxi.

## Hallazgos de calidad entre anios

- **Duraciones no positivas en yellow 2026.** Pasan de 13,510 (0.03 %) a
  371,683 (1.25 %) y aparecen de forma constante en todos los meses de 2026. Los
  371,683 casos se concentran en el `VendorID` 7, un proveedor que no existe en
  2024: registra 367,120 viajes y **todos** tienen duracion cero (hora de
  recogida igual a la de bajada). Es un problema de captura de ese proveedor.
- **Montos negativos en yellow.** Bajan de 609,344 en 2024 a 161,835 en 2026
  (de 1.5 % a 0.5 % de los viajes). Corresponden a reembolsos, disputas o
  ajustes y no a viajes reales.
- **`payment_type` no reportado.** En green pasa de 3.7 % de viajes sin forma de
  pago en 2024 a 14.5 % en 2026. En yellow la categoria 0 (tarifa flexible o no
  registrada) pasa de 9.9 % a 26.0 %.
- **`passenger_count` nulo.** Coincide con los viajes sin forma de pago
  registrada: 9.9 % de yellow 2024 y 26.0 % de yellow 2026.

## Reglas de limpieza adoptadas

Estos conteos no eliminan registros: la tabla `trips` conserva todas las filas.
Los analisis que calculan promedios usan la definicion de **viaje valido**:

```text
0 < trip_distance < 100 millas
0 < fare_amount < 1000 USD
0 < duracion < 24 horas
```

Este filtro excluye entre 3.6 % y 5.5 % de los viajes segun tipo de taxi y anio.
Los umbrales (100 millas, 1,000 USD, 24 horas) son reglas de revision, elegidas
porque estan muy por encima de lo plausible para un viaje en la ciudad; los
reembolsos y valores extremos se analizan por separado en lugar de mezclarse con
los viajes normales.
