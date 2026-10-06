"""Estado REAL del CI de qa-automation-portfolio, leído de la API pública de GitHub.

Reemplaza los badges "passing" que antes eran texto fijo: si el CI se pone rojo,
el sitio lo refleja. Principios de diseño:

- Nunca miente por omisión: si GitHub no responde, o el último dato es viejo,
  el estado es UNKNOWN ("sin datos"), jamás PASSING por defecto.
- No frena el render de la página: la lectura vive en un hilo aparte y las
  páginas siempre responden con lo que haya en caché.
- Respeta el límite de la API sin autenticar (60 peticiones/hora por IP): con
  TTL de 5 min y 2 peticiones por refresco gasta como máximo 24/hora.
- Solo librería estándar (urllib), sin dependencias nuevas en la imagen Docker.

Limitación conocida: los steps con `continue-on-error: true` (booking flow, ver
CLAUDE.md de qa-automation-portfolio) figuran como "success" en la API aunque
fallen, así que su fallo NO se refleja aquí. Es coherente con la regla del repo
de que ese fallo en CI es esperado y no una regresión.
"""
import json
import logging
import os
import threading
import time
import urllib.request

log = logging.getLogger(__name__)

REPO = "anfelgonta201514/qa-automation-portfolio"
WORKFLOW = "tests.yml"
BRANCH = "master"
API = "https://api.github.com"

TTL = 300              # s: cada cuánto se refresca el dato
RETRY_AFTER_FAIL = 60  # s: espera antes de reintentar tras un error (evita martillar la API)
MAX_STALE = 6 * 3600   # s: pasado esto, un dato viejo se descarta y se muestra "sin datos"
TIMEOUT = 4            # s: por petición a GitHub

PASSING, FAILING, UNKNOWN = "passing", "failing", "unknown"

# Conclusiones que cuentan como fallo real. "cancelled" y "skipped" NO: un run
# cancelado a mano no significa que el código esté roto.
_FAILED = {"failure", "timed_out", "startup_failure"}

EMPTY = {"states": {}, "run_url": None, "sha": None, "finished": None}


def _state(conclusions):
    """Resume una lista de conclusiones de GitHub en passing / failing / unknown."""
    conclusions = [c for c in conclusions if c]
    if not conclusions:
        return UNKNOWN
    if any(c in _FAILED for c in conclusions):
        return FAILING
    if all(c == "success" for c in conclusions):
        return PASSING
    return UNKNOWN


def evaluate(run, jobs):
    """Estado por proyecto (claves = las etiquetas de PROJECT_TAGS en public.py)."""
    api_jobs = [j for j in jobs if j.get("name") == "API tests"]
    ui_jobs = [j for j in jobs if str(j.get("name", "")).startswith("UI tests")]
    # El BDD de UI vive como steps dentro de los jobs de UI; el escenario de
    # admin es el bloqueante (el de booking es continue-on-error).
    bdd_steps = [
        s.get("conclusion")
        for j in ui_jobs
        for s in j.get("steps", [])
        if "BDD - admin room" in str(s.get("name", ""))
    ]
    return {
        "API": _state([j.get("conclusion") for j in api_jobs]),
        "UI": _state([j.get("conclusion") for j in ui_jobs]),
        "BDD": _state(bdd_steps),
        "CI/CD": _state([run.get("conclusion")]),
    }


def _get(path):
    req = urllib.request.Request(
        API + path,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "qa-portfolio-server"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def _fetch():
    runs = _get(
        f"/repos/{REPO}/actions/workflows/{WORKFLOW}/runs?branch={BRANCH}&status=completed&per_page=1"
    )["workflow_runs"]
    if not runs:
        return dict(EMPTY)
    run = runs[0]
    jobs = _get(f"/repos/{REPO}/actions/runs/{run['id']}/jobs?per_page=100")["jobs"]
    return {
        "states": evaluate(run, jobs),
        "run_url": run.get("html_url"),
        "sha": (run.get("head_sha") or "")[:7],
        "finished": run.get("updated_at"),
    }


_lock = threading.Lock()
_cache = {"data": None, "fetched_at": 0.0, "refreshing": False, "next_try": 0.0}


def _refresh():
    try:
        data = _fetch()
    except Exception as exc:  # red caída, límite de la API, JSON raro...: nunca debe tumbar el sitio
        log.warning("ci_status: no se pudo leer GitHub (%s)", exc)
        with _lock:
            _cache["refreshing"] = False
            _cache["next_try"] = time.time() + RETRY_AFTER_FAIL
        return
    with _lock:
        _cache.update(data=data, fetched_at=time.time(), refreshing=False)


def get_status():
    """Último dato conocido; dispara un refresco en segundo plano si está vencido."""
    if os.environ.get("CI_STATUS_DISABLED"):
        return EMPTY
    now = time.time()
    with _lock:
        data = _cache["data"]
        age = now - _cache["fetched_at"]
        stale = data is None or age > TTL
        start = stale and not _cache["refreshing"] and now >= _cache["next_try"]
        if start:
            _cache["refreshing"] = True
    if start:
        threading.Thread(target=_refresh, daemon=True).start()
    if data is None or age > MAX_STALE:
        return EMPTY
    return data


def state_for(tag):
    """Estado de un proyecto por su etiqueta (UI / API / CI/CD / BDD)."""
    return get_status()["states"].get(tag, UNKNOWN)
