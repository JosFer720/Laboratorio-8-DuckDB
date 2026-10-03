# Lab 8 - DuckDB

Repositorio base del laboratorio 8 del curso **CC3084 - Data Science**
(Universidad del Valle de Guatemala, Ciclo 2, 2026).

Este es el repositorio **proporcionado por el docente**. Contiene la estructura
del proyecto, el ambiente de ejecucion basado en Docker y un script que descarga
los datos de **2026**. Todo lo demas debe ser construido por cada equipo.

## Trabajo con fork

El laboratorio se desarrolla y se entrega sobre un **fork** de este repositorio.
No se trabaja directamente sobre el repositorio del docente.

1. Realice un fork de este repositorio:
   <https://github.com/menene/duckdb>

2. Clone **su propio fork** (no el del docente):

   ```bash
   git clone https://github.com/<su-usuario>/duckdb.git
   cd duckdb
   ```

3. Opcional, para recibir correcciones publicadas por el docente:

   ```bash
   git remote add upstream https://github.com/menene/duckdb.git
   git fetch upstream
   ```

Realice commits frecuentes y descriptivos: el historial del repositorio es parte
de la evaluacion. **La entrega del laboratorio es la URL de su fork.**

## Estructura

```text
duckdb/
|
+-- data/
|   +-- raw/
|   +-- processed/
|
+-- notebooks/
|
+-- scripts/
|
+-- sql/
|
+-- docs/
|
+-- Dockerfile
+-- metabase.Dockerfile
+-- docker-compose.yml
+-- README.md
```

Cada directorio separa una responsabilidad del flujo:

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

Considere el espacio en disco: las imagenes de Docker ocupan unos 3 GB y los
datos de los tres anios del laboratorio superan 1.5 GB, a los que se suma la
base materializada del Ejercicio 6. Se recomienda tener al menos 10 GB libres.

## Datos

El repositorio incluye `scripts/download_data.py`, que descarga los archivos de
2026 publicados por la TLC (`--help` muestra las opciones disponibles). Los
archivos se guardan en `data/raw/<tipo>/<anio>/`.

La TLC publica cada mes con varias semanas de atraso, por lo que los ultimos
meses de 2026 todavia no existen. El script consulta al servidor que meses estan
publicados, de modo que vuelve a ejecutarse sin problema conforme aparezcan
nuevos archivos.

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

## Material a entregar

Al finalizar, su fork debe contener:

- el codigo fuente modificado y los scripts de descarga;
- las consultas SQL desarrolladas;
- el notebook o notebooks utilizados;
- la documentacion de las consultas;
- los scripts utilizados para los benchmarks;
- el codigo de los indicadores y visualizaciones;
- el tablero o la evidencia del tablero desarrollado;
- este `README.md`, completado segun la siguiente seccion.

Los archivos de datos descargados **no** deben incluirse.

---

# Documentacion del equipo

Las siguientes secciones deben ser completadas por cada equipo. El README final
debe permitir que una persona que no participo en el desarrollo pueda levantar el
ambiente, descargar los datos, ejecutar el analisis, reproducir los benchmarks y
generar los resultados principales.

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

Las carpetas `data/`, `notebooks/`, `scripts/`, `sql/` y `docs/` se montan bajo
`/workspace` dentro del contenedor `lab`. Por eso, los cambios y archivos
descargados quedan disponibles tanto en el host como en Docker. Para detener
los servicios sin borrar datos:

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
docker compose exec lab python scripts/download_data.py --year 2026
```

Si instaló localmente las mismas dependencias de `requirements.txt`, el comando
equivalente es:

```bash
python scripts/download_data.py --year 2026
```

El script descarga Yellow Taxi y Green Taxi en
`data/raw/<tipo>/2026/`. Los meses que todavia no haya publicado la TLC se
reportan y se omiten. Si un archivo no vacio ya existe, una nueva ejecucion lo
conserva y no vuelve a descargarlo; esto permite actualizar el conjunto de
datos incrementalmente.

## Como ejecutar el analisis

Las consultas iniciales estan en `sql/exploration.sql` y leen los archivos
Parquet directamente, sin importarlos antes a una base persistente. Ejecute
todo el archivo desde la raiz del proyecto con DuckDB para Python:

```bash
docker compose exec -T lab python -c "from pathlib import Path; import duckdb; con=duckdb.connect(); sql=Path('sql/exploration.sql').read_text(encoding='utf-8'); [print(con.execute(query).fetchdf().to_string(index=False)) for query in sql.split(';') if query.strip()]"
```

Tambien puede abrir `sql/exploration.sql` desde JupyterLab y ejecutar sus
consultas individualmente con `duckdb.sql(...)`. Las rutas relativas funcionan
porque el directorio de trabajo del contenedor es `/workspace`.

Antes de consultar, confirme que existen archivos en ambas rutas:

```text
data/raw/yellow/2026/*.parquet
data/raw/green/2026/*.parquet
```

La exploracion revisa archivos disponibles, volumen de registros, esquema,
muestras y problemas iniciales de calidad como nulos, distancias cero, montos
negativos, duraciones invalidas y valores atipicos. Los resultados observados
para los meses disponibles estan documentados en
[`docs/data_quality_2026.md`](docs/data_quality_2026.md).

## Como reproducir los benchmarks

<!-- TODO (Ejercicio 6) -->

## Como generar los resultados principales

<!-- TODO -->

## Por que usar un ambiente reproducible

Docker fija la version de Python y `requirements.txt` fija las versiones de
DuckDB, JupyterLab y las bibliotecas de analisis. De esta forma, cada integrante
y el evaluador ejecutan el mismo software, con las mismas rutas internas y sin
depender de paquetes instalados globalmente en su computadora. Los datos se
mantienen fuera de Git, pero los scripts y consultas necesarios para volver a
obtener y analizar esos datos si se versionan. Esta separacion facilita repetir
los resultados, diagnosticar diferencias y actualizar el flujo cuando la TLC
publique nuevos meses.
