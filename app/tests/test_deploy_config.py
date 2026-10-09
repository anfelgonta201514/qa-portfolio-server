"""Pruebas de la configuración de despliegue que hace falta para el modo en vivo (QAP-18).

Docker no se puede arrancar aquí, así que se leen como texto el Dockerfile, docker-compose.yml y .env.example y se
comprueba que dicen lo que deben. Lo que NO prueban: que el contenedor arranque (eso lo ve el deploy y su smoke test).
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = (ROOT / "app" / "Dockerfile").read_text(encoding="utf-8")
COMPOSE = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
ENV_EXAMPLE = (ROOT / ".env.example").read_text(encoding="utf-8")


def _app_service():
    """Texto del servicio `app` del compose (hasta el siguiente servicio)."""
    m = re.search(r"^  app:\n(.*?)^  \w[\w-]*:\n", COMPOSE, flags=re.S | re.M)
    assert m, "no se encontró el servicio app"
    return m.group(1)


def _documented_variables(prefix):
    """Variables `PREFIJO_*` que .env.example documenta (activas o comentadas)."""
    return sorted(set(re.findall(rf"^#?\s*({prefix}_[A-Z_]+)=", ENV_EXAMPLE, flags=re.M)))


# ---------- Gunicorn: un proceso con hilos

def test_gunicorn_uses_threads_so_a_slow_provider_call_does_not_block_the_whole_site():
    assert re.search(r"--worker-class[\"', =]+gthread", DOCKERFILE), "falta --worker-class gthread"
    threads = int(re.search(r"--threads[\"', =]+(\d+)", DOCKERFILE).group(1))
    assert threads >= 2


def test_gunicorn_keeps_exactly_one_process_because_the_limits_live_in_memory():
    workers = re.search(r"--workers[\"', =]+(\d+)", DOCKERFILE)
    assert workers and workers.group(1) == "1", "con más de un proceso cada uno tendría su propio contador"


def test_the_worker_timeout_is_longer_than_the_provider_timeout():
    # Un worker que tarda más que --timeout muere. AIConfig.timeout_seconds (15 s) debe caber con margen.
    timeout = int(re.search(r"--timeout[\"', =]+(\d+)", DOCKERFILE).group(1))
    from ai_service import AIConfig
    assert timeout >= AIConfig().timeout_seconds + 10


# ---------- docker-compose: el servicio app recibe las variables

AI_VARS = _documented_variables("AI")
LOGIN_VARS = _documented_variables("LOGIN")


def test_the_example_env_documents_the_variables_this_test_expects():
    assert {"AI_PROVIDER", "AI_MODEL", "AI_API_KEY", "AI_DAILY_CAP", "AI_MAX_OUTPUT_TOKENS"} <= set(AI_VARS)
    assert {"LOGIN_MAX_FAILURES", "LOGIN_WINDOW_SECONDS"} <= set(LOGIN_VARS)


@pytest.mark.parametrize("name", AI_VARS + LOGIN_VARS)
def test_compose_passes_every_documented_variable_to_the_app_container(name):
    # El compose SOLO entrega las variables que lista: sin esto el .env no llega a la app aunque la tenga.
    assert re.search(rf"^\s+{name}:\s*\$\{{{name}(:-[^}}]*)?\}}\s*$", _app_service(), flags=re.M), f"{name} no se pasa a `app`"


def test_compose_never_hardcodes_a_secret_value():
    for name in ("AI_API_KEY", "SECRET_KEY"):
        line = re.search(rf"^\s+{name}:\s*(.*)$", _app_service(), flags=re.M).group(1).strip()
        assert re.fullmatch(r"\$\{%s(:-)?\}" % name, line), f"{name} debe venir del .env, no escrito en el compose: {line!r}"


def test_the_cookie_secure_switch_is_not_exposed_to_the_container():
    # SESSION_COOKIE_SECURE=0 es solo para desarrollo local por http; que llegue a producción por un .env descuidado
    # quitaría el flag Secure de la cookie de sesión.
    assert "SESSION_COOKIE_SECURE" not in COMPOSE


def test_the_live_mode_is_off_in_the_example_env_and_the_key_is_empty():
    assert not re.search(r"^AI_PROVIDER=\S", ENV_EXAMPLE, flags=re.M), "AI_PROVIDER no debe venir activo en el ejemplo"
    assert not re.search(r"^AI_API_KEY=\S", ENV_EXAMPLE, flags=re.M), "nunca una clave en .env.example"
