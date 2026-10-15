"""Pruebas de URLs https, vista previa al compartir, robots.txt y sitemap.xml (QAP-22).

En producción Nginx habla https con el visitante y http con Gunicorn, y envía `X-Forwarded-Proto: https`. Estas pruebas
imitan eso con esa cabecera: sin ella el cliente de pruebas es http y se vería el comportamiento ANTERIOR (URLs con
http://), que es justo el defecto que se corrigió. Lo que NO prueban: que Nginx envíe de verdad la cabecera (se ve en
`nginx/nginx.conf`, ver la última prueba) ni cómo se ve la vista previa en LinkedIn (eso se comprueba a mano).
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from werkzeug.middleware.proxy_fix import ProxyFix

import content
from webhelpers import add_user, csrf_token

ROOT = Path(__file__).resolve().parents[2]
HTTPS = {"X-Forwarded-Proto": "https"}
ALL_PAGES = [(page, lang, paths[lang]) for page, paths in content.PAGES.items() for lang in content.LANGS]
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


def _meta(html, attr, name):
    m = re.search(rf'<meta {attr}="{re.escape(name)}" content="([^"]*)"', html)
    return m.group(1) if m else None


def _link(html, rel):
    m = re.search(rf'<link rel="{rel}" href="([^"]*)"', html)
    return m.group(1) if m else None


# ---------- ProxyFix: las URLs absolutas salen con https detrás de Nginx

def test_proxyfix_trusts_only_the_forwarded_protocol(flask_app):
    fix = flask_app.wsgi_app
    assert isinstance(fix, ProxyFix)
    # X-Forwarded-For NO: request_ip.py usa X-Real-IP porque un cliente puede escribir lo que quiera en X-Forwarded-For.
    assert (fix.x_for, fix.x_proto, fix.x_host, fix.x_port, fix.x_prefix) == (0, 1, 0, 0, 0)


def test_a_forwarded_for_header_does_not_change_the_client_address(client, flask_app):
    seen = {}

    @flask_app.get("/__probe")
    def probe():
        from flask import request
        seen["addr"] = request.remote_addr
        return "ok"

    client.get("/__probe", headers={"X-Forwarded-For": "1.2.3.4", **HTTPS}, environ_overrides={"REMOTE_ADDR": "10.0.0.9"})
    assert seen["addr"] == "10.0.0.9"


def test_the_en_redirect_keeps_https_instead_of_downgrading_to_http(client):
    resp = client.get("/en", headers=HTTPS)          # sin barra final: Flask redirige a /en/
    assert resp.status_code == 308
    assert resp.headers["Location"] == "https://localhost/en/"


def test_without_the_forwarded_header_urls_stay_http_which_is_the_behaviour_that_was_fixed(client):
    assert client.get("/en").headers["Location"].startswith("http://")


@pytest.mark.parametrize("page,lang,path", ALL_PAGES, ids=[f"{p}-{l}" for p, l, _ in ALL_PAGES])
def test_no_page_emits_an_absolute_http_url_behind_the_proxy(client, page, lang, path):
    html = client.get(path, headers=HTTPS).get_data(as_text=True)
    assert not re.search(r'(?:href|content|src)="http://', html)


# ---------- vista previa al compartir (Open Graph / Twitter) y canonical

@pytest.mark.parametrize("page,lang,path", ALL_PAGES, ids=[f"{p}-{l}" for p, l, _ in ALL_PAGES])
def test_every_public_page_has_a_complete_share_preview(client, page, lang, path):
    html = client.get(path, headers=HTTPS).get_data(as_text=True)
    url = f"https://localhost{path}"
    title = re.search(r"<title>(.*?)</title>", html, flags=re.S).group(1)

    assert _link(html, "canonical") == url
    assert _meta(html, "property", "og:url") == url
    assert _meta(html, "property", "og:type") == "website"
    assert _meta(html, "property", "og:title") == title and title.strip()
    assert _meta(html, "property", "og:description") == content.T[lang]["meta_description"]
    assert _meta(html, "property", "og:locale") == ("es_CO" if lang == "es" else "en_US")
    assert _meta(html, "property", "og:locale:alternate") == ("en_US" if lang == "es" else "es_CO")
    assert _meta(html, "name", "twitter:card") == "summary"
    assert _meta(html, "name", "twitter:title") == title
    assert _meta(html, "name", "twitter:description") == content.T[lang]["meta_description"]


def test_the_preview_image_is_an_absolute_https_url_that_really_exists(client):
    html = client.get("/", headers=HTTPS).get_data(as_text=True)
    image = _meta(html, "property", "og:image")
    assert image.startswith("https://localhost/static/img/")
    assert _meta(html, "name", "twitter:image") == image
    assert client.get(image.removeprefix("https://localhost")).status_code == 200


def test_the_declared_image_size_matches_the_real_file(client):
    html = client.get("/", headers=HTTPS).get_data(as_text=True)
    path = ROOT / "app" / "static" / "img" / _meta(html, "property", "og:image").rsplit("/", 1)[1]
    header = path.read_bytes()[16:24]
    width, height = int.from_bytes(header[:4], "big"), int.from_bytes(header[4:], "big")
    assert (str(width), str(height)) == (_meta(html, "property", "og:image:width"), _meta(html, "property", "og:image:height"))


def test_hreflang_links_are_https_and_point_to_both_languages(client):
    html = client.get("/", headers=HTTPS).get_data(as_text=True)
    hrefs = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', html))
    assert hrefs == {"es": "https://localhost/", "en": "https://localhost/en/", "x-default": "https://localhost/"}


# ---------- robots.txt y sitemap.xml

def test_robots_txt_allows_the_site_hides_admin_and_api_and_points_to_the_sitemap(client):
    resp = client.get("/robots.txt", headers=HTTPS)
    assert resp.status_code == 200 and resp.mimetype == "text/plain"
    lines = resp.get_data(as_text=True).splitlines()
    assert "User-agent: *" in lines and "Allow: /" in lines
    assert "Disallow: /admin/" in lines and "Disallow: /api/" in lines
    assert "Sitemap: https://localhost/sitemap.xml" in lines


def _sitemap(client):
    resp = client.get("/sitemap.xml", headers=HTTPS)
    assert resp.status_code == 200 and resp.mimetype == "application/xml"
    return ET.fromstring(resp.get_data())


def test_sitemap_is_valid_xml_and_lists_every_public_page_in_both_languages(client):
    urls = [u.find("sm:loc", NS).text for u in _sitemap(client).findall("sm:url", NS)]
    expected = [f"https://localhost{path}" for _, _, path in ALL_PAGES]
    assert sorted(urls) == sorted(expected) and len(urls) == len(set(urls))


def test_sitemap_never_lists_admin_api_or_the_live_demo_endpoint(client):
    for url in _sitemap(client).findall("sm:url", NS):
        # Por prefijo de ruta: "/proyectos/api-pytest" es una página pública (el caso de estudio de API) y contiene "/api".
        path = url.find("sm:loc", NS).text.removeprefix("https://localhost")
        assert not path.startswith(("/admin", "/api/", "/demos/live", "/en/demos/live")), path


def test_every_sitemap_entry_declares_its_language_alternatives(client):
    for url in _sitemap(client).findall("sm:url", NS):
        alternates = {a.get("hreflang"): a.get("href") for a in url.findall("x:link", NS)}
        assert set(alternates) == {"es", "en", "x-default"}
        assert all(href.startswith("https://localhost/") for href in alternates.values())


def test_every_listed_page_really_answers_200(client):
    for url in _sitemap(client).findall("sm:url", NS):
        path = url.find("sm:loc", NS).text.removeprefix("https://localhost")
        assert client.get(path).status_code == 200, path


# ---------- efecto colateral de que Flask vea https: Flask-WTF exige Referer del mismo sitio (QAP-22)

def test_login_still_works_behind_the_proxy_when_the_browser_sends_its_referer(make_app):
    app = make_app()
    add_user(app)
    client = app.test_client()
    token = csrf_token(client)
    resp = client.post("/admin/login", data={"username": "admin", "password": "clave-solo-para-pruebas", "csrf_token": token},
                       headers={**HTTPS, "Referer": "https://localhost/admin/login"})
    assert resp.status_code == 302


def test_a_post_without_referer_is_now_rejected_because_the_request_is_https(make_app):
    # Documenta el efecto: es el comportamiento seguro y el navegador SIEMPRE manda Referer al mismo origen con la
    # política strict-origin-when-cross-origin que pone Nginx (comprobado en la última prueba).
    app = make_app()
    add_user(app)
    client = app.test_client()
    token = csrf_token(client)
    resp = client.post("/admin/login", data={"username": "admin", "password": "clave-solo-para-pruebas", "csrf_token": token},
                       headers=HTTPS)
    assert resp.status_code == 400


# ---------- lo que no se puede arrancar aquí: Nginx

def test_nginx_forwards_the_scheme_and_does_not_strip_the_referer_on_same_origin_posts():
    conf = (ROOT / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    assert re.search(r"proxy_set_header X-Forwarded-Proto \$scheme;", conf)
    assert re.search(r'add_header Referrer-Policy "strict-origin-when-cross-origin" always;', conf)
    assert "no-referrer" not in conf
