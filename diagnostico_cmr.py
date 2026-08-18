"""
diagnostico_cmr.py
======================================================================
Encuentra la combinacion exacta de short_name y version que CMR
reconoce para DIST-ALERT, y confirma como se llaman los archivos.

    python diagnostico_cmr.py > cmr.txt
======================================================================
"""
from __future__ import annotations

from pathlib import Path

import earthaccess

from config_local import Config

# Nombres candidatos de la coleccion: CMR es estricto con el nombre
# exacto, asi que se prueban las variantes plausibles.
CANDIDATOS_NOMBRE = [
    "OPERA_L3_DIST-ALERT-HLS_V1",
    "OPERA_L3_DIST-ALERT-HLS",
]
# Formatos candidatos del numero de version (CMR tambien es estricto
# con esto: "1" y "1.0" no son intercambiables).
CANDIDATOS_VERSION = [None, "1.0", "1", "001", "1.1"]

# Un mes con datos garantizados, sobre el Caqueta (zona con
# deforestacion activa y buena cobertura de imagenes, para asegurar
# que la busqueda de prueba devuelva resultados si la combinacion es
# correcta).
TEMPORAL = ("2024-06-01", "2024-06-15")
BBOX = (-75.5, 0.5, -74.0, 2.0)


def sep(t: str) -> None:
    print("\n" + "=" * 68)
    print(t)
    print("=" * 68)


def main() -> None:
    """Recorre nombre x version candidatos y reporta cual combinacion
    de short_name/version reconoce CMR para DIST-ALERT, ademas de
    confirmar el formato de nombre de archivo del que dependen las
    expresiones regulares de descargar_dist.py.
    """
    cfg = Config()

    sep("0. AUTENTICACION")
    auth = earthaccess.login(persist=True)
    print(f"  autenticado: {auth.authenticated}")
    if not auth.authenticated:
        print("  Cree la cuenta en https://urs.earthdata.nasa.gov")
        return

    sep("1. COLECCIONES QUE COINCIDEN CON EL NOMBRE")
    # search_datasets busca a nivel de COLECCION (el "catalogo", no los
    # archivos en si): confirma si CMR conoce ese short_name, y con que
    # numero de version exacto esta registrado.
    for nombre in CANDIDATOS_NOMBRE:
        print(f"\n  short_name = {nombre}")
        try:
            cols = earthaccess.search_datasets(short_name=nombre)
            print(f"    colecciones halladas: {len(cols)}")
            for c in cols:
                u = c.get_umm("ShortName")
                v = c.get_umm("Version")
                cid = c.concept_id()
                print(f"      ShortName={u}  Version={v}  concept_id={cid}")
        except Exception as exc:
            print(f"    [error] {str(exc)[:200]}")

    sep("2. BUSQUEDA DE GRANULOS: QUE COMBINACION FUNCIONA")
    # search_data busca a nivel de GRANULO (los archivos reales). Aqui
    # se prueban todas las combinaciones nombre x version y se anota
    # la primera que devuelve resultados como la "ganadora": esa es la
    # que hay que usar en config_local.py (dist_short_name/dist_version).
    ganadora = None
    for nombre in CANDIDATOS_NOMBRE:
        for ver in CANDIDATOS_VERSION:
            kw = dict(short_name=nombre, bounding_box=BBOX, temporal=TEMPORAL)
            if ver is not None:
                kw["version"] = ver
            etiqueta = f"{nombre} | version={ver}"
            try:
                res = earthaccess.search_data(**kw)
                print(f"  {len(res):5d} granulos  <-  {etiqueta}")
                if res and ganadora is None:
                    ganadora = (nombre, ver, res)
            except Exception as exc:
                print(f"  ERROR         <-  {etiqueta}: {str(exc)[:120]}")

    if ganadora is None:
        sep("SIN RESULTADOS EN NINGUNA COMBINACION")
        print("  Puede ser que su cuenta Earthdata necesite aceptar el EULA")
        print("  del producto. Entre a https://search.earthdata.nasa.gov,")
        print("  busque OPERA DIST-ALERT y descargue un granulo a mano una")
        print("  vez: eso activa el consentimiento.")
        return

    nombre, ver, res = ganadora
    sep("3. COMBINACION GANADORA")
    print(f"  short_name = {nombre}")
    print(f"  version    = {ver}")
    print(f"  granulos   = {len(res)}")
    print("\n  Ponga estos valores en config_local.py:")
    print(f"    dist_short_name: str = \"{nombre}\"")
    print(f"    dist_version: str = \"{ver if ver else ''}\"")

    sep("4. ARCHIVOS DE UN GRANULO (para validar los nombres de capa)")
    # data_links() devuelve las URLs de descarga de TODAS las capas de
    # un granulo (19 en DIST-ALERT); aqui solo se listan para inspeccion
    # manual y confirmar los nombres de sufijo de capa.
    g = res[0]
    enlaces = g.data_links()
    print(f"  el granulo trae {len(enlaces)} enlaces:")
    for u in enlaces:
        print(f"    {Path(u).name}")

    sep("5. LAS DOS CAPAS QUE NECESITAMOS")
    for capa in (cfg.capa_estado, cfg.capa_fecha):
        hit = [u for u in enlaces if u.endswith(f"{capa}.tif")]
        print(f"  {capa:20} -> {len(hit)} coincidencia(s)")
        for u in hit:
            print(f"      {u}")

    sep("6. EXTRACCION DE TILE Y SELLO DE TIEMPO")
    if enlaces:
        n = Path(enlaces[0]).name
        partes = n.split("_")
        print(f"  nombre : {n}")
        for i, p in enumerate(partes):
            print(f"    [{i}] {p}")
        print("\n  descargar_dist.py espera el tile en el patron _T##XXX_")
        print("  y el sello de tiempo en la posicion [4]. Confirme arriba.")


if __name__ == "__main__":
    main()
