import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from scripts import download_data


class FakeResponse:
    def __init__(self, *, status_code=200, chunks=()):
        self.status_code = status_code
        self.ok = 200 <= status_code < 400
        self._chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def iter_content(self, chunk_size):
        del chunk_size
        yield from self._chunks


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(
            download_data,
            "descargar_zonas",
            return_value={"descargados": 0, "omitidos": 1, "no_publicados": [], "fallidos": []},
        )
        self.descargar_zonas = patcher.start()
        self.addCleanup(patcher.stop)

    def test_year_2026_downloads_yellow_and_green(self):
        empty_summary = {
            "descargados": 0,
            "omitidos": 0,
            "no_publicados": [],
            "fallidos": [],
        }
        with patch.object(sys, "argv", ["download_data.py", "--year", "2026"]), patch.object(
            download_data, "descargar", side_effect=[empty_summary, empty_summary]
        ) as descargar:
            self.assertEqual(download_data.main(), 0)

        self.assertEqual(
            [call.args for call in descargar.call_args_list],
            [("yellow", 2026), ("green", 2026)],
        )

    def test_default_downloads_every_supported_year(self):
        empty_summary = {
            "descargados": 0,
            "omitidos": 0,
            "no_publicados": [],
            "fallidos": [],
        }
        with patch.object(sys, "argv", ["download_data.py"]), patch.object(
            download_data,
            "descargar",
            side_effect=[dict(empty_summary) for _ in range(6)],
        ) as descargar:
            self.assertEqual(download_data.main(), 0)

        self.assertEqual(
            [call.args for call in descargar.call_args_list],
            [
                ("yellow", 2024), ("green", 2024),
                ("yellow", 2025), ("green", 2025),
                ("yellow", 2026), ("green", 2026),
            ],
        )

    def test_year_can_be_repeated(self):
        empty_summary = {
            "descargados": 0,
            "omitidos": 0,
            "no_publicados": [],
            "fallidos": [],
        }
        argv = ["download_data.py", "--year", "2026", "--year", "2024", "--taxi", "green"]
        with patch.object(sys, "argv", argv), patch.object(
            download_data,
            "descargar",
            side_effect=[dict(empty_summary), dict(empty_summary)],
        ) as descargar:
            self.assertEqual(download_data.main(), 0)

        self.assertEqual(
            [call.args for call in descargar.call_args_list],
            [("green", 2024), ("green", 2026)],
        )

    def test_rejects_unsupported_year(self):
        with patch.object(sys, "argv", ["download_data.py", "--year", "2023"]):
            with self.assertRaises(SystemExit) as raised:
                download_data.main()

        self.assertEqual(raised.exception.code, 2)

    def test_real_download_failure_returns_nonzero(self):
        failed_summary = {
            "descargados": 0,
            "omitidos": 0,
            "no_publicados": [],
            "fallidos": ["2026-01"],
        }
        empty_summary = {
            "descargados": 0,
            "omitidos": 0,
            "no_publicados": [],
            "fallidos": [],
        }
        with patch.object(sys, "argv", ["download_data.py", "--year", "2026"]), patch.object(
            download_data, "descargar", side_effect=[failed_summary, empty_summary]
        ):
            self.assertEqual(download_data.main(), 1)


    def test_zone_lookup_is_downloaded_once_per_run(self):
        empty_summary = {"descargados": 0, "omitidos": 0, "no_publicados": [], "fallidos": []}
        with patch.object(sys, "argv", ["download_data.py", "--year", "2025"]), patch.object(
            download_data, "descargar", side_effect=[dict(empty_summary), dict(empty_summary)]
        ):
            self.assertEqual(download_data.main(), 0)

        self.descargar_zonas.assert_called_once_with()


class PathsTests(unittest.TestCase):
    def test_destination_uses_expected_raw_directory(self):
        with patch.object(download_data, "DIR_DESTINO", Path("data/raw")):
            self.assertEqual(
                download_data.ruta_destino("green", 2026, 3),
                Path("data/raw/green/2026/green_tripdata_2026-03.parquet"),
            )

    def test_rejects_unknown_taxi_type_before_building_path(self):
        with self.assertRaises(ValueError):
            download_data.ruta_destino("../outside", 2026, 1)


