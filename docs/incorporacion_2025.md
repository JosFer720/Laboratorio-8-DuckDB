# Incorporación de 2025

Este documento cuenta cómo se agregaron al sistema los datos de 2025, sin perder
los de 2024 y 2026 que ya estaban descargados. Después de este paso el proyecto
trabaja con los taxis yellow y green de los tres años.

## Qué se cambió

El cambio principal fue muy pequeño. En `scripts/download_data.py` hay una lista
con los años que el sistema sabe descargar, llamada `ANIOS_PERMITIDOS`. Se agregó
2025 a esa lista y quedó como `(2024, 2025, 2026)`. Con eso el script ya sabe
pedir los archivos de 2025 a la TLC. La forma de descargar no cambió. El script
sigue saltándose los archivos que ya existen, sigue preguntándole al servidor qué
meses están publicados antes de pedirlos y sigue escribiendo cada descarga primero
en un archivo temporal, para que una descarga cortada no deje un archivo a medias.

Además, el mismo script ahora descarga el catálogo de zonas de la TLC
(`taxi_zone_lookup.csv`) y lo guarda en `data/raw/zones/`. Ese archivo dice qué
nombre y qué distrito corresponde a cada número de zona. También se descarga una
sola vez. Después `scripts/create_database.py` lo carga en la base como la tabla
`zones`, usando [`sql/create_zones.sql`](../sql/create_zones.sql), para que el
tablero pueda mostrar nombres de lugares en lugar de números.

Las pruebas automáticas también se actualizaron. En `tests/test_download_data.py`
la prueba de descargar todos los años ahora espera seis descargas (dos tipos de
taxi por tres años), y hay pruebas nuevas para el catálogo de zonas. En
`tests/test_database.py` hay pruebas para la tabla `zones`.

Ni `sql/exploration.sql` ni `sql/create_tables.sql` tuvieron que cambiar. Las dos
buscan los archivos con un comodín, `data/raw/<tipo>/*/*.parquet`, que quiere
decir cualquier archivo Parquet dentro de cualquier carpeta de año. Por eso los
archivos de 2025 entraron solos en cuanto se descargaron.

## Cómo se comprobó que todo quedó bien

Se corrió la descarga tres veces seguidas. La primera solo con 2024 y 2026, para
tener el mismo punto de partida que antes de este ejercicio. La segunda con todos
los años, para que bajara 2025. La tercera otra vez con todos los años, para
comprobar que no volviera a bajar nada.

```bash
docker compose exec lab python scripts/download_data.py --year 2024 --year 2026   # estado previo
docker compose exec lab python scripts/download_data.py                           # agrega 2025
docker compose exec lab python scripts/download_data.py                           # tercera vez, nada nuevo
```

| Qué se revisó | Resultado |
| --- | --- |
| Descarga de 2024 y 2026 con la carpeta `data/raw/` vacía | 40 archivos descargados y ninguno fallido |
| Descarga con todos los años | 25 descargados (12 de yellow 2025, 12 de green 2025 y el catálogo de zonas), 40 que ya existían y ninguno fallido |
| Descarga repetida | 0 descargados, 65 que ya existían y ninguno fallido |
| Meses que todavía no existen | De septiembre a diciembre de 2026 (8 archivos). El script los reporta como no publicados y eso es normal |
| Archivos por tipo de taxi (consulta 1 de `exploration.sql`) | 32 de yellow y 32 de green |
| Registros por archivo (consulta 2) | Ningún mes vacío. En 2025 hay 48,722,602 viajes yellow y 591,375 green |
| 2024 y 2026 siguen iguales | 41,169,720 y 29,703,355 viajes yellow, y 660,218 y 337,114 green, los mismos números que había antes de agregar 2025 |
| Tabla `trips` creada con `create_database.py` | 121,184,384 filas, 3.4 GB, creada en 8.6 segundos |
| Pruebas automáticas | Las 36 pruebas de `tests.test_download_data`, `tests.test_database` y `tests.test_indicators` pasan |

Estas son las consultas que se usaron para comprobarlo. Las dos primeras leen los
archivos Parquet directamente y están en `sql/exploration.sql`. La tercera revisa
la tabla ya creada. La cuarta busca en qué mes aparece por primera vez una columna
nueva dentro de los archivos.

