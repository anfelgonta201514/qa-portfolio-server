"""Pruebas del menú lateral del sitio público (QAP-24).

Regresión: «Este sitio» llevaba la etiqueta «pronto» aunque su sección (#arquitectura en la portada) ya existía.
Lo que NO prueban: cómo se ve el menú (se revisó a mano) ni que el contenido de cada página sea el adecuado.
"""
import re

import pytest

import content

HTTPS = {"X-Forwarded-Proto": "https"}
PAGES = [(page, lang, paths[lang]) for page, paths in content.PAGES.items() for lang in content.LANGS]


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


def _nav(html):
    block = re.search(r'<nav class="side-nav".*?</nav>', html, flags=re.S)
    assert block, "no hay menú lateral"
    return block.group(0)


@pytest.mark.parametrize("page,lang,path", PAGES, ids=[f"{p}-{l}" for p, l, _ in PAGES])
def test_no_menu_entry_is_marked_as_coming_soon(client, page, lang, path):
    nav = _nav(client.get(path, headers=HTTPS).get_data(as_text=True))
    assert 'class="soon"' not in nav
    assert not re.search(r"\b(pronto|soon)\b", re.sub(r"<[^>]+>", " ", nav), flags=re.I)


@pytest.mark.parametrize("lang,path", [("es", "/"), ("en", "/en/")])
def test_every_menu_link_points_to_something_that_exists(client, lang, path):
    links = re.findall(r'<a href="([^"]+)"', _nav(client.get(path, headers=HTTPS).get_data(as_text=True)))
    assert len(links) == 5
    for href in links:
        target, _, fragment = href.partition("#")
        page = client.get(target or path, headers=HTTPS)
        assert page.status_code == 200, href
        if fragment:
            assert f'id="{fragment}"' in page.get_data(as_text=True), f"{href}: no existe el ancla"


def test_the_this_site_entry_leads_to_its_real_section_in_both_languages(client):
    for path, label in (("/", content.T["es"]["nav_site"]), ("/en/", content.T["en"]["nav_site"])):
        html = client.get(path, headers=HTTPS).get_data(as_text=True)
        assert re.search(rf'<a href="{re.escape(path)}#arquitectura">.*?<span>{re.escape(label)}</span>', _nav(html), flags=re.S)
        assert 'id="arquitectura"' in html
