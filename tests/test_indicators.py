import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

from scripts import create_database, indicators, setup_dashboard
from tests.test_database import escribir_parquet


class IndicatorFileTests(unittest.TestCase):
    def setUp(self):
        self.indicadores = indicators.cargar_indicadores()

    def test_there_are_at_least_ten_questions(self):
        self.assertGreaterEqual(len(self.indicadores), 10)
        for indicador in self.indicadores:
            self.assertTrue(indicador.pregunta)
            self.assertTrue(indicador.descripcion, indicador.archivo)

    def test_titles_are_unique(self):
        titulos = [i.titulo for i in self.indicadores]
        self.assertEqual(len(titulos), len(set(titulos)))

    def test_layout_fits_grid_without_overlaps(self):
        ocupadas = {(fila, col) for fila in range(indicators.ALTO_ENCABEZADO) for col in range(24)}
        for indicador in self.indicadores:
            col, fila, ancho, alto = indicador.layout
            self.assertLessEqual(col + ancho, 24, indicador.archivo)
            celdas = {(f, c) for f in range(fila, fila + alto) for c in range(col, col + ancho)}
            self.assertFalse(ocupadas & celdas, f"{indicador.archivo} se superpone")
            ocupadas |= celdas

    def test_header_is_parsed(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "01_prueba.sql"
            ruta.write_text(
                "-- @title Prueba\n"
                "-- @question Cuantos?\n"
                "-- @display bar\n"
                "-- @x mes\n"
                "-- @series anio\n"
                "-- @y viajes\n"
                "-- @colors 2024=#111111,2025=#222222\n"
                "-- @layout 0,2,12,6\n"
                "--\n"
                "-- Explicacion.\n"
                "SELECT 1 AS mes, '2024' AS anio, 3 AS viajes;\n"
            )
            indicador = indicators.leer_indicador(ruta)
        self.assertEqual(indicador.display, "bar")
        self.assertEqual(indicador.layout, (0, 2, 12, 6))
        self.assertEqual(indicador.colores, {"2024": "#111111", "2025": "#222222"})
        self.assertEqual(indicador.descripcion, "Explicacion.")

    def test_chart_without_axes_is_rejected(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "x.sql"
            ruta.write_text(
                "-- @title X\n-- @question Q\n-- @display line\n-- @layout 0,0,6,3\nSELECT 1;\n"
            )
            with self.assertRaises(ValueError):
                indicators.leer_indicador(ruta)

    def test_chart_settings_use_declared_columns(self):
        indicador = next(i for i in self.indicadores if i.stack)
        ajustes = setup_dashboard.visualizacion(indicador)
        self.assertEqual(ajustes["graph.dimensions"], [indicador.x, indicador.series])
        self.assertEqual(ajustes["graph.metrics"], [indicador.y])
        self.assertEqual(ajustes["stackable.stack_type"], "normalized")
        self.assertFalse(ajustes["graph.max_categories_enabled"])


class IndicatorQueryTests(unittest.TestCase):
    """Cada consulta debe ejecutarse sobre una base con el esquema real."""

    def test_every_indicator_runs_on_the_database_schema(self):
        with tempfile.TemporaryDirectory() as directorio:
            raw = Path(directorio) / "raw"
            escribir_parquet(raw / "yellow/2024/yellow_tripdata_2024-01.parquet", "yellow", 4)
            escribir_parquet(raw / "yellow/2025/yellow_tripdata_2025-01.parquet", "yellow", 3)
            escribir_parquet(raw / "green/2024/green_tripdata_2024-01.parquet", "green", 2)
            zonas = raw / "zones" / "taxi_zone_lookup.csv"
            zonas.parent.mkdir(parents=True)
            zonas.write_text(
                '"LocationID","Borough","Zone","service_zone"\n'
                '10,"Manhattan","Zona A","Yellow Zone"\n'
                '20,"Manhattan","Zona B","Yellow Zone"\n'
            )
            salida = Path(directorio) / "taxi.duckdb"
            with patch.object(create_database, "DIR_RAW", raw):
                create_database.construir(salida)

            con = duckdb.connect(str(salida), read_only=True)
            try:
                for indicador in indicators.cargar_indicadores():
                    with self.subTest(indicador=indicador.nombre):
                        resultado = con.execute(indicador.sql).fetchdf()
                        self.assertGreater(len(resultado), 0)
                        for columna in (indicador.x, indicador.series, indicador.y):
                            if columna:
                                self.assertIn(columna, resultado.columns)
            finally:
                con.close()


if __name__ == "__main__":
    unittest.main()
