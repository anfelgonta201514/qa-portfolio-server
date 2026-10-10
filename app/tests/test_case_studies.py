"""Pruebas de los casos de estudio de API, CI/CD y BDD (QAP-9).

Protegen tres cosas: que las páginas existan y sean iguales en ES y EN, que los enlaces entre casos formen el recorrido
previsto, y -lo más importante para un portafolio- que lo que se afirma sea verificable: los fragmentos de código son copia
literal de archivos de qa-automation-portfolio y las cifras coinciden con ese repo. Esas dos últimas comprobaciones solo
corren cuando el repo hermano está en la carpeta de al lado (en la máquina de Andres sí; en CI se omiten).
"""
import re
from pathlib import Path

import pytest

import case_studies
import content
from webhelpers import add_project

LANGS = ("es", "en")
KEYS = ("case_api", "case_ci", "case_bdd")
SIBLING = Path(__file__).resolve().parents[3] / "qa-automation-portfolio"
needs_sibling = pytest.mark.skipif(not SIBLING.is_dir(), reason="qa-automation-portfolio no está en la carpeta de al lado")


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


def page(client, key, lang):
    resp = client.get(content.PAGES[key][lang])
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


# ---------- las páginas existen, en los dos idiomas

@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("key", KEYS)
def test_each_case_study_page_renders_with_its_title_and_the_live_ci_badge(client, key, lang):
    html = page(client, key, lang)
    c = case_studies.CASES[lang][key]

    assert f"<h1" in html and c["tag"] in html
    assert c["short"] in html
    assert "ci-badge" in html                          # el estado real del CI, no un texto fijo
    assert f'hreflang="{"en" if lang == "es" else "es"}"' in html


@pytest.mark.parametrize("key", KEYS)
def test_spanish_and_english_have_the_same_structure(key):
    es, en = case_studies.CASES["es"][key], case_studies.CASES["en"][key]
    assert set(es) == set(en)
    for field in ("meta", "decisions", "steps", "kpis", "limits", "struggles", "table"):
        assert len(es.get(field, [])) == len(en.get(field, [])), field
    assert es["snippet"] == en["snippet"]                              # el código es el mismo en los dos idiomas
    assert es["slug"] == en["slug"]
    numbers = lambda c: [re.findall(r"\d+", v) for _, v, *_ in c["kpis"]]      # "1 de 2" y "1 of 2" son la misma cifra
    assert numbers(es) == numbers(en)
    assert [h for *_, h in es["meta"]] == [h for *_, h in en["meta"]]            # mismos enlaces


@pytest.mark.parametrize("lang", LANGS)
def test_every_text_field_of_every_case_is_filled(lang):
    for key in KEYS:
        c = case_studies.CASES[lang][key]
        for field in ("short", "tag", "h1", "lead", "problem", "approach", "snippet", "snippet_note", "snippet_href",
                      "limits_title"):
            assert c[field].strip(), (key, field)
        assert c["limits"] and c["decisions"] and c["kpis"] and c["steps"]


# ---------- recorrido entre casos

CHAIN = ["case_ui", "case_api", "case_ci", "case_bdd", "demos"]


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("i", range(1, 4))
def test_the_pager_links_each_case_to_the_previous_and_the_next(client, i, lang):
    key = CHAIN[i]
    html = page(client, key, lang)
    prev_href, next_href = content.PAGES[CHAIN[i - 1]][lang], content.PAGES[CHAIN[i + 1]][lang]

    nav = html[html.index('<nav class="pager">'):]
    assert f'href="{prev_href}"' in nav and f'href="{next_href}"' in nav


@pytest.mark.parametrize("lang", LANGS)
def test_the_ui_case_now_links_to_the_api_case_instead_of_saying_soon(client, lang):
    html = page(client, "case_ui", lang)
    assert f'href="{content.PAGES["case_api"][lang]}"' in html
    assert "pronto" not in html.lower().split('<nav class="pager">')[1] and "soon" not in html.lower().split('<nav class="pager">')[1]


@pytest.mark.parametrize("key", KEYS)
def test_the_projects_menu_entry_is_highlighted_on_every_case_study(client, key):
    html = page(client, key, "es")
    assert re.search(r'<a href="/proyectos/ui-playwright" aria-current="page">', html)


