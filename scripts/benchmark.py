#!/usr/bin/env python3
"""Compara consultar los Parquet directamente contra una tabla DuckDB.

Para cada conjunto de datos (anios descargados, acumulados de menor a mayor)
y cada consulta de sql/benchmark_queries.sql:

  1. parquet : vista `trips` sobre los archivos Parquet (mismo SELECT que
               sql/create_tables.sql), en una conexion en memoria;
  2. tabla   : tabla `trips` materializada en una base DuckDB construida solo
               con los anios de ese conjunto.

El texto de la consulta es identico en ambos casos. Cada consulta se ejecuta
una vez sin medir (calentamiento) y luego --repeat veces midiendo; se registra
la mediana. Tambien se mide el costo de materializar la tabla y se verifica
que ambas estrategias devuelvan el mismo resultado.

Uso (desde la raiz del proyecto):
    python scripts/benchmark.py
    python scripts/benchmark.py --repeat 5 --output docs/benchmark_results.csv

Salida: docs/benchmark_results.csv (una fila por consulta y conjunto).
"""

import argparse
import csv
import math
import re
import statistics
import sys
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_database  # noqa: E402

ARCHIVO_CONSULTAS = Path("sql/benchmark_queries.sql")
SALIDA_POR_DEFECTO = Path("docs/benchmark_results.csv")
BASE_TEMPORAL = Path("data/processed/benchmark_tmp.duckdb")
CAMPOS = [
    "query_id", "description", "dataset", "years", "rows",
    "parquet_seconds", "table_seconds", "difference_seconds", "speedup",
    "same_result",
]


def cargar_consultas(ruta: Path = ARCHIVO_CONSULTAS) -> list[tuple[str, str, str]]:
    """Lee (id, descripcion, sql) de las consultas marcadas con '-- @query'."""
    consultas = []
    marca = re.compile(r"^--\s*@query\s+(\S+)\s*\|\s*(.+)$")
    actual = None
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        m = marca.match(linea)
        if m:
            actual = [m.group(1), m.group(2).strip(), []]
            consultas.append(actual)
        elif actual is not None:
            actual[2].append(linea)
    resultado = []
    for id_, descripcion, lineas in consultas:
        sql = "\n".join(lineas).strip()
        if not sql.endswith(";"):
            raise ValueError(f"la consulta {id_} no termina en ';'")
        resultado.append((id_, descripcion, sql))
    return resultado


def anios_descargados() -> list[int]:
    """Anios con Parquet en data/raw para ambos tipos de taxi."""
    por_tipo = []
    for tipo in create_database.TIPOS_TAXI:
        carpetas = (create_database.DIR_RAW / tipo).glob("*")
        por_tipo.append({
            int(c.name) for c in carpetas
            if c.name.isdigit() and any(c.glob("*.parquet"))
        })
    return sorted(set.intersection(*por_tipo))


def conjuntos(anios: list[int]) -> list[list[int]]:
    """Conjuntos acumulados: [a1], [a1, a2], [a1, a2, a3], ..."""
    return [anios[: i + 1] for i in range(len(anios))]


def medir(con, sql: str, repeticiones: int) -> tuple[float, list]:
    """Mediana de `repeticiones` ejecuciones (tras un calentamiento) y el resultado."""
    resultado = con.execute(sql).fetchall()
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        con.execute(sql).fetchall()
        tiempos.append(time.perf_counter() - inicio)
    return statistics.median(tiempos), resultado


def iguales(a: list, b: list) -> bool:
    """Compara resultados tolerando diferencias de redondeo en decimales."""
    if len(a) != len(b):
        return False
    for fila_a, fila_b in zip(a, b):
        if len(fila_a) != len(fila_b):
            return False
        for x, y in zip(fila_a, fila_b):
            if isinstance(x, float) or isinstance(y, float):
                if x is None or y is None or not math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-6):
                    return False
            elif x != y:
                return False
    return True


def etiqueta(anios: list[int]) -> str:
    return "+".join(str(a) for a in anios)


def ejecutar(repeticiones: int) -> list[dict]:
    consultas = cargar_consultas()
    anios = anios_descargados()
    if not anios:
        raise SystemExit("No hay datos descargados. Ejecute primero scripts/download_data.py.")

    filas = []
    for subconjunto in conjuntos(anios):
        nombre = etiqueta(subconjunto)
        print(f"\n=== Conjunto de datos: {nombre} ===")

        # Estrategia 1: Parquet directo, a traves de una vista con el mismo SELECT.
        con_parquet = duckdb.connect()
        con_parquet.execute(
            f"CREATE VIEW trips AS {create_database.select_viajes(subconjunto)}"
        )
        total = con_parquet.execute("SELECT count(*) FROM trips").fetchone()[0]

        # Estrategia 2: tabla materializada solo con estos anios.
        BASE_TEMPORAL.parent.mkdir(parents=True, exist_ok=True)
        BASE_TEMPORAL.unlink(missing_ok=True)
        con_tabla = duckdb.connect(str(BASE_TEMPORAL))
        inicio = time.perf_counter()
        con_tabla.execute(create_database.sentencia_create(subconjunto))
        carga = time.perf_counter() - inicio
        print(f"  materializar tabla: {carga:.2f} s ({total:,} filas)")
        filas.append({
            "query_id": "materializacion",
            "description": "Costo unico de CREATE TABLE trips a partir de los Parquet",
            "dataset": nombre, "years": len(subconjunto), "rows": total,
            "parquet_seconds": "", "table_seconds": round(carga, 4),
            "difference_seconds": "", "speedup": "", "same_result": "",
        })

        try:
            for id_, descripcion, sql in consultas:
                t_parquet, r_parquet = medir(con_parquet, sql, repeticiones)
                t_tabla, r_tabla = medir(con_tabla, sql, repeticiones)
                mismo = iguales(r_parquet, r_tabla)
                filas.append({
                    "query_id": id_, "description": descripcion,
                    "dataset": nombre, "years": len(subconjunto), "rows": total,
                    "parquet_seconds": round(t_parquet, 4),
                    "table_seconds": round(t_tabla, 4),
                    "difference_seconds": round(t_parquet - t_tabla, 4),
                    "speedup": round(t_parquet / t_tabla, 2) if t_tabla > 0 else "",
                    "same_result": mismo,
                })
                aviso = "" if mismo else "  <-- RESULTADOS DISTINTOS"
                print(
                    f"  {id_:<24} parquet {t_parquet:8.3f} s | "
                    f"tabla {t_tabla:8.3f} s | x{t_parquet / max(t_tabla, 1e-9):5.1f}{aviso}"
                )
        finally:
            con_parquet.close()
            con_tabla.close()
            BASE_TEMPORAL.unlink(missing_ok=True)
    return filas


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Parquet vs tabla DuckDB.")
    parser.add_argument("--repeat", type=int, default=3, help="repeticiones medidas por consulta")
    parser.add_argument("--output", type=Path, default=SALIDA_POR_DEFECTO)
    argumentos = parser.parse_args()

    filas = ejecutar(argumentos.repeat)

    argumentos.output.parent.mkdir(parents=True, exist_ok=True)
    with argumentos.output.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"\nResultados guardados en {argumentos.output}")

    distintos = [f for f in filas if f["same_result"] is False]
    if distintos:
        print("ADVERTENCIA: hay consultas con resultados distintos entre estrategias.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
