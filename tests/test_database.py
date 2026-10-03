import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

from scripts import benchmark, create_database


def escribir_parquet(ruta: Path, tipo: str, filas: int) -> None:
    """Crea un Parquet minimo con las columnas que usa create_tables.sql."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    prefijo = "tpep" if tipo == "yellow" else "lpep"
    con = duckdb.connect()
    con.execute(
        f"""
        COPY (
            SELECT
                1::INTEGER AS VendorID,
                TIMESTAMP '2024-01-15 10:00:00' AS {prefijo}_pickup_datetime,
                TIMESTAMP '2024-01-15 10:30:00' AS {prefijo}_dropoff_datetime,
                1::BIGINT AS passenger_count,
                2.5::DOUBLE AS trip_distance,
                10::INTEGER AS PULocationID,
                20::INTEGER AS DOLocationID,
                1::BIGINT AS payment_type,
                12.0::DOUBLE AS fare_amount,
                2.0::DOUBLE AS tip_amount,
                0.0::DOUBLE AS tolls_amount,
                15.0::DOUBLE AS total_amount
            FROM range({filas})
        ) TO '{ruta.as_posix()}' (FORMAT parquet)
        """
    )
    con.close()


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raw = Path(self._tmp.name) / "raw"
        escribir_parquet(self.raw / "yellow/2024/yellow_tripdata_2024-01.parquet", "yellow", 5)
        escribir_parquet(self.raw / "yellow/2026/yellow_tripdata_2026-02.parquet", "yellow", 3)
        escribir_parquet(self.raw / "green/2024/green_tripdata_2024-01.parquet", "green", 2)
        patcher = patch.object(create_database, "DIR_RAW", self.raw)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_table_has_every_year_and_taxi_type(self):
        salida = Path(self._tmp.name) / "taxi.duckdb"
        create_database.construir(salida)

        con = duckdb.connect(str(salida), read_only=True)
        filas = con.execute(
            "SELECT taxi_type, year, month, count(*) FROM trips GROUP BY ALL ORDER BY ALL"
        ).fetchall()
        con.close()
        self.assertEqual(
            filas,
            [("green", 2024, 1, 2), ("yellow", 2024, 1, 5), ("yellow", 2026, 2, 3)],
        )

    def test_year_filter_limits_the_table(self):
        salida = Path(self._tmp.name) / "solo2024.duckdb"
        create_database.construir(salida, [2024])

        con = duckdb.connect(str(salida), read_only=True)
        anios = {fila[0] for fila in con.execute("SELECT DISTINCT year FROM trips").fetchall()}
        con.close()
        self.assertEqual(anios, {2024})

    def test_duration_is_derived_in_minutes(self):
        salida = Path(self._tmp.name) / "taxi.duckdb"
        create_database.construir(salida)

        con = duckdb.connect(str(salida), read_only=True)
        duracion = con.execute("SELECT DISTINCT duration_minutes FROM trips").fetchall()
        con.close()
        self.assertEqual(duracion, [(30.0,)])

    def test_missing_files_fail_with_clear_message(self):
        vacio = Path(self._tmp.name) / "vacio"
        with patch.object(create_database, "DIR_RAW", vacio):
            with self.assertRaises(SystemExit):
                create_database.construir(Path(self._tmp.name) / "x.duckdb")

    def test_failed_build_does_not_leave_partial_database(self):
        salida = Path(self._tmp.name) / "taxi.duckdb"
        with patch.object(create_database, "sentencia_create", return_value="SELEC roto"):
            with self.assertRaises(duckdb.Error):
                create_database.construir(salida)
        self.assertFalse(salida.exists())
        self.assertFalse(salida.with_name(salida.name + ".tmp").exists())

    def test_parquet_view_matches_the_table(self):
        con = duckdb.connect()
        con.execute(f"CREATE VIEW trips AS {create_database.select_viajes()}")
        total = con.execute("SELECT count(*) FROM trips").fetchone()[0]
        con.close()
        self.assertEqual(total, 10)


class BenchmarkHelperTests(unittest.TestCase):
    def test_queries_are_loaded_with_ids_and_descriptions(self):
        consultas = benchmark.cargar_consultas()
        ids = [c[0] for c in consultas]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(consultas), 6)
        for _, descripcion, sql in consultas:
            self.assertTrue(descripcion)
            self.assertIn("FROM trips", sql)

    def test_datasets_accumulate_years(self):
        self.assertEqual(
            benchmark.conjuntos([2024, 2025, 2026]),
            [[2024], [2024, 2025], [2024, 2025, 2026]],
        )

    def test_results_compare_with_float_tolerance(self):
        self.assertTrue(benchmark.iguales([("a", 1.0000000001)], [("a", 1.0)]))
        self.assertFalse(benchmark.iguales([("a", 1.5)], [("a", 1.0)]))
        self.assertFalse(benchmark.iguales([("a", 1)], [("a", 1), ("b", 2)]))


if __name__ == "__main__":
    unittest.main()
