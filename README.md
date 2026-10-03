# Lab 8 - DuckDB

Laboratorio 8 del curso **CC3084 - Data Science** (Universidad del Valle de
Guatemala, Ciclo 2, 2026).

Flujo reproducible con DuckDB para descargar, consultar, transformar y analizar
los viajes de taxis amarillos (*yellow*) y verdes (*green*) de Nueva York
publicados por la NYC TLC. El flujo crece de forma incremental: se descargan los
archivos Parquet de cada anio (2024, 2025 y 2026), se consultan directamente, se
materializan en una base DuckDB, se comparan ambas estrategias de acceso y se
construye un tablero de indicadores en Metabase.

## Repositorio

Este repositorio es un **fork** de <https://github.com/menene/duckdb>, el
repositorio base proporcionado por el docente. Para trabajar con el:

```bash
git clone <url-de-este-fork>
cd <directorio-del-fork>
```

Opcionalmente, para recibir correcciones publicadas por el docente:

```bash
git remote add upstream https://github.com/menene/duckdb.git
git fetch upstream
```

## Estructura

```text
.
+-- data/
|   +-- raw/            Parquet originales: data/raw/<tipo>/<anio>/ y data/raw/zones/
|   +-- processed/      base materializada: taxi.duckdb
+-- notebooks/
|   +-- analysis.ipynb             analisis exploratorio
|   +-- evolucion_2024_2026.ipynb  evolucion de los tres anios
+-- scripts/
|   +-- download_data.py     descarga incremental desde la NYC TLC
|   +-- create_database.py   crea data/processed/taxi.duckdb (tablas trips y zones)
|   +-- benchmark.py         compara Parquet directo vs tabla DuckDB
|   +-- run_sql.py           ejecuta un archivo .sql e imprime los resultados
|   +-- indicators.py        ejecuta los indicadores y guarda sus resultados
|   +-- render_dashboard.py  imagen estatica del tablero
|   +-- setup_dashboard.py   crea el tablero en Metabase
+-- sql/
|   +-- exploration.sql        consultas directas sobre Parquet
|   +-- analysis.sql           analisis exploratorio sobre la tabla trips
|   +-- create_tables.sql      definicion de la tabla trips
|   +-- create_zones.sql       definicion de la tabla zones
|   +-- benchmark_queries.sql  consultas del benchmark
|   +-- indicators/            una consulta por indicador del tablero
+-- docs/               documentacion de consultas, calidad, benchmark, indicadores y discusion
|   +-- dashboard/      imagen del tablero y resultados de cada indicador
+-- tests/              pruebas de los scripts y de los indicadores
+-- Dockerfile
+-- metabase.Dockerfile
+-- docker-compose.yml
+-- README.md
```

Proposito de cada directorio:

- `data/raw/`: archivos Parquet originales descargados de la NYC TLC,
  organizados por tipo de taxi y anio. No se modifican ni se versionan.
- `data/processed/`: artefactos derivados y bases DuckDB materializadas. Se
  pueden regenerar a partir de los datos originales y tampoco se versionan.
- `notebooks/`: analisis interactivos y visualizaciones en Jupyter.
- `scripts/`: programas reproducibles para descargar, validar y transformar
  datos.
- `sql/`: consultas DuckDB versionadas, incluidas las exploraciones directas
  sobre Parquet y los indicadores del tablero (`sql/indicators/`).
- `docs/`: resultados, evidencia y documentacion complementaria.

## Requisitos

- Docker, con Docker Compose
- Git

La primera construccion del ambiente descarga varios cientos de MB y puede
tardar algunos minutos.

Considere el espacio en disco: las imagenes de Docker ocupan unos 3 GB, los
Parquet de 2024, 2025 y 2026 unos 1.9 GB y la base materializada unos 3.4 GB (el
benchmark crea temporalmente otra de hasta el mismo tamano). Se recomienda tener
al menos 15 GB libres y asignar a Docker al menos 8 GB de memoria.

## Datos