# ---------- las tarjetas de proyectos enlazan a su caso, no a "pronto"

def test_every_project_card_links_to_its_case_study_when_the_projects_come_from_the_seed(flask_app):
    import seed  # noqa: F401  (siembra los 4 proyectos reales en la base de la app por defecto)
    from app import app as seeded_app
    html = seeded_app.test_client().get("/").get_data(as_text=True)

    for key in ("case_ui",) + KEYS:
        assert f'href="{content.PAGES[key]["es"]}"' in html, key
    assert "Caso de estudio pronto" not in html


def test_the_repo_urls_of_the_seeded_projects_all_have_a_case_page():
    import seed
    urls = {p["repo_url"] for p in seed.PROJECTS}
    assert urls <= set(content.CASE_STUDIES), urls - set(content.CASE_STUDIES)
    assert {content.CASE_STUDIES[u] for u in urls} == {"case_ui", *KEYS}


# ---------- enlaces y escape

ALLOWED_PREFIXES = ("https://github.com/anfelgonta201514/", "https://restful-booker.herokuapp.com/")


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("key", KEYS)
def test_external_links_in_the_case_are_the_expected_ones_and_open_safely(client, key, lang):
    html = page(client, key, lang)
    body = html[html.index('<section class="card hero-case">'):html.index('<nav class="pager">')]
    anchors = re.findall(r'<a href="(https?://[^"]+)"([^>]*)>', body)

    assert anchors
    for href, attrs in anchors:
        assert href.startswith(ALLOWED_PREFIXES), f"enlace externo inesperado: {href}"
        assert 'target="_blank"' in attrs and 'rel="noopener noreferrer"' in attrs, href


def test_the_ci_snippet_shows_the_workflow_expression_literally(client):
    html = page(client, "case_ci", "es")
    assert "UI tests (${{ matrix.browser }})" in html            # no lo interpreta Jinja: sale tal cual


@pytest.mark.parametrize("key", KEYS)
def test_the_snippets_have_no_markup_that_would_be_interpreted(client, key):
    snippet = case_studies.CASES["es"][key]["snippet"]
    html = page(client, key, "es")
    assert "<script" not in snippet.lower()
    code = html.split('<pre class="code"><code>')[1].split("</code></pre>")[0]
    assert code.count("\n") == snippet.count("\n")


# ---------- honestidad: lo que se afirma se puede comprobar

def test_the_checked_date_is_stated_where_numbers_were_measured():
    for lang in LANGS:
        api = case_studies.CASES[lang]["case_api"]
        assert case_studies.CHECKED in " ".join(sub for *_, sub in api["kpis"])
        ci = case_studies.CASES[lang]["case_ci"]
        assert case_studies.CHECKED in " ".join(sub for *_, sub in ci["kpis"]) and case_studies.CHECKED in ci["history"]


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("key", KEYS)
def test_every_case_states_its_limits(client, key, lang):
    html = page(client, key, lang)
    assert case_studies.CASES[lang][key]["limits_title"] in html
    assert html.count("<li>") >= 2


@needs_sibling
@pytest.mark.parametrize("key", sorted(case_studies.SNIPPET_SOURCES))
def test_each_snippet_is_a_literal_copy_of_a_file_of_the_tests_repo(key):
    rel, snippet = case_studies.SNIPPET_SOURCES[key]
    source = (SIBLING / rel).read_text(encoding="utf-8").replace("\r\n", "\n")
    assert snippet in source, f"{rel} cambió: hay que actualizar el fragmento de case_studies.py"


@needs_sibling
def test_the_api_test_counts_shown_match_the_repo():
    tests = SIBLING / "api-tests" / "restful-booker" / "tests"
    counts = {f.name: len(re.findall(r"^def test_", f.read_text(encoding="utf-8"), flags=re.M)) for f in tests.glob("test_*.py")}
    assert sum(counts.values()) == 10
    assert (counts["test_auth.py"], counts["test_booking_crud.py"], counts["test_negative_cases.py"]) == (2, 5, 3)
    assert case_studies.CASES["es"]["case_api"]["kpis"][0][1] == "10"


