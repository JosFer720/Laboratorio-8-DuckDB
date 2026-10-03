#!/usr/bin/env python3
"""Ejecuta un archivo .sql con DuckDB e imprime el resultado de cada consulta.

Uso (desde la raiz del proyecto):
    python scripts/run_sql.py sql/exploration.sql
    python scripts/run_sql.py sql/analysis.sql --db data/processed/taxi.duckdb

Sin --db se usa una base en memoria, suficiente para las consultas que leen
los Parquet directamente. Con --db la base se abre en modo solo lectura.
"""

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta un archivo SQL con DuckDB.")
    parser.add_argument("sql", type=Path, help="archivo .sql a ejecutar")
    parser.add_argument("--db", type=Path, help="base DuckDB (solo lectura); por defecto en memoria")
    parser.add_argument("--max-rows", type=int, default=60, help="filas a imprimir por consulta")
    argumentos = parser.parse_args()

    if argumentos.db is not None and not argumentos.db.exists():
        raise SystemExit(
            f"No existe {argumentos.db}. Ejecute primero scripts/create_database.py."
        )

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 50)
    pd.set_option("display.max_colwidth", 60)

    con = (
        duckdb.connect(str(argumentos.db), read_only=True)
        if argumentos.db
        else duckdb.connect()
    )
    try:
        sentencias = duckdb.extract_statements(argumentos.sql.read_text(encoding="utf-8"))
        for numero, sentencia in enumerate(sentencias, start=1):
            primera = next(
                (l.strip() for l in sentencia.query.splitlines() if l.strip()), ""
            )
            print(f"\n--- consulta {numero}/{len(sentencias)}: {primera[:80]}")
            resultado = con.execute(sentencia.query).fetchdf()
            print(resultado.head(argumentos.max_rows).to_string(index=False))
            if len(resultado) > argumentos.max_rows:
                print(f"... ({len(resultado)} filas en total)")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