`scripts/download_data.py` descarga los archivos Parquet publicados por la TLC
(`--help` muestra las opciones disponibles). Se guardan en
`data/raw/<tipo>/<anio>/`. Anios soportados: 2024, 2025 y 2026. Tambien
descarga el catalogo de zonas de la TLC (`data/raw/zones/taxi_zone_lookup.csv`),
que la base usa para mostrar nombres de zona.

La TLC publica cada mes con varias semanas de atraso, por lo que los ultimos
meses de 2026 todavia no existen (a octubre de 2026 estan publicados hasta
agosto). El script consulta al servidor que meses estan publicados, de modo que
vuelve a ejecutarse sin problema conforme aparezcan nuevos archivos.

Los datos descargados **no deben incluirse en el repositorio Git**. El archivo
`.gitignore` ya esta configurado para evitarlo.

Fuente de datos: NYC TLC Trip Record Data
<https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>

Dentro de los contenedores, la carpeta `data/` del proyecto esta montada en
`/workspace/data`. Esa es la ruta que deben usar las herramientas que corren
dentro del ambiente, no la ruta de su computadora.

> **Nota sobre DuckDB:** un archivo `.duckdb` admite un solo proceso con permiso
> de escritura a la vez. Si conecta una herramienta externa a su base de datos,
> use el modo de solo lectura (`read_only`) en esa conexion; de lo contrario los
> demas procesos no podran abrir el archivo.

---

## Como levantar el ambiente

Desde la raiz del repositorio, construya e inicie JupyterLab y Metabase:

```bash
docker compose up --build -d
docker compose ps
```

Cuando ambos servicios aparezcan como `healthy`, abra:

- JupyterLab: <http://localhost:8888/lab>
- Metabase: <http://localhost:3000>

Los puertos solo se publican en `127.0.0.1`; esta configuracion sin token de
Jupyter esta pensada exclusivamente para desarrollo local. No exponga estos
servicios directamente a Internet.

Puede comprobar las herramientas instaladas con:

```bash
docker compose exec lab python --version
docker compose exec lab python -c "import duckdb, jupyterlab; print('DuckDB', duckdb.__version__); print('JupyterLab', jupyterlab.__version__)"
```

Las carpetas `data/`, `notebooks/`, `scripts/`, `sql/`, `docs/` y `tests/` se
montan bajo `/workspace` dentro del contenedor `lab`. Por eso, los cambios y
archivos descargados quedan disponibles tanto en el host como en Docker. Para
detener los servicios sin borrar datos:

```bash
docker compose down
```

Metabase conserva su configuracion en el volumen `metabase-data`. Cuando
exista `data/processed/taxi.duckdb`, registre en Metabase una base DuckDB cuya
ruta sea `/workspace/data/processed/taxi.duckdb`. Evite que Metabase y otro
proceso escriban simultaneamente en el mismo archivo.

## Como descargar los datos

Con los servicios iniciados, ejecute la descarga dentro del ambiente
reproducible:

```bash
docker compose exec lab python scripts/download_data.py                  # todos los anios
docker compose exec lab python scripts/download_data.py --year 2024      # un anio
docker compose exec lab python scripts/download_data.py --year 2024 --year 2025 --taxi yellow
```

Si instalo localmente las mismas dependencias de `requirements.txt`, el comando
equivalente es `python scripts/download_data.py`.

El script descarga Yellow Taxi y Green Taxi en `data/raw/<tipo>/<anio>/`. Los
meses que todavia no haya publicado la TLC se reportan y se omiten. Si un
archivo no vacio ya existe, una nueva ejecucion lo conserva y no vuelve a
descargarlo; esto permite actualizar el conjunto de datos incrementalmente.
Una descarga interrumpida no deja archivos `.parquet` a medias porque se escribe
primero en un archivo temporal.

**Como saber que la descarga esta completa:** el resumen final del script indica
cuantos archivos se descargaron, cuantos ya existian, cuantos no estan
publicados y cuantos fallaron (el codigo de salida es distinto de cero si hubo
fallos). Ejecutarlo por segunda vez debe reportar `descargados: 0`. Ademas, la
consulta 2 de `sql/exploration.sql` cuenta los registros de cada archivo para
detectar meses vacios. La incorporacion de cada anio esta documentada en
[`docs/incorporacion_2024.md`](docs/incorporacion_2024.md) y
[`docs/incorporacion_2025.md`](docs/incorporacion_2025.md).

