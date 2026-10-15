"""Pruebas del contenido de las tarjetas de proyectos (QAP-23: semanas 8-14).

El contenido vive en la BASE de datos y se carga con `app/seed.py`; las traducciones al inglés y las etiquetas, en
`content.py`, con el TÍTULO como clave. Si un título cambia en un sitio y no en el otro, la tarjeta sale sin traducir o con
la etiqueta genérica "QA" y nadie se entera: estas pruebas lo vigilan. `seed.py` ejecuta la base al importarse, así que
se lee con `ast` sin importarlo. Lo que NO prueban: que el texto sea cierto (eso se verificó contra el repo, Jira y
producción al redactarlo) ni que las filas existan en la base de producción (el deploy no ejecuta el seed).
"""
import ast
import html
import re
from pathlib import Path

import pytest

import content
from public import CI_TAGS
from webhelpers import add_project

ROOT = Path(__file__).resolve().parents[2]
SERVER_REPO = "https://github.com/anfelgonta201514/qa-portfolio-server"


def _seed_projects():
    tree = ast.parse((ROOT / "app" / "seed.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PROJECTS":
            return ast.literal_eval(node.value)
    raise AssertionError("no se encontró PROJECTS en seed.py")


SEED = _seed_projects()
OLD = [p for p in SEED if p["week"] <= 7]
NEW = [p for p in SEED if p["week"] >= 8]
CARD = re.compile(r'<a class="card project-card" href="([^"]*)"(.*?)</a>', re.S)


@pytest.fixture
def site(flask_app):
    for p in SEED:
        add_project(flask_app, p["title"], p["description"], p["tech_stack"], p["week"], p["repo_url"])
    return flask_app.test_client()


def _cards(client, path):
    page = client.get(path).get_data(as_text=True)
    cards = []
    for href, body in CARD.findall(page):
        cards.append({
            "href": html.unescape(href),
            "tag": re.search(r'<span class="pill">([^<]*)</span>', body).group(1),
            "title": html.unescape(re.search(r'<span class="project-title">(.*?)</span>', body, re.S).group(1)),
            "badge": "ci-badge" in body,
            "body": body,
        })
    return cards


# ---------- el seed

def test_the_seed_has_the_four_original_cards_and_the_six_new_ones():
    assert len(OLD) == 4 and len(NEW) == 6 and len(SEED) == 10


def test_seed_titles_are_unique_because_the_seed_and_the_translations_key_on_them():
    titles = [p["title"] for p in SEED]
    assert len(titles) == len(set(titles))


def test_cards_are_listed_in_week_order_so_the_site_order_matches_the_seed():
    weeks = [p["week"] for p in SEED]
    assert weeks == sorted(weeks)


@pytest.mark.parametrize("p", NEW, ids=[p["title"][:30] for p in NEW])
def test_new_cards_fit_their_columns_and_read_like_the_existing_ones(p):
    assert 0 < len(p["title"]) <= 120                       # Project.title es String(120)
    assert 150 <= len(p["description"]) <= 700              # no más corta que una frase, no un muro de texto
    assert len(p["tech_stack"]) <= 255                      # Project.tech_stack es String(255)
    stack = [s.strip() for s in p["tech_stack"].split(",")]
    assert 3 <= len(stack) <= 7 and all(stack)


@pytest.mark.parametrize("p", NEW, ids=[p["title"][:30] for p in NEW])
def test_new_cards_link_to_something_that_exists_in_this_repo(p):
    url = p["repo_url"]
    assert url == SERVER_REPO or url.startswith(SERVER_REPO + "/"), url
    m = re.match(re.escape(SERVER_REPO) + r"/(?:blob|tree)/main/(.+)$", url)
    if m:
        assert (ROOT / m.group(1)).exists(), f"{m.group(1)} no existe en el repo"


# ---------- traducciones y etiquetas (clave: el título)

def test_every_seed_title_has_an_english_translation():
    missing = [p["title"] for p in SEED if p["title"] not in content.PROJECT_EN]
    assert not missing, f"sin traducción: {missing}"


def test_new_translations_are_really_translated_not_copied():
    for p in NEW:
        en_title, en_description = content.PROJECT_EN[p["title"]]
        assert en_title != p["title"] and en_description != p["description"]
        # Ni una letra propia del español en el texto inglés (los textos en inglés no llevan ningún acento).
        assert not re.search(r"[¿¡ñáéíóúü]", en_title + en_description, flags=re.I), (en_title, en_description[:60])


def test_new_cards_have_their_own_tag_and_none_is_a_ci_tag():
    assert set(content.PROJECT_TAG_BY_TITLE) == {p["title"] for p in NEW}, "una etiqueta sobra o falta"
    for title, tag in content.PROJECT_TAG_BY_TITLE.items():
        assert tag and tag not in CI_TAGS, f"{title}: {tag} llevaría la insignia de CI de otro repo"


# ---------- cómo se ven en la portada

@pytest.mark.parametrize("path", ["/", "/en/"])
def test_the_home_page_shows_ten_cards_in_the_seed_order(site, path):
    cards = _cards(site, path)
    assert len(cards) == 10
    assert [c["tag"] for c in cards][:4] == ["UI", "API", "CI/CD", "BDD"]
    assert [c["tag"] for c in cards][4:] == [content.PROJECT_TAG_BY_TITLE[p["title"]] for p in NEW]


@pytest.mark.parametrize("path", ["/", "/en/"])
def test_only_the_ci_cards_show_the_ci_badge(site, path):
    cards = _cards(site, path)
    assert all(c["badge"] for c in cards[:4]), "las 4 tarjetas de CI conservan su insignia"
    assert not any(c["badge"] for c in cards[4:]), "una tarjeta sin CI mostraría «sin datos», que confunde"


def test_without_ci_data_the_old_cards_still_say_unknown_instead_of_losing_the_badge(site):
    # En pruebas el CI está desactivado: los estados están vacíos y las 4 tarjetas antiguas deben seguir con "unknown".
    assert all("ci-unknown" in c["body"] for c in _cards(site, "/")[:4])


def test_the_english_page_shows_the_translated_titles_and_none_of_the_spanish_ones(site):
    titles = [c["title"] for c in _cards(site, "/en/")[4:]]
    assert titles == [content.PROJECT_EN[p["title"]][0] for p in NEW]
    assert not set(titles) & {p["title"] for p in NEW}


def test_the_spanish_page_shows_the_spanish_titles(site):
    assert [c["title"] for c in _cards(site, "/")[4:]] == [p["title"] for p in NEW]


@pytest.mark.parametrize("path", ["/", "/en/"])
def test_new_cards_open_their_code_in_a_new_tab_and_have_no_case_study_page(site, path):
    for card, p in zip(_cards(site, path)[4:], NEW):
        assert card["href"] == p["repo_url"]
        assert 'target="_blank"' in card["body"] and 'rel="noopener noreferrer"' in card["body"]


def test_the_projects_api_lists_the_ten_cards(site):
    assert len(site.get("/api/projects").get_json()) == 10


@pytest.mark.parametrize("path,label", [("/", "Ver código"), ("/en/", "View code")])
def test_new_cards_say_view_code_and_never_promise_a_case_study_that_will_not_exist(site, path, label):
    # Regresión: la etiqueta decía "Caso de estudio pronto · ver código" (de cuando los casos aún no existían).
    for card in _cards(site, path)[4:]:
        assert label in card["body"]
        assert "pronto" not in card["body"].lower() and "soon" not in card["body"].lower()
