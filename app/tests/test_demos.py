"""Pruebas de la página de demos de IA (ejemplos reales pregenerados).

Lo que más importa proteger aquí es la HONESTIDAD de la página (regla del
proyecto, ver CLAUDE.md "Enfoque de IA del portafolio"): estos ejemplos nunca
deben presentarse como resultados en vivo, y siempre deben decir qué modelo
los generó.

Correr:  python -m pytest app/tests -q
"""
import html as html_lib
import re

import pytest

import demo_content
from app import app

LANGS = ("es", "en")
PATHS = {"es": "/demos", "en": "/en/demos"}


@pytest.fixture(scope="module")
def client():
    return app.test_client()


def _page(client, lang):
    resp = client.get(PATHS[lang])
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


# ---------- la página existe y es honesta

@pytest.mark.parametrize("lang", LANGS)
def test_demos_page_renders_and_states_it_is_not_live(client, lang):
    page = _page(client, lang)
    needle = "no en vivo" if lang == "es" else "not live"
    assert needle in page.lower()


@pytest.mark.parametrize("lang", LANGS)
def test_demos_page_names_the_model_that_generated_the_answers(client, lang):
    page = _page(client, lang)
    assert demo_content.MODEL["name"] in page
    assert demo_content.MODEL["date"] in page


@pytest.mark.parametrize("lang", LANGS)
def test_demos_page_has_no_free_text_input_that_would_imply_live_mode(client, lang):
    # Sin <form>, <textarea> ni <input>: un cuadro de entrada insinuaría que lo que se
    # escribe se procesa en el momento, y no es así.
    page = _page(client, lang).lower()
    assert "<form" not in page
    assert "<textarea" not in page
    assert "<input" not in page


@pytest.mark.parametrize("lang", LANGS)
def test_demos_page_never_claims_live_generation(client, lang):
    # Se ignoran los avisos que dicen "no en vivo / not live" y se busca cualquier otra
    # afirmación de generación en vivo en el HTML visible.
    page = re.sub(r"<[^>]+>", " ", _page(client, lang)).lower()
    page = page.replace("no en vivo", "").replace("not live", "")
    assert "en vivo" not in page.replace("modo en vivo", "")
    assert "live demo" not in page.replace("live mode", "")


@pytest.mark.parametrize("lang", LANGS)
def test_demos_page_is_linked_from_the_menu(client, lang):
    home = client.get("/" if lang == "es" else "/en/").get_data(as_text=True)
    assert f'href="{PATHS[lang]}"' in home


# ---------- el contenido está completo en los dos idiomas

@pytest.mark.parametrize("key", demo_content.DEMO_ORDER)
def test_every_demo_has_examples_in_both_languages_with_the_same_ids(key):
    ids = {lang: [ex["id"] for ex in demo_content.EXAMPLES[key][lang]] for lang in LANGS}
    assert ids["es"] and ids["es"] == ids["en"]


@pytest.mark.parametrize("lang", LANGS)
def test_every_demo_has_ui_texts_in_both_languages(lang):
    for key in demo_content.DEMO_ORDER:
        entry = demo_content.UI[lang]["demos"][key]
        assert entry["name"] and entry["what"]


@pytest.mark.parametrize("lang", LANGS)
def test_every_example_has_title_input_and_output(lang):
    for key in demo_content.DEMO_ORDER:
        for ex in demo_content.EXAMPLES[key][lang]:
            assert ex["title"].strip() and ex["input"].strip(), (key, ex["id"])
            assert ex["output"], (key, ex["id"])


def test_test_cases_are_well_formed():
    for lang in LANGS:
        for ex in demo_content.EXAMPLES["testcases"][lang]:
            for case in ex["output"]["cases"]:
                assert case["id"] and case["title"] and case["expected"]
                assert case["steps"], (ex["id"], case["id"])
            assert ex["output"]["questions"]


def test_api_examples_declare_how_they_were_validated():
    for lang in LANGS:
        for ex in demo_content.EXAMPLES["apitests"][lang]:
            assert ex["run"], ex["id"]
            assert "def test_" in ex["output"]["code"]


# ---------- seguridad del render

@pytest.mark.parametrize("lang", LANGS)
def test_example_text_is_escaped_not_injected_as_html(client, lang):
    # Un traceback real contiene "<module>": debe salir escapado, nunca como etiqueta.
    page = _page(client, lang)
    assert "in &lt;module&gt;" in page
    assert "in <module>" not in page


def test_content_with_html_is_escaped(monkeypatch, client):
    monkeypatch.setitem(
        demo_content.EXAMPLES["bugs"]["es"][0], "input", "<script>alert('xss')</script>"
    )
    page = _page(client, "es")
    assert "<script>alert('xss')</script>" not in page
    assert html_lib.escape("<script>alert('xss')</script>") in page or "&lt;script&gt;" in page


# ---------- verificación manual contra la API real (requiere red; no corre por defecto)

@pytest.mark.network
def test_api_examples_run_against_real_api(tmp_path):
    """Ejecuta EXACTAMENTE el código que muestra la página contra la API real.

    Se corre a mano antes de publicar un cambio en los ejemplos:
        python -m pytest app/tests -q -m network
    """
    import subprocess
    import sys

    for ex in demo_content.EXAMPLES["apitests"]["en"]:
        path = tmp_path / f"test_{ex['id']}.py"
        path.write_text(ex["output"]["code"], encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(path), "-q", "-p", "no:cacheprovider",
             "-p", "no:allure_pytest", "-p", "no:allure_pytest_bdd"],
            capture_output=True, text=True, timeout=180,
        )
        assert ex["run"] in result.stdout, (ex["id"], result.stdout[-400:])
