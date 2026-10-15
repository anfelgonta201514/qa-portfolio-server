"""Pruebas de la redacción de la cobertura de regresión (QAP-25).

El texto decía «subió la cobertura un 60%, hasta el 75%» (y el KPI «+60% de regresión automatizada»), que sugería +60 puntos.
Lo exacto, según Andres (2026-10-14): el 60% era lo que la regresión automatizada ya cubría ANTES, el 75% lo que se llegó a
cubrir, y hoy ronda el 90% (a la release actual; varía si el producto crece más rápido que la automatización). Estas pruebas
mantienen coherentes los 6 sitios donde aparece (portada, KPI y viñeta de FLYR, en ES y EN) y vigilan que no vuelva la
formulación inexacta. Lo que NO prueban: que las cifras sean ciertas (solo Andres lo sabe) ni que el PDF del CV coincida
(es otro archivo, lo regenera Andres).
"""
import re

import pytest

import content

LANGS = ("es", "en")
HTTPS = {"X-Forwarded-Proto": "https"}
COVERAGE_KPI = {"es": "Flujos críticos cubiertos", "en": "Critical flows covered"}
CYCLE_KPI = {"es": "Ciclo de regresión", "en": "Regression cycle"}


def _kpi(lang, label):
    return next(k for k in content.KPIS[lang] if k[0] == label)


def _first_flyr_bullet(lang):
    return content.JOBS[lang][0]["points"][0]


@pytest.mark.parametrize("lang", LANGS)
def test_the_kpi_shows_the_current_coverage_and_says_where_it_started(lang):
    _, value, caption = _kpi(lang, COVERAGE_KPI[lang])
    assert value == "~90%"
    assert "~60%" in caption


@pytest.mark.parametrize("lang", LANGS)
def test_the_flyr_bullet_tells_the_whole_story_60_to_75_and_now_90(lang):
    bullet = _first_flyr_bullet(lang)
    assert "~60%" in bullet and "75%" in bullet and "90%" in bullet
    assert bullet.index("~60%") < bullet.index("75%") < bullet.index("90%")
    assert "release" in bullet, "el 90% debe decir que es a la release actual"


@pytest.mark.parametrize("lang", LANGS)
def test_the_home_summary_uses_the_current_figure_not_the_old_75(lang):
    text = content.T[lang]["current_text"]
    assert "~90%" in text and "75%" not in text


@pytest.mark.parametrize("lang", LANGS)
def test_the_misleading_plus_60_phrasing_does_not_come_back(lang):
    texts = [content.T[lang]["current_text"], *(" ".join(k) for k in content.KPIS[lang])]
    texts += [p for job in content.JOBS[lang] for p in job["points"]]
    for text in texts:
        assert not re.search(r"\+60%", text), text
        assert not re.search(r"subió la cobertura|increased automated regression coverage by 60", text, flags=re.I), text


@pytest.mark.parametrize("lang", LANGS)
def test_the_regression_cycle_figure_is_untouched_because_it_is_a_different_number(lang):
    _, value, caption = _kpi(lang, CYCLE_KPI[lang])
    assert value == "1h → 24m" and "−60%" in caption
    assert "60% (de 1h a 24 min)" in content.JOBS["es"][0]["points"][1]
    assert "60% (from 1h to 24 min)" in content.JOBS["en"][0]["points"][1]


@pytest.mark.parametrize("path,lang", [("/", "es"), ("/en/", "en")])
def test_the_home_page_renders_the_new_figure_and_no_longer_the_old_kpi(flask_app, path, lang):
    html = flask_app.test_client().get(path, headers=HTTPS).get_data(as_text=True)
    assert "~90%" in html
    assert "+60%" not in html


@pytest.mark.parametrize("path,fragment", [("/experiencia", "del ~60% al 75%"), ("/en/experience", "from ~60% to 75%")])
def test_the_experience_page_renders_the_corrected_bullet(flask_app, path, fragment):
    assert fragment in flask_app.test_client().get(path, headers=HTTPS).get_data(as_text=True)