class PublicationTests(unittest.TestCase):
    def test_404_means_month_is_not_published(self):
        with patch.object(
            download_data.requests, "head", return_value=FakeResponse(status_code=404)
        ):
            self.assertFalse(download_data.esta_publicado("https://example.test/file.parquet"))

    def test_cloudfront_403_means_month_is_not_published(self):
        with patch.object(
            download_data.requests, "head", return_value=FakeResponse(status_code=403)
        ):
            self.assertFalse(download_data.esta_publicado("https://example.test/file.parquet"))

    def test_network_error_is_not_misreported_as_unpublished(self):
        with patch.object(
            download_data.requests,
            "head",
            side_effect=requests.Timeout("network unavailable"),
        ):
            with self.assertRaises(requests.RequestException):
                download_data.esta_publicado("https://example.test/file.parquet")

    def test_server_error_is_not_misreported_as_unpublished(self):
        with patch.object(
            download_data.requests, "head", return_value=FakeResponse(status_code=503)
        ):
            with self.assertRaises(requests.RequestException):
                download_data.esta_publicado("https://example.test/file.parquet")


class DownloadTests(unittest.TestCase):
    def test_nonempty_existing_file_is_skipped_without_network_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "yellow" / "2026" / "yellow_tripdata_2026-01.parquet"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"already downloaded")

            with patch.object(download_data, "DIR_DESTINO", root), patch.object(
                download_data,
                "esta_publicado",
                return_value=False,
            ) as published:
                summary = download_data.descargar("yellow", 2026)

            self.assertEqual(summary["omitidos"], 1)
            self.assertEqual(published.call_count, 11)
            self.assertEqual(existing.read_bytes(), b"already downloaded")

    def test_successful_download_is_atomically_promoted(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "yellow_tripdata_2026-01.parquet"
            response = FakeResponse(chunks=(b"abc", b"def"))
            with patch.object(download_data.requests, "get", return_value=response):
                written = download_data.descargar_archivo(
                    "https://example.test/file.parquet", destination
                )

            self.assertEqual(written, 6)
            self.assertEqual(destination.read_bytes(), b"abcdef")
            self.assertEqual(list(destination.parent.glob(f".{destination.name}.*.part")), [])

    def test_failed_download_removes_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "green_tripdata_2026-01.parquet"
            with patch.object(
                download_data.requests,
                "get",
                side_effect=requests.ConnectionError("connection lost"),
            ):
                with self.assertRaises(requests.RequestException):
                    download_data.descargar_archivo(
                        "https://example.test/file.parquet", destination
                    )

            self.assertFalse(destination.exists())
            self.assertEqual(list(destination.parent.glob(f".{destination.name}.*.part")), [])

    def test_publication_check_failure_is_reported_as_real_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            download_data, "DIR_DESTINO", Path(directory)
        ), patch.object(
            download_data,
            "esta_publicado",
            side_effect=[requests.Timeout("network unavailable")] + [False] * 11,
        ):
            summary = download_data.descargar("green", 2026)

        self.assertEqual(summary["fallidos"], ["2026-01"])
        self.assertEqual(len(summary["no_publicados"]), 11)


class ZoneLookupTests(unittest.TestCase):
    def test_existing_zone_lookup_is_not_downloaded_again(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "zones" / "taxi_zone_lookup.csv"
            existing.parent.mkdir(parents=True)
            existing.write_text("LocationID,Borough,Zone,service_zone\n")

            with patch.object(download_data, "DIR_DESTINO", root), patch.object(
                download_data, "descargar_archivo"
            ) as descargar_archivo:
                summary = download_data.descargar_zonas()

            self.assertEqual(summary["omitidos"], 1)
            descargar_archivo.assert_not_called()

    def test_missing_zone_lookup_is_downloaded_to_zones_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(download_data, "DIR_DESTINO", root), patch.object(
                download_data, "descargar_archivo", return_value=100
            ) as descargar_archivo:
                summary = download_data.descargar_zonas()

            self.assertEqual(summary["descargados"], 1)
            descargar_archivo.assert_called_once_with(
                download_data.URL_ZONAS, root / "zones" / "taxi_zone_lookup.csv"
            )


if __name__ == "__main__":
    unittest.main()
