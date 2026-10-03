# Lab 8 - DuckDB

Laboratorio 8 del curso **CC3084 - Data Science** (Universidad del Valle de
Guatemala, Ciclo 2, 2026).

Flujo reproducible con DuckDB para descargar, consultar, transformar y analizar
los viajes de taxis amarillos (*yellow*) y verdes (*green*) de Nueva York
publicados por la NYC TLC. El flujo crece de forma incremental: se descargan los
archivos Parquet de cada anio, se consultan directamente, se materializan en una
base DuckDB y se comparan ambas estrategias de acceso.

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
|   +-- raw/            Parquet originales: data/raw/<tipo>/<anio>/
|   +-- processed/      base materializada: taxi.duckdb
+-- notebooks/          analysis.ipynb
+-- scripts/
|   +-- download_data.py     descarga incremental desde la NYC TLC
|   +-- create_database.py   crea data/processed/taxi.duckdb
|   +-- benchmark.py         compara Parquet directo vs tabla DuckDB
|   +-- run_sql.py           ejecuta un archivo .sql e imprime los resultados
+-- sql/
|   +-- exploration.sql        consultas directas sobre Parquet
|   +-- analysis.sql           analisis exploratorio sobre la tabla trips
|   +-- create_tables.sql      definicion de la tabla trips
|   +-- benchmark_queries.sql  consultas del benchmark
+-- docs/               documentacion de consultas, calidad de datos y benchmark
+-- tests/              pruebas de los scripts
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
  sobre Parquet.
- `docs/`: resultados, evidencia y documentacion complementaria.

## Requisitos

- Docker, con Docker Compose
- Git

La primera construccion del ambiente descarga varios cientos de MB y puede
tardar algunos minutos.

Considere el espacio en disco: las imagenes de Docker ocupan unos 3 GB, los
Parquet de 2024 y 2026 unos 1.2 GB (mas los de 2025 cuando se incorpore) y la
base materializada unos 2 GB. Se recomienda tener al menos 10 GB libres.

## Datos

`scripts/download_data.py` descarga los archivos Parquet publicados por la TLC
(`--help` muestra las opciones disponibles). Se guardan en
`data/raw/<tipo>/<anio>/`. Anios soportados actualmente: 2024 y 2026.

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
docker compose exec lab python scripts/download_data.py --year 2024 --year 2026 --taxi yellow
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
detectar meses vacios. La incorporacion de 2024 esta documentada en
[`docs/incorporacion_2024.md`](docs/incorporacion_2024.md).

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
  `year`, `month` y `duration_minutes`. Acepta `--year` para limitar los anios.
  Para agregar un anio nuevo basta con descargarlo y volver a ejecutar el script.
- **Analisis exploratorio** (`sql/analysis.sql` y `notebooks/analysis.ipynb`):
  preguntas sobre volumen mensual, distancia y tarifa, diferencias entre yellow
  y green, actividad por hora, formas de pago y valores atipicos, con sus
  hallazgos. El notebook se abre desde JupyterLab
  (<http://localhost:8888/lab>) y se puede volver a ejecutar completo.

### Hallazgos principales del analisis

(2026 solo tiene enero a agosto; las comparaciones entre anios usan esos meses.)

1. **Yellow crece y green cae**: yellow pasa de 26.4 M a 29.7 M de viajes
   (+12.6 %) y green de 443 mil a 337 mil (-24.0 %).
2. **Cambio en la mezcla de pagos**: los viajes yellow con forma de pago
   "flexible / no registrada" pasan de 9.9 % a 26.0 %. La propina promedio baja
   de 3.34 a 2.88 USD, pero con tarjeta se mantiene (4.30 vs 4.26 USD).
3. **Yellow y green son servicios distintos**: green es 1.4 % del volumen,
   circula a mayor velocidad promedio (15.6 vs 11.2 mph) y baja el fin de semana.
4. **Calidad de datos**: un proveedor que aparece en 2026 (`VendorID` 7) registra
   367 mil viajes yellow con duracion cero, lo que multiplica por 27 las
   duraciones invalidas respecto a 2024.

## Como reproducir los benchmarks

```bash
docker compose exec lab python scripts/benchmark.py
```

El script construye, para cada conjunto de anios acumulado (2024, 2024+2026),
una tabla DuckDB y una vista sobre los Parquet con el mismo SELECT, ejecuta
las consultas de `sql/benchmark_queries.sql` en ambas, verifica que los
resultados coincidan y guarda los tiempos en `docs/benchmark_results.csv`. Tarda
unos minutos porque materializa la tabla para cada conjunto. La metodologia,
la tabla de resultados y la discusion estan en [`docs/benchmark.md`](docs/benchmark.md).

Resultado resumido: sobre 72 millones de filas, la tabla materializada responde
entre 1x y 30x mas rapido que Parquet segun la consulta, pero crear la tabla
tarda unos 105 s; para exploracion puntual conviene consultar Parquet y para
analisis repetidos conviene la tabla.

## Pruebas

```bash
docker compose exec lab python -m unittest tests.test_download_data tests.test_database
```

## Como generar los resultados principales

<!-- TODO: indicadores, tablero y analisis final -->

## Por que usar un ambiente reproducible

Docker fija la version de Python y `requirements.txt` fija las versiones de
DuckDB, JupyterLab y las bibliotecas de analisis. De esta forma, cada integrante
y el evaluador ejecutan el mismo software, con las mismas rutas internas y sin
depender de paquetes instalados globalmente en su computadora. Los datos se
mantienen fuera de Git, pero los scripts y consultas necesarios para volver a
obtener y analizar esos datos si se versionan. Esta separacion facilita repetir
los resultados, diagnosticar diferencias y actualizar el flujo cuando la TLC
publique nuevos meses.
