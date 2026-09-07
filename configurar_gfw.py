"""
configurar_gfw.py
======================================================================
Registro de una sola vez en la API de Global Forest Watch (GFW) y
obtencion de la API key necesaria para consultar la fuente de evento del
pipeline (por defecto gfw_integrated_alerts; ver config_local.py y
descargar_gfw.py). La misma key sirve para cualquier dataset de la API.

Flujo (verificado contra el esquema real de data-api.globalforestwatch.org,
no documentacion de terceros):

  1. POST /auth/sign-up          {name, email}
     -> GFW envia una contrasena temporal a ese correo.

  2. POST /auth/token             {username=email, password}
     -> devuelve un access_token de corta duracion.

  3. POST /auth/apikey            {alias, organization, email, domains: []}
     (con el access_token como Bearer)
     -> devuelve la API key real, que es la que usa el resto del pipeline.

USO (desde la raiz del proyecto)
---------------------------------
    python configurar_gfw.py signup --nombre "Su Nombre" --email correo@ejemplo.com
        (una sola vez; revise su correo despues de correrlo)

    python configurar_gfw.py apikey --email correo@ejemplo.com --password "la-de-su-correo"
        (guarda la API key en gfw_api_key.txt, NO se sube a ningun repositorio)

La API key queda en datos/logs/gfw_api_key.txt (fuera del control de
versiones) y descargar_gfw.py la lee de ahi, o de la variable de entorno
GFW_API_KEY si se prefiere no dejarla en disco.
======================================================================
"""
from __future__ import annotations

import argparse
import getpass
import json

import requests

from config_local import DIR_LOG, logger

BASE = "https://data-api.globalforestwatch.org"
ARCHIVO_KEY = DIR_LOG / "gfw_api_key.txt"


def _extraer(respuesta: dict, *rutas: str):
    """
    Busca un valor en la respuesta probando varias rutas posibles
    ("data.access_token", "access_token", ...). La API de GFW no publica
    el esquema exacto de estas respuestas de autenticacion en su OpenAPI
    (a diferencia del resto de endpoints), asi que en vez de asumir un
    nombre de campo y fallar en silencio si esta mal, se prueban las
    variantes mas probables y, si ninguna aparece, se imprime la
    respuesta cruda para poder ajustarlo a mano.
    """
    for ruta in rutas:
        nodo = respuesta
        ok = True
        for parte in ruta.split("."):
            if isinstance(nodo, dict) and parte in nodo:
                nodo = nodo[parte]
            else:
                ok = False
                break
        if ok and nodo:
            return nodo
    logger.error("No se encontro ninguno de estos campos en la respuesta: %s", rutas)
    logger.error("Respuesta cruda del servidor:\n%s", json.dumps(respuesta, indent=2))
    return None


def cmd_signup(nombre: str, email: str) -> int:
    r = requests.post(f"{BASE}/auth/sign-up", json={"name": nombre, "email": email}, timeout=30)
    if r.status_code >= 300:
        logger.error("Fallo el registro (%d): %s", r.status_code, r.text[:300])
        return 1
    logger.info("Registro enviado. Revise %s: GFW manda una contrasena temporal.", email)
    logger.info("Con esa contrasena, corra:")
    logger.info('  python configurar_gfw.py apikey --email %s --password "..."', email)
    return 0


def cmd_apikey(email: str, password: str, alias: str, organizacion: str) -> int:
    # Paso 2: intercambiar email + contrasena por un token de acceso.
    r = requests.post(
        f"{BASE}/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if r.status_code >= 300:
        logger.error("No se pudo obtener el token (%d): %s", r.status_code, r.text[:300])
        return 1
    token = _extraer(r.json(), "data.access_token", "access_token", "data.accessToken")
    if not token:
        return 1

    # Paso 3: con el token, pedir una API key nombrada.
    r = requests.post(
        f"{BASE}/auth/apikey",
        json={"alias": alias, "organization": organizacion, "email": email, "domains": []},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if r.status_code >= 300:
        logger.error("No se pudo crear la API key (%d): %s", r.status_code, r.text[:300])
        return 1
    api_key = _extraer(r.json(), "data.api_key", "api_key", "data.apiKey")
    if not api_key:
        return 1

    ARCHIVO_KEY.write_text(api_key)
    logger.info("API key guardada en %s", ARCHIVO_KEY)
    logger.info("Sin dominios asociados: queda en el nivel de limite de tasa mas bajo, "
                "suficiente para descargas de este pipeline (no es una app web publica).")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Registro en la API de Global Forest Watch")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("signup")
    ps.add_argument("--nombre", required=True)
    ps.add_argument("--email", required=True)

    pk = sub.add_parser("apikey")
    pk.add_argument("--email", required=True)
    pk.add_argument("--password", default=None,
                    help="Si se omite, se pide de forma oculta por consola.")
    pk.add_argument("--alias", default="trabajo-de-grado-deforestacion")
    pk.add_argument("--organizacion", default="Tesis - Universidad")

    a = p.parse_args()
    if a.cmd == "signup":
        return cmd_signup(a.nombre, a.email)
    if a.cmd == "apikey":
        password = a.password or getpass.getpass("Contrasena temporal (la del correo de GFW): ")
        return cmd_apikey(a.email, password, a.alias, a.organizacion)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
