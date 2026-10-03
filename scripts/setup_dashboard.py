#!/usr/bin/env python3
"""Crea (o actualiza) el tablero de indicadores en Metabase.

Usa la API de Metabase para:
  1. completar la configuracion inicial si Metabase todavia no tiene usuario
     administrador (con las credenciales de MB_ADMIN_EMAIL / MB_ADMIN_PASSWORD);
  2. registrar la base data/processed/taxi.duckdb en modo solo lectura;
  3. crear una pregunta SQL nativa por cada archivo de sql/indicators/, con la
     visualizacion declarada en su encabezado (ver scripts/indicators.py);
  4. organizar las preguntas en el tablero "Taxis NYC - Indicadores".

Es idempotente: si la coleccion, las preguntas o el tablero ya existen se
actualizan en lugar de duplicarse, por lo que se puede volver a ejecutar despues
de agregar un anio o modificar una consulta.

Uso (dentro del contenedor lab, con los servicios de docker compose iniciados):
    python scripts/setup_dashboard.py
    python scripts/setup_dashboard.py --public     # ademas crea un enlace publico de solo lectura

Variables de entorno (opcionales):
    MB_URL             URL de Metabase vista desde el script (por defecto http://metabase:3000)
    MB_ADMIN_EMAIL     usuario administrador (por defecto admin@lab8.local)
    MB_ADMIN_PASSWORD  contrasena del administrador (por defecto Lab8-duckdb)
"""

import argparse
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indicators import ALTO_ENCABEZADO, Indicador, cargar_indicadores  # noqa: E402

MB_URL = os.environ.get("MB_URL", "http://metabase:3000").rstrip("/")
MB_ADMIN_EMAIL = os.environ.get("MB_ADMIN_EMAIL", "admin@lab8.local")
MB_ADMIN_PASSWORD = os.environ.get("MB_ADMIN_PASSWORD", "Lab8-duckdb")

NOMBRE_BASE = "Taxis NYC (DuckDB)"
RUTA_BASE = "/workspace/data/processed/taxi.duckdb"
NOMBRE_COLECCION = "Lab 8 - Taxis NYC"
NOMBRE_TABLERO = "Taxis NYC - Indicadores"
TIEMPO_ESPERA = 120

ENCABEZADO = """\
## Viajes de taxi de Nueva York (NYC TLC) - yellow y green

Fuente: tablas `trips` y `zones` de `data/processed/taxi.duckdb`; cada tarjeta es un archivo de \
`sql/indicators/`. Promedios sobre viajes validos (0 < distancia < 100 mi, 0 < tarifa < 1000 USD, \
0 < duracion < 24 h). Comparaciones anuales sobre los meses publicados en todos los anios.\
"""


class Metabase:
    def __init__(self, url: str):
        self.url = url
        self.sesion = requests.Session()

    def llamar(self, metodo: str, ruta: str, **kwargs):
        respuesta = self.sesion.request(
            metodo, f"{self.url}/api/{ruta}", timeout=TIEMPO_ESPERA, **kwargs
        )
        if not respuesta.ok:
            raise RuntimeError(
                f"{metodo} /api/{ruta} -> HTTP {respuesta.status_code}: {respuesta.text[:500]}"
            )
        return respuesta.json() if respuesta.content else None

    def esperar(self, intentos: int = 60) -> None:
        for _ in range(intentos):
            try:
                if self.sesion.get(f"{self.url}/api/health", timeout=5).ok:
                    return
            except requests.RequestException:
                pass
            time.sleep(5)
        raise SystemExit(f"Metabase no responde en {self.url}")

    def iniciar_sesion(self, email: str, password: str) -> None:
        propiedades = self.llamar("GET", "session/properties")
        if not propiedades.get("has-user-setup"):
            print(f"Configuracion inicial de Metabase (administrador {email})")
            self.llamar("POST", "setup", json={
                "token": propiedades["setup-token"],
                "user": {
                    "email": email,
                    "password": password,
                    "first_name": "Lab",
                    "last_name": "DuckDB",
                    "site_name": "Lab 8 DuckDB",
                },
                "prefs": {"site_name": "Lab 8 DuckDB", "site_locale": "es", "allow_tracking": False},
            })
        sesion = self.llamar("POST", "session", json={"username": email, "password": password})
        self.sesion.headers["X-Metabase-Session"] = sesion["id"]


