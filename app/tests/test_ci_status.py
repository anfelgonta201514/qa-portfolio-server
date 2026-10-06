"""Pruebas de ci_status: la lógica de estado y el comportamiento ante fallos.

Correr desde la raíz del repo:  python -m pytest app/tests -q
(no necesitan red ni base de datos: GitHub se simula).
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ci_status  # noqa: E402


def _job(name, conclusion="success", steps=None):
    return {"name": name, "conclusion": conclusion, "steps": steps or []}


def _ui(conclusion="success", bdd="success"):
    return _job(
        "UI tests (chromium)",
        conclusion,
        [
            {"name": "Run UI tests (admin + rooms)", "conclusion": "success"},
            {"name": "Run UI tests (BDD - admin room)", "conclusion": bdd},
        ],
    )


RUN_OK = {"conclusion": "success"}


# ---------- evaluate: la lógica de estado ----------

def test_evaluate_all_green_every_project_passing():
    states = ci_status.evaluate(RUN_OK, [_job("API tests"), _ui()])
    assert states == {"API": "passing", "UI": "passing", "BDD": "passing", "CI/CD": "passing"}


def test_evaluate_api_job_failed_only_api_and_cicd_failing():
    states = ci_status.evaluate({"conclusion": "failure"}, [_job("API tests", "failure"), _ui()])
    assert states["API"] == "failing"
    assert states["CI/CD"] == "failing"
    assert states["UI"] == "passing"


def test_evaluate_bdd_step_failed_marks_bdd_and_ui_failing():
    states = ci_status.evaluate({"conclusion": "failure"}, [_job("API tests"), _ui("failure", bdd="failure")])
    assert states["BDD"] == "failing"
    assert states["UI"] == "failing"
    assert states["API"] == "passing"


def test_evaluate_one_browser_failing_is_enough_to_fail_ui():
    jobs = [_job("API tests"), _ui(), _job("UI tests (webkit)", "failure")]
    assert ci_status.evaluate({"conclusion": "failure"}, jobs)["UI"] == "failing"


def test_evaluate_cancelled_run_is_unknown_not_failing():
    # Un run cancelado a mano no significa que el código esté roto.
    states = ci_status.evaluate({"conclusion": "cancelled"}, [_job("API tests", "cancelled"), _ui("cancelled", "cancelled")])
    assert set(states.values()) == {"unknown"}


def test_evaluate_missing_jobs_is_unknown_never_passing():
    # Si el workflow cambia de nombres y no encontramos nada, NO se asume "passing".
    states = ci_status.evaluate(RUN_OK, [_job("some other job")])
    assert states["API"] == "unknown"
    assert states["UI"] == "unknown"
    assert states["BDD"] == "unknown"


def test_evaluate_ignores_none_conclusions_from_running_jobs():
    assert ci_status._state([None, None]) == "unknown"


# ---------- caché y fallos ----------

@pytest.fixture(autouse=True)
def clean_cache(monkeypatch):
    monkeypatch.delenv("CI_STATUS_DISABLED", raising=False)
    monkeypatch.setitem(ci_status._cache, "data", None)
    monkeypatch.setitem(ci_status._cache, "fetched_at", 0.0)
    monkeypatch.setitem(ci_status._cache, "refreshing", False)
    monkeypatch.setitem(ci_status._cache, "next_try", 0.0)


def _wait_for_refresh():
    for _ in range(100):
        if not ci_status._cache["refreshing"]:
            return
        time.sleep(0.02)
    raise AssertionError("el refresco en segundo plano no terminó")


def test_first_call_is_unknown_then_data_arrives(monkeypatch):
    good = {"states": {"UI": "passing"}, "run_url": "u", "sha": "abc1234", "finished": "2026-10-06T00:00:00Z"}
    monkeypatch.setattr(ci_status, "_fetch", lambda: good)
    assert ci_status.state_for("UI") == "unknown"  # primer request: aún no hay dato, y no bloquea
    _wait_for_refresh()
    assert ci_status.state_for("UI") == "passing"


def test_github_down_shows_unknown_and_does_not_crash(monkeypatch):
    def boom():
        raise OSError("sin red")

    monkeypatch.setattr(ci_status, "_fetch", boom)
    ci_status.get_status()
    _wait_for_refresh()
    assert ci_status.state_for("UI") == "unknown"
    assert ci_status._cache["next_try"] > time.time()  # no martilla la API tras un error


def test_failed_refresh_keeps_last_good_value(monkeypatch):
    good = {"states": {"UI": "passing"}, "run_url": None, "sha": "abc1234", "finished": None}
    monkeypatch.setattr(ci_status, "_fetch", lambda: good)
    ci_status.get_status()
    _wait_for_refresh()
    # el dato envejece (vencido, pero menor a MAX_STALE) y el siguiente refresco falla
    monkeypatch.setitem(ci_status._cache, "fetched_at", time.time() - ci_status.TTL - 1)
    monkeypatch.setattr(ci_status, "_fetch", lambda: (_ for _ in ()).throw(OSError("caído")))
    assert ci_status.state_for("UI") == "passing"
    _wait_for_refresh()
    assert ci_status.state_for("UI") == "passing"  # se conserva el último dato bueno


def test_data_older_than_max_stale_is_discarded(monkeypatch):
    good = {"states": {"UI": "passing"}, "run_url": None, "sha": "abc1234", "finished": None}
    monkeypatch.setattr(ci_status, "_fetch", lambda: good)
    ci_status.get_status()
    _wait_for_refresh()
    monkeypatch.setitem(ci_status._cache, "fetched_at", time.time() - ci_status.MAX_STALE - 1)
    monkeypatch.setitem(ci_status._cache, "next_try", time.time() + 999)  # que no re-lea
    assert ci_status.state_for("UI") == "unknown"  # nunca se muestra "passing" con un dato demasiado viejo


def test_unknown_tag_is_unknown():
    assert ci_status.state_for("NO-EXISTE") == "unknown"


def test_disabled_env_returns_empty(monkeypatch):
    monkeypatch.setenv("CI_STATUS_DISABLED", "1")
    assert ci_status.get_status() is ci_status.EMPTY