### Cambios realizados al script de descarga

El repositorio base traía `scripts/download_data.py` a medio terminar. Ya saltaba
los archivos que existían y escribía cada descarga en un archivo temporal, pero
solo servía para 2026 y tenía problemas que podían dar una descarga incompleta sin
que nadie se diera cuenta. Estos fueron los cambios, en el orden en que se
hicieron.

Primero, para descargar 2026 de forma confiable, se hicieron cinco cambios.

1. El año ya no está escrito dentro de las funciones. El script original usaba una
   constante `ANIO = 2026` en todos lados y no tenía la opción `--year`. Ahora las
   funciones reciben el año como dato y se agregó `--year` a la línea de comandos.
2. Se agregó `validar_parametros`, que revisa el tipo de taxi, el año y el mes antes
   de armar la ruta o la dirección de descarga. Así un valor raro, como un tipo de
   taxi `../otra_carpeta`, no puede escribir archivos fuera de `data/raw/`.
3. Se corrigió cómo se decide si un mes ya está publicado. El script original
   trataba cualquier error de red, o cualquier error del servidor, como si el mes
   todavía no existiera. Entonces un corte de internet hacía que el script dijera
   "no publicado" y terminara como si todo hubiera salido bien. Ahora solo las
   respuestas 403 y 404 cuentan como mes no publicado. La TLC responde 403 para los
   meses que todavía no existen. Cualquier otro error se reporta como descarga
   fallida y el script termina con un código distinto de cero.
4. El archivo temporal ahora tiene un nombre único. Antes siempre se llamaba igual
   que el archivo final más `.part`, y dos descargas al mismo tiempo podían
   escribir en el mismo archivo. Ahora se crea con `tempfile.mkstemp`, se borra si
   la descarga falla y solo se renombra al nombre final cuando terminó bien.
5. También se reportan como fallidos los errores al guardar en disco (`OSError`),
   por ejemplo cuando no queda espacio. Antes solo se manejaban los errores de red.

Junto con estos cambios se creó `tests/test_download_data.py`, con pruebas que
simulan al servidor de la TLC. Revisan que un archivo existente no se vuelva a
pedir, que un 403 o un 404 cuenten como mes no publicado, que un error de red o un
error 503 cuenten como falla, y que una descarga cortada no deje archivos a medias.

Después, para agregar 2024 se cambió la constante por la lista
`ANIOS_PERMITIDOS = (2024, 2026)`, y `--year` se puede repetir o dejar sin poner
para descargar todos los años. Está explicado en
[`docs/incorporacion_2024.md`](docs/incorporacion_2024.md).

Por último, para agregar 2025 se sumó ese año a la lista y el script empezó a
descargar también el catálogo de zonas de la TLC en `data/raw/zones/`. Está
explicado en [`docs/incorporacion_2025.md`](docs/incorporacion_2025.md).

## Como ejecutar el analisis

Los scripts SQL se ejecutan con `scripts/run_sql.py`, que imprime el resultado de
cada consulta del archivo:

```bash
# Consultas directas sobre los Parquet (no necesitan base de datos)
docker compose exec -T lab python scripts/run_sql.py sql/exploration.sql

# Crear la tabla materializada y ejecutar el analisis exploratorio sobre ella
docker compose exec lab python scripts/create_database.py
docker compose exec -T lab python scripts/run_sql.py sql/analysis.sql --db data/processed/taxi.duckdb
```

- **Exploracion directa sobre Parquet** (`sql/exploration.sql`): archivos,
  registros, columnas, tipos, muestras y calidad de datos. Usa
  `data/raw/<tipo>/*/*.parquet`, por lo que incluye todos los anios descargados.
  Esta documentada en [`docs/exploration_queries.md`](docs/exploration_queries.md)
  y los problemas de calidad encontrados en
  [`docs/data_quality.md`](docs/data_quality.md).