def lista(respuesta) -> list:
    """Algunos endpoints devuelven una lista y otros {'data': [...]}."""
    return respuesta["data"] if isinstance(respuesta, dict) else respuesta


def asegurar_base(mb: Metabase) -> int:
    detalles = {"database_file": RUTA_BASE, "read_only": True, "old_implicit_casting": True}
    for base in lista(mb.llamar("GET", "database")):
        if base["name"] == NOMBRE_BASE:
            mb.llamar("PUT", f"database/{base['id']}", json={"details": detalles})
            mb.llamar("POST", f"database/{base['id']}/sync_schema")
            print(f"Base existente: {NOMBRE_BASE} (id {base['id']})")
            return base["id"]
    base = mb.llamar("POST", "database", json={
        "engine": "duckdb",
        "name": NOMBRE_BASE,
        "details": detalles,
        "is_full_sync": True,
    })
    print(f"Base registrada: {NOMBRE_BASE} -> {RUTA_BASE} (id {base['id']})")
    return base["id"]


def asegurar_coleccion(mb: Metabase) -> int:
    for coleccion in lista(mb.llamar("GET", "collection")):
        if coleccion.get("name") == NOMBRE_COLECCION and not coleccion.get("archived"):
            return coleccion["id"]
    return mb.llamar("POST", "collection", json={"name": NOMBRE_COLECCION, "parent_id": None})["id"]


def elementos(mb: Metabase, coleccion: int, modelo: str) -> dict[str, int]:
    respuesta = mb.llamar("GET", f"collection/{coleccion}/items", params={"models": modelo})
    return {e["name"]: e["id"] for e in lista(respuesta)}


def visualizacion(indicador: Indicador) -> dict:
    ajustes: dict = {}
    if indicador.display in {"line", "bar", "row"}:
        dimensiones = [indicador.x] + ([indicador.series] if indicador.series else [])
        ajustes["graph.dimensions"] = dimensiones
        ajustes["graph.metrics"] = [indicador.y]
        ajustes["graph.x_axis.title_text"] = indicador.x.replace("_", " ")
        ajustes["graph.y_axis.title_text"] = indicador.y.replace("_", " ")
        if indicador.x in {"mes", "hora", "anio", "rango_millas", "grupo"}:
            ajustes["graph.x_axis.scale"] = "ordinal"
        # Sin limite de series: con el limite activo Metabase agrupa las ultimas en "Other".
        ajustes["graph.max_categories_enabled"] = False
        if indicador.stack:
            ajustes["stackable.stack_type"] = indicador.stack
        if indicador.colores:
            ajustes["series_settings"] = {
                valor: {"color": color} for valor, color in indicador.colores.items()
            }
        elif indicador.display == "row":
            ajustes["series_settings"] = {indicador.y: {"color": "#2a78d6"}}
    if indicador.display == "scalar":
        ajustes["scalar.compact_primary_number"] = False
    return ajustes


def asegurar_pregunta(mb: Metabase, indicador: Indicador, base: int, coleccion: int,
                      existentes: dict[str, int]) -> int:
    cuerpo = {
        "name": indicador.titulo,
        "description": f"{indicador.pregunta} {indicador.descripcion} "
                       f"(sql/indicators/{indicador.archivo.name})",
        "display": indicador.display,
        "visualization_settings": visualizacion(indicador),
        "dataset_query": {
            "type": "native",
            "native": {"query": indicador.sql, "template-tags": {}},
            "database": base,
        },
        "collection_id": coleccion,
    }
    if indicador.titulo in existentes:
        id_ = existentes[indicador.titulo]
        mb.llamar("PUT", f"card/{id_}", json=cuerpo)
        accion = "actualizada"
    else:
        id_ = mb.llamar("POST", "card", json=cuerpo)["id"]
        accion = "creada"
    print(f"  pregunta {accion}: {indicador.titulo} (id {id_})")
    return id_


