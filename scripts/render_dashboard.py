#!/usr/bin/env python3
"""Genera una imagen estatica del tablero de indicadores.

Ejecuta las consultas de sql/indicators/ sobre data/processed/taxi.duckdb y
dibuja cada indicador con la visualizacion y la posicion declaradas en su
encabezado (las mismas que usa scripts/setup_dashboard.py en Metabase). Sirve
como evidencia reproducible del tablero sin depender de un navegador.

Uso (desde la raiz del proyecto):
    python scripts/render_dashboard.py
    python scripts/render_dashboard.py --output docs/dashboard/tablero.png
"""

import argparse
import sys
import textwrap
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indicators import ALTO_ENCABEZADO, BASE_POR_DEFECTO, Indicador, cargar_indicadores  # noqa: E402

SALIDA_POR_DEFECTO = Path("docs/dashboard/tablero.png")
COLUMNAS = 24
# Orden categorico fijo para series sin color declarado.
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
SUPERFICIE = "#fcfcfb"
GRILLA = "#e4e3df"

plt.rcParams.update({
    "font.size": 9,
    "axes.edgecolor": GRILLA,
    "axes.labelcolor": TEXTO_2,
    "axes.titlecolor": TEXTO,
    "axes.titlesize": 10,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRILLA,
    "grid.linewidth": 0.6,
    "xtick.color": TEXTO_2,
    "ytick.color": TEXTO_2,
    "legend.frameon": False,
    "legend.fontsize": 8,
    "figure.facecolor": SUPERFICIE,
    "axes.facecolor": SUPERFICIE,
})


def colores(indicador: Indicador, series: list[str]) -> dict[str, str]:
    asignados = {}
    libres = iter(PALETA)
    for serie in series:
        asignados[serie] = indicador.colores.get(serie) or next(libres)
    return asignados


def titulo(eje, indicador: Indicador) -> None:
    eje.set_title("\n".join(textwrap.wrap(indicador.titulo, 70)), pad=8)


def dibujar_scalar(eje, indicador: Indicador, datos: pd.DataFrame) -> None:
    eje.axis("off")
    valor = datos.iloc[0, 0]
    texto = f"{valor:,.0f}" if float(valor).is_integer() and abs(valor) >= 1000 else f"{valor:,.2f}"
    eje.text(0.02, 0.38, texto, fontsize=26, fontweight="bold", color=TEXTO, transform=eje.transAxes)
    eje.text(0.02, 0.82, "\n".join(textwrap.wrap(indicador.titulo, 45)), fontsize=9,
             color=TEXTO_2, transform=eje.transAxes, va="top")


def dibujar_tabla(eje, indicador: Indicador, datos: pd.DataFrame) -> None:
    eje.axis("off")
    titulo(eje, indicador)
    celdas = datos.astype(object).where(datos.notna(), "")
    tabla = eje.table(cellText=celdas.values, colLabels=[c.replace("_", " ") for c in datos.columns],
                      loc="center", cellLoc="right", colLoc="right")
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(8)
    tabla.scale(1, 1.35)
    for (fila, _), celda in tabla.get_celld().items():
        celda.set_edgecolor(GRILLA)
        celda.set_facecolor(SUPERFICIE)
        if fila == 0:
            celda.set_text_props(color=TEXTO_2, fontweight="bold")


def dibujar_linea(eje, indicador: Indicador, datos: pd.DataFrame) -> None:
    titulo(eje, indicador)
    if indicador.series:
        series = list(dict.fromkeys(datos[indicador.series].astype(str)))
        paleta = colores(indicador, series)
        for serie in series:
            d = datos[datos[indicador.series].astype(str) == serie]
            eje.plot(d[indicador.x], d[indicador.y], color=paleta[serie], linewidth=2,
                     marker="o", markersize=3, label=serie)
        eje.legend(loc="best", ncols=len(series))
    else:
        eje.plot(datos[indicador.x], datos[indicador.y], color=PALETA[0], linewidth=2)
    eje.set_xlabel(indicador.x.replace("_", " "))
    eje.set_ylabel(indicador.y.replace("_", " "))
    if indicador.x in {"mes", "hora"}:
        eje.set_xticks(sorted(datos[indicador.x].unique())[:: 2 if indicador.x == "hora" else 1])


