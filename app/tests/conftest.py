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


OPT_IN_MARKERS = {
    "network": "necesita red (API externa)",
    "groq_live": "usa una clave REAL de Groq y gasta cuota",
}


def pytest_configure(config):
    for name, why in OPT_IN_MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {why}; no corre salvo con -m {name}")


def pytest_collection_modifyitems(config, items):
    """Las pruebas con marcador de "opt-in" se saltan salvo que se pidan con `-m <marcador>`."""
    requested = config.getoption("-m") or ""
    for name, why in OPT_IN_MARKERS.items():
        if name in requested:
            continue
        skip = pytest.mark.skip(reason=f"{why}: correr con -m {name}")
        for item in items:
            if name in item.keywords:
                item.add_marker(skip)
