#!/usr/bin/env python3
"""Descarga los archivos Parquet del NYC TLC Trip Record Data.

Descarga los registros de viajes de taxis amarillos (yellow) y verdes (green)
de los anios soportados (ver ANIOS_PERMITIDOS). Incorporar un anio nuevo solo
requiere agregarlo a esa tupla: el resto del flujo no cambia.

Fuente oficial de los datos:
    https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

Uso:
    python scripts/download_data.py                             # todos los anios
    python scripts/download_data.py --year 2026                 # un anio
    python scripts/download_data.py --year 2024 --year 2025     # varios anios
    python scripts/download_data.py --year 2024 --taxi yellow

Los archivos se guardan en:
    data/raw/<tipo>/<anio>/<nombre-original>.parquet
    data/raw/zones/taxi_zone_lookup.csv   (catalogo de zonas de la TLC)

Comportamiento:
  - La TLC publica cada mes con varias semanas de atraso, por lo que no todos
    los meses del anio en curso existen todavia. El script consulta al servidor que
    meses estan publicados en lugar de suponerlos.
  - Un archivo que ya existe localmente no se vuelve a descargar.
  - La descarga se hace sobre un nombre temporal y solo se renombra al
    terminar, de modo que una interrupcion no deja archivos .parquet a medias.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

import requests

ANIOS_PERMITIDOS = (2024, 2025, 2026)
TIPOS_TAXI = ("yellow", "green")
URL_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
URL_ZONAS = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
DIR_DESTINO = Path("data/raw")

TIEMPO_ESPERA = 60          # segundos por peticion
INTENTOS = 3                # intentos por archivo antes de darse por vencido
BLOQUE = 1024 * 1024        # 1 MiB por bloque de descarga


def validar_parametros(tipo: str, anio: int, mes: int) -> None:
    """Rechaza valores que no pertenecen al conjunto de datos soportado."""
    if tipo not in TIPOS_TAXI:
        raise ValueError(f"tipo de taxi no permitido: {tipo!r}")
    if anio not in ANIOS_PERMITIDOS:
        raise ValueError(f"anio no permitido: {anio!r}")
    if not 1 <= mes <= 12:
        raise ValueError(f"mes fuera de rango: {mes!r}")


def construir_nombre(tipo: str, anio: int, mes: int) -> str:
    """Nombre del archivo publicado por la TLC, p. ej. yellow_tripdata_2026-01.parquet."""
    validar_parametros(tipo, anio, mes)
    return f"{tipo}_tripdata_{anio}-{mes:02d}.parquet"


def construir_url(tipo: str, anio: int, mes: int) -> str:
    """URL completa del archivo Parquet mensual."""
    return f"{URL_BASE}/{construir_nombre(tipo, anio, mes)}"


def ruta_destino(tipo: str, anio: int, mes: int) -> Path:
    """Ruta local donde se guarda el archivo."""
    return DIR_DESTINO / tipo / str(anio) / construir_nombre(tipo, anio, mes)


def esta_publicado(url: str) -> bool:
    """Indica si el archivo existe en el servidor (sin descargarlo)."""
    respuesta = requests.head(url, timeout=TIEMPO_ESPERA, allow_redirects=True)
    # El origen S3 de la TLC responde 403 para objetos mensuales que todavia
    # no existen; CloudFront conserva ese codigo en lugar de devolver 404.
    if respuesta.status_code in (403, 404):
        return False
    respuesta.raise_for_status()
    return True


def formato_tamanio(n: float) -> str:
    for unidad in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unidad == "GiB":
            return f"{n:.1f} {unidad}"
        n /= 1024
    return f"{n:.1f} GiB"


def descargar_archivo(url: str, destino: Path) -> int:
    """Descarga `url` en `destino`. Devuelve la cantidad de bytes escritos."""
    destino.parent.mkdir(parents=True, exist_ok=True)

    ultimo_error = None
    for intento in range(1, INTENTOS + 1):
        temporal = None
        try:
            descriptor, nombre_temporal = tempfile.mkstemp(
                dir=destino.parent,
                prefix=f".{destino.name}.",
                suffix=".part",
            )
            os.close(descriptor)
            temporal = Path(nombre_temporal)
            with requests.get(url, stream=True, timeout=TIEMPO_ESPERA) as respuesta:
                respuesta.raise_for_status()
                escritos = 0
                with temporal.open("wb") as archivo:
                    for bloque in respuesta.iter_content(chunk_size=BLOQUE):
                        if bloque:
                            archivo.write(bloque)
                            escritos += len(bloque)
            if escritos == 0:
                raise requests.RequestException("el servidor devolvio un archivo vacio")
            temporal.replace(destino)
            return escritos
        except (requests.RequestException, OSError) as error:
            ultimo_error = error
            if temporal is not None:
                temporal.unlink(missing_ok=True)
            if intento < INTENTOS:
                print(f"      intento {intento}/{INTENTOS} fallido ({error}); reintentando")

    if isinstance(ultimo_error, requests.RequestException):
        raise requests.RequestException(f"no se pudo descargar {url}: {ultimo_error}")
    raise OSError(f"no se pudo guardar {destino}: {ultimo_error}")


def descargar(tipo: str, anio: int) -> dict:
    """Descarga todos los meses publicados de un tipo de taxi y un anio."""
    validar_parametros(tipo, anio, 1)
    print(f"\n=== {tipo.upper()} {anio} ===")
    resumen = {"descargados": 0, "omitidos": 0, "no_publicados": [], "fallidos": []}

    for mes in range(1, 13):
        etiqueta = f"{anio}-{mes:02d}"
        destino = ruta_destino(tipo, anio, mes)

        if destino.exists() and destino.stat().st_size > 0:
            print(f"  {etiqueta}  ya existe, se omite")
            resumen["omitidos"] += 1
            continue

        url = construir_url(tipo, anio, mes)
        try:
            publicado = esta_publicado(url)
        except requests.RequestException as error:
            print(f"  {etiqueta}  ERROR al consultar publicacion: {error}")
            resumen["fallidos"].append(etiqueta)
            continue
        if not publicado:
            print(f"  {etiqueta}  aun no publicado por la TLC")
            resumen["no_publicados"].append(etiqueta)
            continue

        print(f"  {etiqueta}  descargando...")
        try:
            escritos = descargar_archivo(url, destino)
        except (requests.RequestException, OSError) as error:
            print(f"  {etiqueta}  ERROR: {error}")
            resumen["fallidos"].append(etiqueta)
        else:
            print(f"  {etiqueta}  listo ({formato_tamanio(escritos)}) -> {destino}")
            resumen["descargados"] += 1

    return resumen


def descargar_zonas() -> dict:
    """Descarga el catalogo de zonas (LocationID -> Borough, Zone) si no existe."""
    print("\n=== ZONAS ===")
    resumen = {"descargados": 0, "omitidos": 0, "no_publicados": [], "fallidos": []}
    destino = DIR_DESTINO / "zones" / "taxi_zone_lookup.csv"
    if destino.exists() and destino.stat().st_size > 0:
        print("  taxi_zone_lookup.csv  ya existe, se omite")
        resumen["omitidos"] += 1
        return resumen
    try:
        escritos = descargar_archivo(URL_ZONAS, destino)
    except (requests.RequestException, OSError) as error:
        print(f"  taxi_zone_lookup.csv  ERROR: {error}")
        resumen["fallidos"].append("taxi_zone_lookup.csv")
    else:
        print(f"  taxi_zone_lookup.csv  listo ({formato_tamanio(escritos)}) -> {destino}")
        resumen["descargados"] += 1
    return resumen


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Descarga los datos de taxis del NYC TLC."
    )
    parser.add_argument(
        "--year", type=int, action="append", choices=ANIOS_PERMITIDOS,
        help="anio a descargar; se puede repetir (por defecto: todos los "
             f"soportados: {', '.join(map(str, ANIOS_PERMITIDOS))})",
    )
    parser.add_argument(
        "--taxi", choices=(*TIPOS_TAXI, "all"), default="all",
        help="tipo de taxi a descargar (por defecto: all)",
    )
    argumentos = parser.parse_args()

    tipos = TIPOS_TAXI if argumentos.taxi == "all" else (argumentos.taxi,)

    total = {"descargados": 0, "omitidos": 0, "no_publicados": [], "fallidos": []}
    anios = sorted(set(argumentos.year or ANIOS_PERMITIDOS))

    for anio in anios:
        for tipo in tipos:
            resumen = descargar(tipo, anio)
            total["descargados"] += resumen["descargados"]
            total["omitidos"] += resumen["omitidos"]
            total["no_publicados"] += [f"{tipo} {m}" for m in resumen["no_publicados"]]
            total["fallidos"] += [f"{tipo} {m}" for m in resumen["fallidos"]]

    zonas = descargar_zonas()
    total["descargados"] += zonas["descargados"]
    total["omitidos"] += zonas["omitidos"]
    total["fallidos"] += zonas["fallidos"]

    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"  descargados   : {total['descargados']}")
    print(f"  ya existian   : {total['omitidos']}")
    print(f"  no publicados : {len(total['no_publicados'])}")
    if total["no_publicados"]:
        print(f"      {', '.join(total['no_publicados'])}")
    print(f"  fallidos      : {len(total['fallidos'])}")
    if total["fallidos"]:
        print(f"      {', '.join(total['fallidos'])}")
    print("=" * 60)

    return 1 if total["fallidos"] else 0


if __name__ == "__main__":
    sys.exit(main())