def dibujar_barras(eje, indicador: Indicador, datos: pd.DataFrame) -> None:
    titulo(eje, indicador)
    tabla = datos.pivot_table(index=indicador.x, columns=indicador.series, values=indicador.y,
                              aggfunc="sum", sort=False) if indicador.series else \
        datos.set_index(indicador.x)[[indicador.y]]
    tabla.columns = [str(c) for c in tabla.columns]
    paleta = colores(indicador, list(tabla.columns))
    if indicador.stack == "normalized":
        tabla = tabla.div(tabla.sum(axis=1), axis=0) * 100
        tabla.plot(kind="barh", stacked=True, ax=eje, width=0.75, edgecolor=SUPERFICIE, linewidth=1.5,
                   color=[paleta[c] for c in tabla.columns])
        eje.set_xlabel("% de los viajes")
        eje.set_ylabel("")
        eje.invert_yaxis()
        eje.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncols=len(tabla.columns))
    else:
        tabla.plot(kind="bar", ax=eje, width=0.75, edgecolor=SUPERFICIE, linewidth=1.5,
                   color=[paleta[c] for c in tabla.columns], rot=0)
        eje.set_xlabel(indicador.x.replace("_", " "))
        eje.set_ylabel(indicador.y.replace("_", " "))
        if len(tabla.columns) > 1:
            eje.legend(loc="upper right")
        else:
            eje.get_legend().remove()


def dibujar_filas(eje, indicador: Indicador, datos: pd.DataFrame) -> None:
    titulo(eje, indicador)
    d = datos.iloc[::-1]
    posiciones = range(len(d))
    eje.barh(posiciones, d[indicador.y], color=PALETA[0], height=0.75)
    # Etiquetas dentro de las barras: los nombres de zona son largos y fuera
    # de la barra invadirian la tarjeta vecina.
    for posicion, (etiqueta, valor) in enumerate(zip(d[indicador.x], d[indicador.y])):
        eje.text(valor * 0.02, posicion, f"{etiqueta}  {valor:,.0f}", va="center",
                 fontsize=7.5, color="#ffffff")
    eje.set_yticks([])
    eje.set_xlabel(indicador.y.replace("_", " "))
    eje.grid(axis="y", visible=False)


DIBUJOS = {
    "scalar": dibujar_scalar,
    "table": dibujar_tabla,
    "line": dibujar_linea,
    "bar": dibujar_barras,
    "row": dibujar_filas,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera una imagen del tablero de indicadores.")
    parser.add_argument("--db", type=Path, default=BASE_POR_DEFECTO)
    parser.add_argument("--output", type=Path, default=SALIDA_POR_DEFECTO)
    argumentos = parser.parse_args()

    if not argumentos.db.exists():
        raise SystemExit(f"No existe {argumentos.db}. Ejecute primero scripts/create_database.py.")

    indicadores = cargar_indicadores()
    filas = max(i.layout[1] + i.layout[3] for i in indicadores)
    figura = plt.figure(figsize=(22, filas * 0.8))
    grilla = figura.add_gridspec(filas, COLUMNAS, hspace=3.2, wspace=3.0,
                                 left=0.04, right=0.98, top=0.985, bottom=0.02)

    encabezado = figura.add_subplot(grilla[0:ALTO_ENCABEZADO, :])
    encabezado.axis("off")
    encabezado.text(0, 0.75, "Viajes de taxi de Nueva York (NYC TLC) - yellow y green",
                    fontsize=16, fontweight="bold", color=TEXTO, transform=encabezado.transAxes)
    encabezado.text(0, 0.1, "Fuente: tabla trips de data/processed/taxi.duckdb (consultas en "
                    "sql/indicators/). Promedios sobre viajes validos; comparaciones anuales sobre los "
                    "meses publicados en todos los anios.", fontsize=9, color=TEXTO_2,
                    transform=encabezado.transAxes)

    con = duckdb.connect(str(argumentos.db), read_only=True)
    try:
        for indicador in indicadores:
            col, fila, ancho, alto = indicador.layout
            eje = figura.add_subplot(grilla[fila:fila + alto, col:col + ancho])
            datos = con.execute(indicador.sql).fetchdf()
            DIBUJOS[indicador.display](eje, indicador, datos)
    finally:
        con.close()

    argumentos.output.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(argumentos.output, dpi=110)
    print(f"Tablero guardado en {argumentos.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
