"""Configuración común de las pruebas de app/tests.

Las variables de entorno se fijan ANTES de importar la app: create_app() las
lee al importarse. Base SQLite en memoria (sin Postgres) y sin salir a la red
(el estado del CI se desactiva): las pruebas son rápidas y deterministas.
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "solo-para-pruebas")
os.environ.setdefault("CI_STATUS_DISABLED", "1")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402


def pytest_configure(config):
    config.addinivalue_line("markers", "network: necesita red (API externa); no corre salvo con -m network")


def pytest_collection_modifyitems(config, items):
    """Las pruebas marcadas `network` se saltan salvo que se pidan con `-m network`."""
    if "network" in (config.getoption("-m") or ""):
        return
    skip = pytest.mark.skip(reason="necesita red: correr con -m network")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)