- **Tabla materializada** (`scripts/create_database.py`): ejecuta
  `sql/create_tables.sql` y crea `data/processed/taxi.duckdb` con la tabla
  `trips`, que une yellow y green con las columnas normalizadas, `taxi_type`,
  `year`, `month` y `duration_minutes`, y la tabla `zones` (`sql/create_zones.sql`).
  Acepta `--year` para limitar los anios. Para agregar un anio nuevo basta con
  descargarlo y volver a ejecutar el script.
- **Analisis exploratorio** (`sql/analysis.sql` y `notebooks/analysis.ipynb`):
  preguntas sobre volumen mensual, distancia y tarifa, diferencias entre yellow
  y green, actividad por hora, formas de pago y valores atipicos, con sus
  hallazgos. El notebook se abre desde JupyterLab
  (<http://localhost:8888/lab>) y se puede volver a ejecutar completo.
- **Evolucion 2024-2026** (`notebooks/evolucion_2024_2026.ipynb`): volumen,
  precio, formas de pago, calidad de datos y peaje de congestion a lo largo de los
  tres anios; resumido en [`docs/analisis_tres_anios.md`](docs/analisis_tres_anios.md).

Para volver a ejecutar los notebooks completos desde la terminal:

```bash
docker compose exec lab jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb
docker compose exec lab jupyter nbconvert --to notebook --execute --inplace notebooks/evolucion_2024_2026.ipynb
```

### Hallazgos principales del analisis

(2026 solo tiene enero a agosto; las comparaciones entre anios usan los meses
comunes a todos los anios.)

1. **Yellow tuvo su pico en 2025 y green cae cada anio**: yellow crece 19.6 % de
   2024 a 2025 y cae 5.9 % en 2026; green cae 10.3 % y 15.3 %.
2. **El precio yellow subio desde diciembre de 2025**: la tarifa promedio de
   2026 es 8.8 % mayor (21.3 frente a 19.6 USD en los mismos meses).
3. **Cambio en la mezcla de pagos en 2025**: los viajes yellow con forma de pago
   "flexible / no registrada" pasan de 9.9 % a 23.8 % y 26.0 %. La propina
   promedio baja de 3.34 a 2.88 USD, pero con tarjeta se mantiene (~22 % de la
   tarifa).
4. **Yellow y green son servicios distintos**: green es 1.1 a 1.6 % del volumen,
   circula a mayor velocidad promedio (17.2 vs 11.3 mph) y baja el fin de semana.
5. **Calidad de datos**: un proveedor que aparece a fines de 2024 (`VendorID` 7)
   registra todos sus viajes con duracion cero (536 mil en 2025 y 367 mil en
   2026), y el `VendorID` 2 registra en 2025 1.9 M de tarifas negativas con total
   positivo. Ver [`docs/data_quality.md`](docs/data_quality.md).
6. **El peaje de congestion** aparece en los datos desde enero de 2025 (7 de cada
   10 viajes yellow), pero la velocidad dentro de Manhattan no cambia.

## Como reproducir los benchmarks

```bash
docker compose exec lab python scripts/benchmark.py
```

El script construye, para cada conjunto de anios acumulado (2024, 2024+2025,
2024+2025+2026), una tabla DuckDB y una vista sobre los Parquet con el mismo SELECT, ejecuta
las consultas de `sql/benchmark_queries.sql` en ambas, verifica que los
resultados coincidan y guarda los tiempos en `docs/benchmark_results.csv`. Tarda
unos minutos porque materializa la tabla para cada conjunto. La metodologia,
la tabla de resultados y la discusion estan en [`docs/benchmark.md`](docs/benchmark.md).

Resultado resumido: sobre 121 millones de filas, la tabla materializada responde
entre 1.2x y 7x mas rapido que Parquet en la mayoria de las consultas (empata en
percentiles y es mas lenta en la consulta que solo usa metadatos), y crearla
tarda 7.8 s; para exploracion puntual conviene consultar Parquet y para
analisis repetidos, como el tablero, conviene la tabla.

## Pruebas

```bash
docker compose exec lab python -m unittest tests.test_download_data tests.test_database tests.test_indicators
```

## Indicadores y tablero

Los 15 indicadores del tablero estan en `sql/indicators/`, un archivo SQL por
indicador con su pregunta, definicion, visualizacion y posicion en el tablero en
el encabezado. Las preguntas, la justificacion de cada indicador y su
interpretacion estan en [`docs/indicadores.md`](docs/indicadores.md).

```bash
docker compose exec lab python scripts/indicators.py        # resultados -> docs/dashboard/resultados/*.csv
docker compose exec lab python scripts/render_dashboard.py  # imagen -> docs/dashboard/tablero.png
docker compose exec lab python scripts/setup_dashboard.py   # tablero en Metabase
```

`scripts/setup_dashboard.py` configura Metabase por API: si todavia no tiene
administrador lo crea con `MB_ADMIN_EMAIL` y `MB_ADMIN_PASSWORD` (por defecto
`admin@lab8.local` / `Lab8-duckdb`, solo para uso local; se pueden cambiar con
`docker compose exec -e MB_ADMIN_EMAIL=... -e MB_ADMIN_PASSWORD=... lab ...`),
registra `data/processed/taxi.duckdb` en solo lectura, crea una pregunta por
indicador y el tablero "Taxis NYC - Indicadores" en la coleccion "Lab 8 - Taxis
NYC". Se puede volver a ejecutar: actualiza en lugar de duplicar. Despues abra
<http://localhost:3000> e inicie sesion con esas credenciales. La opcion
`--public` agrega un enlace publico de solo lectura al tablero.

## Como generar los resultados principales

Desde un clon nuevo, con Docker en ejecucion:

```bash
docker compose up --build -d                                        # 1. ambiente
docker compose exec lab python scripts/download_data.py             # 2. datos (2024-2026 + zonas)
docker compose exec -T lab python scripts/run_sql.py sql/exploration.sql             # 3. exploracion Parquet
docker compose exec lab python scripts/create_database.py           # 4. tabla trips + zones
docker compose exec -T lab python scripts/run_sql.py sql/analysis.sql --db data/processed/taxi.duckdb
docker compose exec lab jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb
docker compose exec lab jupyter nbconvert --to notebook --execute --inplace notebooks/evolucion_2024_2026.ipynb
docker compose exec lab python scripts/benchmark.py                 # 5. benchmark -> docs/benchmark_results.csv
docker compose exec lab python scripts/indicators.py                # 6. indicadores
docker compose exec lab python scripts/render_dashboard.py
docker compose exec lab python scripts/setup_dashboard.py           # 7. tablero en Metabase
```

| Resultado | Donde |
| --- | --- |
| Exploracion directa sobre Parquet | [`docs/exploration_queries.md`](docs/exploration_queries.md), [`docs/data_quality.md`](docs/data_quality.md) |
| Analisis exploratorio | `notebooks/analysis.ipynb`, `sql/analysis.sql` |
| Incorporacion de 2024 y 2025 | [`docs/incorporacion_2024.md`](docs/incorporacion_2024.md), [`docs/incorporacion_2025.md`](docs/incorporacion_2025.md) |
| Benchmark Parquet vs tabla | [`docs/benchmark.md`](docs/benchmark.md), `docs/benchmark_results.csv` |
| Indicadores y tablero | [`docs/indicadores.md`](docs/indicadores.md), `docs/dashboard/` |
| Analisis de los tres anios | [`docs/analisis_tres_anios.md`](docs/analisis_tres_anios.md), `notebooks/evolucion_2024_2026.ipynb` |
| Discusion final | [`docs/discusion.md`](docs/discusion.md) |

Los numeros documentados corresponden a los datos publicados al 2 de octubre de
2026 (2026 hasta agosto); cuando la TLC publique meses nuevos, los mismos
comandos los incorporan y los resultados cambian.

## Por que usar un ambiente reproducible

Docker fija la version de Python y `requirements.txt` fija las versiones de
DuckDB, JupyterLab y las bibliotecas de analisis. De esta forma, cada integrante
y el evaluador ejecutan el mismo software, con las mismas rutas internas y sin
depender de paquetes instalados globalmente en su computadora. Los datos se
mantienen fuera de Git, pero los scripts y consultas necesarios para volver a
obtener y analizar esos datos si se versionan. Esta separacion facilita repetir
los resultados, diagnosticar diferencias y actualizar el flujo cuando la TLC
publique nuevos meses.
