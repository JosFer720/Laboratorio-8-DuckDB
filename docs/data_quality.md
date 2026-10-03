# Calidad de los datos

Resultados obtenidos el 2 de octubre de 2026 al ejecutar `sql/exploration.sql`
sobre los archivos descargados: 2024 y 2025 completos (12 meses) y 2026 de enero
a agosto. Son una fotografia del conjunto disponible en esa fecha y deben volver
a calcularse cuando la NYC TLC publique meses nuevos.

La primera version de este documento se escribio solo con 2024 y 2026. Al
incorporar 2025 se corrigieron dos conclusiones: el proveedor con duraciones
cero y las columnas nuevas no aparecen en 2026 sino en 2025 (ver mas abajo).

## Cobertura

| Tipo de taxi | Anio | Archivos | Registros |
| --- | --- | ---: | ---: |
| Yellow | 2024 | 12 | 41,169,720 |
| Yellow | 2025 | 12 | 48,722,602 |
| Yellow | 2026 | 8 | 29,703,355 |
| Green | 2024 | 12 | 660,218 |
| Green | 2025 | 12 | 591,375 |
| Green | 2026 | 8 | 337,114 |
| **Total** | | **64** | **121,184,384** |

Los campos clave revisados (`VendorID`, fechas, ubicaciones, distancia, tarifa
y monto total) no presentan valores nulos en ningun anio. Si hay nulos en
`payment_type` (green) y en `passenger_count` (ver abajo).

## Cambios de esquema entre anios

`parquet_schema()` muestra en que mes aparece cada columna:

| Columna | Aparece en | Contenido |
| --- | --- | --- |
| `cbd_congestion_fee` | enero de 2025 (yellow y green) | peaje de congestion del sur de Manhattan, vigente desde el 5 de enero de 2025; 0.75 USD por viaje cuando aplica |
| `request_source` | junio de 2026 (yellow y green) | origen de la solicitud; solo una parte de las filas tiene valor |

Por eso las consultas leen con `union_by_name = true`: DuckDB une los archivos
por nombre de columna y rellena con `NULL` las que faltan en un archivo, en
lugar de fallar por columnas distintas. La tabla `trips` no incluye estas
columnas porque no existen en todos los anios; cuando se necesitan se leen
directamente de los Parquet (ver `notebooks/evolucion_2024_2026.ipynb`).

## Problemas observados

| Control | Yellow 2024 | Yellow 2025 | Yellow 2026 | Green 2024 | Green 2025 | Green 2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Distancia igual a cero | 776,305 | 1,402,958 | 952,231 | 34,574 | 24,438 | 12,212 |
| Distancia negativa | 0 | 0 | 0 | 0 | 0 | 0 |
| Tarifa negativa | 731,024 | 2,848,620 | 157,364 | 2,144 | 1,736 | 999 |
| Monto total negativo | 609,344 | 973,721 | 161,835 | 2,174 | 1,774 | 1,023 |
| Duracion menor o igual a cero | 13,510 | 546,304 | 371,683 | 662 | 1,910 | 234 |
| Distancia mayor a 100 millas | 1,613 | 2,870 | 1,223 | 235 | 209 | 72 |
| Duracion mayor a 24 horas | 230 | 352 | 263 | 0 | 2 | 4 |
| Monto total mayor a 1,000 USD | 43 | 85 | 49 | 1 | 1 | 1 |
| % excluido por la regla de viaje valido | 3.56 | 9.35 | 4.96 | 5.53 | 5.02 | 5.24 |

Rangos observados (muestran errores de captura evidentes):

| | Yellow 2024 | Yellow 2025 | Yellow 2026 | Green 2024 | Green 2025 | Green 2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Distancia maxima (millas) | 398,608.6 | 397,994.4 | 328,522.2 | 233,972.4 | 262,315.9 | 179,830.9 |
| Tarifa minima (USD) | -2,261.2 | -1,807.6 | -2,555.2 | -450.0 | -470.6 | -500.0 |
| Tarifa maxima (USD) | 335,544.4 | 863,372.1 | 7,045.0 | 1,422.6 | 1,086.6 | 1,676.7 |
| Duracion minima (s) | -85,623 | -3,088,339 | -18,031,051 | -1,896 | -2,930 | -41,220 |
| Duracion maxima (s) | 586,051 | 892,846 | 1,029,925 | 86,392 | 90,046 | 147,382 |

Ademas, hay viajes con fecha de recogida fuera del anio de su archivo (por
ejemplo 2001, 2002 o 2008): 56, 29 y 17 viajes yellow, y 20, 21 y 14 green, en
2024, 2025 y 2026. Son errores del reloj del taxi.

## Hallazgos de calidad entre anios

- **Duraciones no positivas en yellow desde 2025.** Pasan de 13,510 (0.03 %) en
  2024 a 546,304 (1.12 %) en 2025 y 371,683 (1.25 %) en 2026. La serie mensual
  muestra que empiezan a crecer en febrero y marzo de 2025 y se estabilizan en
  1.2 a 1.6 % de los viajes. Las causa el `VendorID` 7: aparece en diciembre de
  2024 (230 viajes), registra 535,901 viajes en 2025 y 367,120 en 2026, y
  **todos** tienen duracion cero (hora de recogida igual a la de bajada). Explica
  el 98.1 % de los casos de 2025 y el 98.8 % de 2026. Es un problema de captura de
  ese proveedor. (Con solo 2024 y 2026 se habia atribuido a un proveedor nuevo en
  2026.)
- **Tarifas negativas con total positivo en yellow 2025.** De las 2.85 M tarifas
  negativas de 2025, 1.88 M son viajes del `VendorID` 2 con `payment_type = 0`
  (tarifa flexible) con tarifa promedio de -4.00 USD y total de +4.30 USD. El
  patron ya existia en 2024 (125 mil viajes), crece durante 2025 y desaparece en
  diciembre de 2025 (135 casos en 2026). Es una convencion de registro de ese
  proveedor, no reembolsos; por eso el porcentaje excluido por la regla de viaje
  valido sube a 9.35 % en 2025.
- **Montos negativos (reembolsos, disputas o ajustes).** En yellow son 1.5 %
  de los viajes en 2024, 2.0 % en 2025 y 0.5 % en 2026.
- **`payment_type` no reportado.** En green pasa de 3.7 % de viajes sin forma de
  pago en 2024 a 8.4 % en 2025 y 14.5 % en 2026. En yellow la categoria 0 (tarifa
  flexible o no registrada) pasa de 9.9 % a 23.8 % y 26.0 %.
- **`passenger_count` nulo.** Coincide exactamente con los viajes sin forma de
  pago registrada (categoria 0 o nula): 9.9 %, 23.8 % y 26.0 % de yellow y 3.7 %,
  8.4 % y 14.5 % de green en 2024, 2025 y 2026.

## Reglas de limpieza adoptadas

Estos conteos no eliminan registros: la tabla `trips` conserva todas las filas.
Los analisis que calculan promedios usan la definicion de **viaje valido**:

```text
0 < trip_distance < 100 millas
0 < fare_amount < 1000 USD
0 < duracion < 24 horas
```

Este filtro excluye entre 3.6 % y 9.4 % de los viajes segun tipo de taxi y anio.
Los umbrales (100 millas, 1,000 USD, 24 horas) son reglas de revision, elegidas
porque estan muy por encima de lo plausible para un viaje en la ciudad; los
reembolsos y valores extremos se analizan por separado en lugar de mezclarse con
los viajes normales. El indicador `15_calidad_mensual` del tablero sigue la
proporcion excluida mes a mes para detectar nuevos problemas de captura.
