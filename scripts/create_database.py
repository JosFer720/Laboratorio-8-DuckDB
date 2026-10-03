#!/usr/bin/env python3
"""Materializa los Parquet descargados en una base DuckDB.

Lee sql/create_tables.sql y lo ejecuta sobre los archivos de data/raw/,
generando data/processed/taxi.duckdb con la tabla `trips`. Si ya se descargo
el catalogo de zonas (data/raw/zones/taxi_zone_lookup.csv), sql/create_zones.sql
agrega ademas la tabla `zones`.

Uso (desde la raiz del proyecto):
    python scripts/create_database.py                       # todos los anios descargados
    python scripts/create_database.py --year 2026           # solo algunos anios
    python scripts/create_database.py --output ruta.duckdb

La base se construye en un archivo temporal y reemplaza a la anterior solo si
la construccion termina bien, de modo que una falla no deja una base a medias.
Como el patron por defecto es data/raw/<tipo>/*/*.parquet, un anio nuevo entra
a la tabla con solo descargarlo y volver a ejecutar este script.
"""

import argparse
import glob
import re
import sys
import time
from pathlib import Path
from string import Template

import duckdb

DIR_RAW = Path("data/raw")
BASE_POR_DEFECTO = Path("data/processed/taxi.duckdb")
ARCHIVO_SQL = Path("sql/create_tables.sql")
ARCHIVO_SQL_ZONAS = Path("sql/create_zones.sql")
TIPOS_TAXI = ("yellow", "green")


def patrones(tipo: str, anios=None) -> list[str]:
    """Patrones glob de los Parquet de un tipo de taxi (todos los anios si `anios` es None)."""
    if not anios:
        return [f"{DIR_RAW.as_posix()}/{tipo}/*/*.parquet"]
    return [f"{DIR_RAW.as_posix()}/{tipo}/{anio}/*.parquet" for anio in sorted(anios)]


def literal_lista(valores: list[str]) -> str:
    """Convierte una lista de rutas en un literal de lista SQL."""
    return "[" + ", ".join("'" + v.replace("'", "''") + "'" for v in valores) + "]"


def sentencia_create(anios=None) -> str:
    """Sentencia CREATE TABLE de sql/create_tables.sql con las rutas sustituidas."""
    texto = Template(ARCHIVO_SQL.read_text(encoding="utf-8"))
    return texto.substitute(
        yellow_files=literal_lista(patrones("yellow", anios)),
        green_files=literal_lista(patrones("green", anios)),
    )


def select_viajes(anios=None) -> str:
    """El SELECT que define `trips`, sin el CREATE TABLE.

    scripts/benchmark.py lo usa para crear una vista equivalente sobre los
    Parquet, de modo que ambas estrategias consulten las mismas columnas.
    """
    sentencia = sentencia_create(anios)
    cuerpo = re.sub(r"^.*?CREATE TABLE trips AS", "", sentencia, flags=re.DOTALL)
    return cuerpo.strip().rstrip(";")


def archivo_zonas() -> Path:
    return DIR_RAW / "zones" / "taxi_zone_lookup.csv"


def sentencia_zonas() -> str:
    """Sentencia CREATE TABLE zones de sql/create_zones.sql con la ruta del CSV."""
    texto = Template(ARCHIVO_SQL_ZONAS.read_text(encoding="utf-8"))
    return texto.substitute(zones_file=literal_lista([archivo_zonas().as_posix()]))


def validar_archivos(anios=None) -> None:
    """Falla con un mensaje claro si no hay Parquet para algun tipo de taxi."""
    for tipo in TIPOS_TAXI:
        if not any(glob.glob(patron) for patron in patrones(tipo, anios)):
            raise SystemExit(
                f"No se encontraron archivos para {tipo}. "
                "Ejecute primero scripts/download_data.py."
            )


def construir(salida: Path, anios=None) -> None:
    validar_archivos(anios)
    salida.parent.mkdir(parents=True, exist_ok=True)
    temporal = salida.with_name(salida.name + ".tmp")
    temporal.unlink(missing_ok=True)

    inicio = time.perf_counter()
    try:
        con = duckdb.connect(str(temporal))
        try:
            con.execute(sentencia_create(anios))
            filas = con.execute("SELECT count(*) FROM trips").fetchone()[0]
            zonas = archivo_zonas().exists()
            if zonas:
                con.execute(sentencia_zonas())
        finally:
            con.close()
        temporal.replace(salida)
    except BaseException:
        temporal.unlink(missing_ok=True)
        raise
    segundos = time.perf_counter() - inicio

    print(f"Base creada: {salida}")
    print(f"  filas en trips : {filas:,}")
    print(f"  tamano         : {salida.stat().st_size / 1024 ** 2:,.1f} MiB")
    print(f"  tiempo         : {segundos:,.1f} s")
    if not zonas:
        print("  (sin tabla zones: ejecute scripts/download_data.py para obtener el catalogo)")

    con = duckdb.connect(str(salida), read_only=True)
    try:
        print("\nResumen por tipo de taxi y anio:")
        print(
            con.execute(
                "SELECT taxi_type, year, count(*) AS viajes FROM trips "
                "GROUP BY ALL ORDER BY ALL"
            ).fetchdf().to_string(index=False)
        )
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Crea la base DuckDB con los viajes de taxi.")
    parser.add_argument(
        "--year", type=int, action="append",
        help="anio a incluir; se puede repetir (por defecto: todos los descargados)",
    )
    parser.add_argument(
        "--output", type=Path, default=BASE_POR_DEFECTO,
        help=f"base de salida (por defecto: {BASE_POR_DEFECTO})",
    )
    argumentos = parser.parse_args()
    construir(argumentos.output, argumentos.year)
    return 0


if __name__ == "__main__":
    sys.exit(main())
