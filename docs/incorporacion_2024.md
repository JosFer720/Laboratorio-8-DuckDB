# Incorporacion de 2024

Cambios realizados para incorporar los datos de 2024 conservando los de 2026.

## Cambios en el sistema

- `scripts/download_data.py`: la constante `ANIOS_PERMITIDOS = (2024, 2026)`
  reemplaza a la restriccion de un solo anio. `--year` se puede repetir y, sin
  `--year`, descarga todos los anios soportados. La logica de descarga no cambio:
  sigue omitiendo archivos que ya existen y reportando los meses no publicados.
- `tests/test_download_data.py`: nuevas pruebas para la descarga de todos los
  anios, la repeticion de `--year` y el rechazo de un anio no soportado.
- `sql/exploration.sql`: las rutas pasaron de `data/raw/<tipo>/2026/*.parquet` a
  `data/raw/<tipo>/*/*.parquet`, y los controles de calidad se desglosan por anio.

## Validacion

```bash
docker compose exec lab python scripts/download_data.py        # descarga lo que falta
docker compose exec lab python scripts/download_data.py        # segunda vez: 0 descargados
```

| Verificacion | Resultado |
| --- | --- |
| Primera ejecucion (carpeta `data/raw/` vacia) | 40 archivos descargados (12 + 12 de 2024 y 8 + 8 de 2026), 0 fallidos |
| Segunda ejecucion | 0 descargados, 40 ya existian |
| Meses no publicados | septiembre a diciembre de 2026 (8 archivos); se reportan, no son un error |
| Archivos por tipo | 20 yellow y 20 green (consulta 1 de `exploration.sql`) |
| Registros | 70,873,075 yellow y 997,332 green; el desglose por archivo no muestra meses vacios |
| 2026 sin cambios | 29,703,355 viajes yellow y 337,114 green, iguales a los documentados al descargar solo 2026 |

Consultas utilizadas para validar (todas en `sql/exploration.sql`):

```sql
SELECT count(*) FROM glob('data/raw/yellow/*/*.parquet');            -- archivos
SELECT filename, count(*) FROM read_parquet('data/raw/yellow/*/*.parquet',
       filename = true, union_by_name = true) GROUP BY filename ORDER BY filename;
```

## Necesitaron cambios las consultas anteriores?

Solo las rutas: el comodin `*/*.parquet` reemplaza al anio fijo. El resto de la
logica no cambio porque las columnas de los viajes son las mismas. Hubo un
cambio de esquema: los Parquet de 2026 tienen dos columnas extra
(`cbd_congestion_fee` y `request_source`). `union_by_name = true` hace que
DuckDB una los archivos por nombre y rellene con `NULL` las columnas ausentes,
asi que las consultas siguen funcionando con ambos anios sin tratamiento
especial.

## Que permite incorporar archivos nuevos sin modificar el flujo

- **Estructura por convencion**: los archivos viven en `data/raw/<tipo>/<anio>/`
  con el nombre original de la TLC. Las consultas y `scripts/create_database.py`
  descubren los anios con un comodin, no con una lista.
- **Descarga incremental e idempotente**: un archivo existente no se vuelve a
  descargar, y el script consulta al servidor que meses estan publicados, de
  modo que se puede volver a ejecutar cuando salgan meses nuevos.
- **Un solo punto de configuracion**: agregar un anio es agregarlo a
  `ANIOS_PERMITIDOS`. Las pruebas y el resto del flujo no dependen del anio.
- **`year` y `month` en la tabla `trips`**, tomados del nombre del archivo, de
  modo que el analisis agrupa por periodo sin depender de las fechas de los
  viajes, que a veces son erroneas.
- **Lectura con `union_by_name`**: tolera columnas que aparezcan o desaparezcan
  entre anios.

> **Nota (al incorporar 2025):** con los tres anios, `parquet_schema()` muestra
> que `cbd_congestion_fee` aparece en enero de 2025 y `request_source` en junio de
> 2026; ver [`incorporacion_2025.md`](incorporacion_2025.md) y
> [`data_quality.md`](data_quality.md).
