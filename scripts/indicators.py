#!/usr/bin/env python3
"""Calcula los indicadores del tablero a partir de la base DuckDB.

Cada archivo de sql/indicators/ contiene una consulta sobre las tablas `trips`
y `zones` de data/processed/taxi.duckdb, precedida por un encabezado de
comentarios con sus metadatos:

    -- @title     titulo de la tarjeta
    -- @question  pregunta de analisis que responde
    -- @display   scalar | line | bar | row | table (tipo de visualizacion)
    -- @x         columna del eje x (graficos)
    -- @series    columna que separa las series (opcional)
    -- @y         columna del valor (graficos)
    -- @stack     normalized (opcional, barras apiladas al 100 %)
    -- @colors    valor=#hex,... color fijo por serie (opcional)
    -- @layout    columna,fila,ancho,alto en la grilla de 24 columnas del tablero

Este script ejecuta todas las consultas, imprime sus resultados y los guarda
en docs/dashboard/resultados/<archivo>.csv. scripts/setup_dashboard.py usa los
mismos archivos para crear el tablero en Metabase, de modo que el SQL de cada
indicador vive en un solo lugar.

Uso (desde la raiz del proyecto):
    python scripts/indicators.py
    python scripts/indicators.py --db data/processed/taxi.duckdb --output docs/dashboard/resultados
"""

import argparse
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import pandas as pd

DIR_INDICADORES = Path("sql/indicators")
BASE_POR_DEFECTO = Path("data/processed/taxi.duckdb")
SALIDA_POR_DEFECTO = Path("docs/dashboard/resultados")
DISPLAYS = {"scalar", "line", "bar", "row", "table"}
ALTO_ENCABEZADO = 4  # filas de la grilla que ocupa el encabezado del tablero


@dataclass
class Indicador:
    archivo: Path
    titulo: str
    pregunta: str
    display: str
    sql: str
    x: str | None = None
    series: str | None = None
    y: str | None = None
    stack: str | None = None
    colores: dict[str, str] = field(default_factory=dict)
    layout: tuple[int, int, int, int] = (0, 0, 12, 6)
    descripcion: str = ""

    @property
    def nombre(self) -> str:
        return self.archivo.stem


def leer_indicador(ruta: Path) -> Indicador:
    """Separa el encabezado de metadatos (-- @clave valor) del SQL de un indicador."""
    meta: dict[str, str] = {}
    descripcion = []
    texto = ruta.read_text(encoding="utf-8")
    for linea in texto.splitlines():
        if not linea.startswith("--"):
            break
        contenido = linea[2:].strip()
        m = re.match(r"^@(\w+)\s+(.+)$", contenido)
        if m:
            meta[m.group(1)] = m.group(2).strip()
        elif contenido:
            descripcion.append(contenido)

    for clave in ("title", "question", "display", "layout"):
        if clave not in meta:
            raise ValueError(f"{ruta}: falta '-- @{clave}' en el encabezado")
    if meta["display"] not in DISPLAYS:
        raise ValueError(f"{ruta}: display no soportado: {meta['display']!r}")
    if meta["display"] in {"line", "bar", "row"} and not {"x", "y"} <= meta.keys():
        raise ValueError(f"{ruta}: los graficos requieren '-- @x' y '-- @y'")

    layout = tuple(int(v) for v in meta["layout"].split(","))
    if len(layout) != 4:
        raise ValueError(f"{ruta}: @layout debe ser columna,fila,ancho,alto")

    colores = {}
    if "colors" in meta:
        for par in meta["colors"].split(","):
            valor, color = par.rsplit("=", 1)
            colores[valor.strip()] = color.strip()

    sql = texto.strip()
    if not sql.endswith(";"):
        raise ValueError(f"{ruta}: la consulta debe terminar en ';'")

    return Indicador(
        archivo=ruta,
        titulo=meta["title"],
        pregunta=meta["question"],
        display=meta["display"],
        sql=sql,
        x=meta.get("x"),
        series=meta.get("series"),
        y=meta.get("y"),
        stack=meta.get("stack"),
        colores=colores,
        layout=layout,
        descripcion=" ".join(descripcion),
    )


def cargar_indicadores(directorio: Path = DIR_INDICADORES) -> list[Indicador]:
    rutas = sorted(directorio.glob("*.sql"))
    if not rutas:
        raise SystemExit(f"No hay consultas en {directorio}")
    return [leer_indicador(ruta) for ruta in rutas]


def main() -> int:
    parser = argparse.ArgumentParser(description="Calcula los indicadores del tablero.")
    parser.add_argument("--db", type=Path, default=BASE_POR_DEFECTO)
    parser.add_argument("--output", type=Path, default=SALIDA_POR_DEFECTO)
    parser.add_argument("--max-rows", type=int, default=15, help="filas a imprimir por indicador")
    argumentos = parser.parse_args()

    if not argumentos.db.exists():
        raise SystemExit(f"No existe {argumentos.db}. Ejecute primero scripts/create_database.py.")

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    indicadores = cargar_indicadores()
    argumentos.output.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(argumentos.db), read_only=True)
    try:
        for indicador in indicadores:
            inicio = time.perf_counter()
            resultado = con.execute(indicador.sql).fetchdf()
            segundos = time.perf_counter() - inicio
            resultado.to_csv(argumentos.output / f"{indicador.nombre}.csv", index=False)
            print(f"\n=== {indicador.nombre}: {indicador.titulo} ({segundos:.2f} s)")
            print(f"    {indicador.pregunta}")
            print(resultado.head(argumentos.max_rows).to_string(index=False))
            if len(resultado) > argumentos.max_rows:
                print(f"... ({len(resultado)} filas en total)")
    finally:
        con.close()

    print(f"\n{len(indicadores)} indicadores guardados en {argumentos.output}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