@needs_sibling
def test_the_non_rest_behaviors_listed_are_pinned_by_tests_in_the_repo():
    text = "".join(f.read_text(encoding="utf-8") for f in (SIBLING / "api-tests" / "restful-booker" / "tests").glob("test_*.py"))
    for needle in ("201", "500", "403", "Bad credentials"):
        assert needle in text, f"ningún test del repo fija {needle}"
    assert len(case_studies.CASES["es"]["case_api"]["table"]) == int(case_studies.CASES["es"]["case_api"]["kpis"][1][1])


@needs_sibling
def test_the_ci_facts_match_the_workflow():
    wf = (SIBLING / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "browser: [chromium, firefox, webkit]" in wf and "fail-fast: false" in wf
    assert wf.count("continue-on-error: true") == 2                      # reserva y BDD de reserva
    assert "workflow_dispatch" in wf and "type=gha" in wf
    assert "playwright/python:v" in (SIBLING / "Dockerfile").read_text(encoding="utf-8")


@needs_sibling
def test_the_bdd_facts_match_the_repo():
    features = sorted((SIBLING / "ui-tests" / "booking-flow" / "features").glob("*.feature"))
    assert [f.name for f in features] == ["admin_room.feature", "booking.feature"]
    assert sum(f.read_text(encoding="utf-8").count("Scenario:") for f in features) == 2


def _repo_links(lang):
    """(enlace, ruta dentro del repo) de todos los enlaces a GitHub de los tres casos."""
    out = []
    for key in KEYS:
        c = case_studies.CASES[lang][key]
        hrefs = [h for *_, h in c["meta"] if h] + [c["snippet_href"], c.get("extra_href")]
        for href in filter(None, hrefs):
            m = re.match(r"https://github\.com/anfelgonta201514/([\w-]+)/(?:tree|blob)/(?:master|main)/(.+)$", href)
            if m:
                out.append((href, m.group(1), m.group(2)))
    return out


@pytest.mark.parametrize("lang", LANGS)
def test_every_github_link_points_to_a_path_that_exists_in_that_repo(lang):
    links = _repo_links(lang)
    assert len(links) == 7                      # 2 de API + 3 de CI/CD + 2 de BDD: si baja, el detector está roto
    repo_root = Path(__file__).resolve().parents[2]
    for href, repo, path in links:
        if repo == "qa-portfolio-server":
            assert (repo_root / path).exists(), f"{href}: no existe {path} en este repo"
        elif SIBLING.is_dir():
            assert (SIBLING / path).exists(), f"{href}: no existe {path} en qa-automation-portfolio"


# ---------- móvil y datos de la página de UI

CSS = (Path(__file__).resolve().parents[1] / "static" / "site.css").read_text(encoding="utf-8")


def test_the_single_column_grids_on_mobile_cannot_be_stretched_by_long_content():
    # `1fr` equivale a minmax(auto, 1fr): un fragmento de código largo ensanchaba la página entera en el móvil
    # (los casos de estudio medían 455-732 px en un móvil de 375). Con minmax(0, 1fr) la columna puede encoger.
    media = CSS[CSS.index("@media (max-width: 960px)"):CSS.index("@media (max-width: 560px)")]
    assert re.search(r"\.two-col, \.three-col, \.case-meta, \.project-grid \{ grid-template-columns: minmax\(0, 1fr\); \}", media)
    assert not re.search(r"grid-template-columns: 1fr;", media)


def test_code_blocks_wrap_instead_of_forcing_a_wide_page():
    assert re.search(r"pre\.code \{[^}]*white-space: pre-wrap;[^}]*overflow-wrap: anywhere;", CSS)


def test_the_api_table_has_data_labels_so_it_can_turn_into_cards_on_mobile(client):
    html = page(client, "case_api", "es")
    assert html.count('data-label="Lo que esperaría REST"') == 6 and html.count('data-label="Lo que responde"') == 6
    assert "attr(data-label)" in CSS


@pytest.mark.parametrize("lang", LANGS)
def test_the_ui_case_study_counts_match_the_suite_and_do_not_claim_the_old_number(client, lang):
    html = page(client, "case_ui", lang)
    assert '<span class="kpi-value">15</span>' in html and '<span class="kpi-value">8</span>' not in html
    assert ("6 escenarios + 9 filas" in html) or ("6 scenarios + 9 rows" in html)