def asegurar_tablero(mb: Metabase, coleccion: int, tarjetas: list[tuple[Indicador, int]]) -> int:
    tableros = elementos(mb, coleccion, "dashboard")
    if NOMBRE_TABLERO in tableros:
        id_ = tableros[NOMBRE_TABLERO]
    else:
        id_ = mb.llamar("POST", "dashboard", json={
            "name": NOMBRE_TABLERO,
            "description": "Indicadores de los viajes de taxi yellow y green de la NYC TLC.",
            "collection_id": coleccion,
        })["id"]

    dashcards = [{
        "id": -1,
        "card_id": None,
        "row": 0, "col": 0, "size_x": 24, "size_y": ALTO_ENCABEZADO,
        "parameter_mappings": [], "series": [],
        "visualization_settings": {
            "virtual_card": {
                "name": None, "display": "text", "visualization_settings": {},
                "dataset_query": {}, "archived": False,
            },
            "text": ENCABEZADO,
        },
    }]
    for posicion, (indicador, card_id) in enumerate(tarjetas, start=2):
        col, fila, ancho, alto = indicador.layout
        dashcards.append({
            "id": -posicion,
            "card_id": card_id,
            "row": fila, "col": col, "size_x": ancho, "size_y": alto,
            "parameter_mappings": [], "series": [], "visualization_settings": {},
        })
    mb.llamar("PUT", f"dashboard/{id_}", json={"dashcards": dashcards})
    return id_


def main() -> int:
    parser = argparse.ArgumentParser(description="Crea el tablero de indicadores en Metabase.")
    parser.add_argument("--public", action="store_true",
                        help="habilita un enlace publico de solo lectura al tablero")
    argumentos = parser.parse_args()

    if not Path("data/processed/taxi.duckdb").exists():
        raise SystemExit("No existe data/processed/taxi.duckdb. Ejecute primero scripts/create_database.py.")

    indicadores = cargar_indicadores()
    mb = Metabase(MB_URL)
    mb.esperar()
    mb.iniciar_sesion(MB_ADMIN_EMAIL, MB_ADMIN_PASSWORD)

    base = asegurar_base(mb)
    coleccion = asegurar_coleccion(mb)
    existentes = elementos(mb, coleccion, "card")
    print(f"Preguntas en la coleccion '{NOMBRE_COLECCION}':")
    tarjetas = [
        (indicador, asegurar_pregunta(mb, indicador, base, coleccion, existentes))
        for indicador in indicadores
    ]

    # Ejecuta cada pregunta una vez para detectar errores de SQL antes de mostrar el tablero.
    errores = []
    for indicador, card_id in tarjetas:
        resultado = mb.llamar("POST", f"card/{card_id}/query")
        if resultado.get("status") != "completed" or resultado.get("error"):
            errores.append(f"{indicador.archivo.name}: {resultado.get('error')}")

    tablero = asegurar_tablero(mb, coleccion, tarjetas)
    print(f"\nTablero: {NOMBRE_TABLERO}")
    print(f"  http://localhost:3000/dashboard/{tablero}")

    if argumentos.public:
        mb.llamar("PUT", "setting/enable-public-sharing", json={"value": True})
        enlace = mb.llamar("POST", f"dashboard/{tablero}/public_link")
        print(f"  enlace publico: http://localhost:3000/public/dashboard/{enlace['uuid']}")

    if errores:
        print("\nERRORES en preguntas:")
        for error in errores:
            print(f"  {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