```sql
-- Archivos y registros por tipo (directo sobre Parquet)
SELECT count(*) FROM glob('data/raw/yellow/*/*.parquet');
SELECT filename, count(*) FROM read_parquet('data/raw/yellow/*/*.parquet',
       filename = true, union_by_name = true) GROUP BY filename ORDER BY filename;

-- La tabla materializada tiene los tres años y sus meses
SELECT taxi_type, year, count(*) AS viajes, min(month) AS mes_min, max(month) AS mes_max
FROM trips GROUP BY ALL ORDER BY ALL;

-- En qué mes aparece cada columna nueva
SELECT min(regexp_extract(file_name, '(\d{4}-\d{2})', 1)) AS primer_mes
FROM parquet_schema('data/raw/yellow/*/*.parquet')
WHERE name = 'cbd_congestion_fee';   -- 2025-01 ('request_source' aparece en 2026-06)
```

## ¿Siguieron funcionando las consultas anteriores?

Se volvieron a correr todas con los tres años juntos. Algunas funcionaron igual,
pero otras tuvieron problemas que con solo dos años no se notaban.

| Archivo | Qué pasó | Qué se cambió |
| --- | --- | --- |
| `sql/exploration.sql` | Funcionó | Nada |
| `sql/create_tables.sql` | Funcionó | Nada |
| `sql/analysis.sql` | Falló | La comparación entre años tenía fijo el mes 8 y la consulta de percentiles se quedó sin memoria |
| `sql/benchmark_queries.sql` | Funcionó | La consulta q7 calculaba los percentiles de la misma forma que la que falló, así que se cambió por precaución |
| `notebooks/analysis.ipynb` | Quedó incompleto | La gráfica mensual tenía fijos los años 2024 y 2026 (2025 no aparecía) y la comparación usaba el mes 8 fijo |

El primer cambio fue en la forma de comparar años. Antes las consultas decían
`month <= 8`, o sea, "usar solo de enero a agosto", porque 2026 llegaba hasta
agosto. Eso deja de ser cierto en cuanto la TLC publique septiembre. Ahora la
consulta busca sola los meses que aparecen en todos los años descargados, con este
filtro.

```sql
WHERE month IN (
    SELECT month FROM trips GROUP BY month
    HAVING count(DISTINCT year) = (SELECT count(DISTINCT year) FROM trips)
)
```

Así la consulta está pensada para no tener que tocarse cuando aparezcan meses
nuevos de 2026 o cuando se agregue otro año.

El segundo cambio fue en los percentiles. Un percentil dice qué valor deja por
debajo a cierto porcentaje de los datos. Por ejemplo, el percentil 50 es la
mediana. Para calcularlo, DuckDB tiene que guardar en memoria todos los valores.
La consulta original pedía seis percentiles con seis llamadas separadas a
`quantile_cont`, y cada llamada guardaba su propia copia de los cerca de 117
millones de tarifas. Con 2024 y 2026 eso todavía cabía, pero con los tres años el
proceso se quedó sin memoria y el sistema lo cerró (código de salida 137) dentro
del contenedor de 7.7 GB. Se cambió por una sola llamada que pide los seis
percentiles juntos, `quantile_cont(fare_amount, [0.05, 0.25, ...])`, que da los
mismos valores guardando una sola copia. Con eso todo `analysis.sql` corre con un
máximo de 4 GB de memoria.

El tercer cambio fue en el notebook. Los colores y las líneas de cada año ahora se
crean a partir de los años que hay en la tabla `trips`, sin escribirlos a mano.

## Resultado

El análisis de los tres años juntos está en
[`analisis_tres_anios.md`](analisis_tres_anios.md) y en
[`notebooks/evolucion_2024_2026.ipynb`](../notebooks/evolucion_2024_2026.ipynb).
El tablero ([`indicadores.md`](indicadores.md)) y la comparación de velocidad entre
Parquet y la tabla ([`benchmark.md`](benchmark.md)), que ahora usa tres tamaños de
datos, se volvieron a generar con los tres años sin cambiar sus scripts.
