# Calidad inicial de los datos 2026

Resultados obtenidos el 2 de octubre de 2026 al ejecutar
`sql/exploration.sql` sobre los archivos publicados de enero a agosto. Estos
valores son una fotografia del conjunto disponible en esa fecha y deben volver
a calcularse cuando la NYC TLC publique meses nuevos.

## Cobertura

| Tipo de taxi | Archivos | Registros |
| --- | ---: | ---: |
| Yellow | 8 | 29,703,355 |
| Green | 8 | 337,114 |

Los campos clave revisados (`VendorID`, fechas, ubicaciones, distancia, tarifa
y monto total) no presentan valores nulos en los archivos disponibles.

## Problemas observados

| Control | Yellow | Green |
| --- | ---: | ---: |
| Distancia igual a cero | 952,231 | 12,212 |
| Distancia negativa | 0 | 0 |
| Tarifa negativa | 157,364 | 999 |
| Monto total negativo | 161,835 | 1,023 |
| Duracion menor o igual a cero | 371,683 | 234 |
| Distancia mayor a 100 millas | 1,223 | 72 |
| Duracion mayor a 24 horas | 263 | 4 |
| Monto total mayor a 1,000 USD | 49 | 1 |

Los rangos tambien muestran valores extremos que requieren revision antes de
calcular promedios o indicadores:

- Yellow: distancia maxima de 328,522.2 millas, tarifa entre -2,555.2 y
  7,045.0 USD, monto total entre -2,560.2 y 7,053.5 USD, y duraciones entre
  -18,031,051 y 1,029,925 segundos.
- Green: distancia maxima de 179,830.92 millas, tarifa entre -500.0 y
  1,676.7 USD, monto total entre -501.5 y 1,678.2 USD, y duraciones entre
  -41,220 y 147,382 segundos.

Estos conteos no eliminan registros. Sirven para definir reglas de limpieza y
analizar por separado reembolsos, cancelaciones, errores de captura y valores
atipicos en las siguientes etapas.
