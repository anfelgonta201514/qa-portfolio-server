"""Pruebas de la configuración de seguridad (QAP-21; casos TC-SEC-01 y TC-SEC-02 de docs/qe/plan-de-pruebas.md).

Cubren los hallazgos H4 (la cookie de sesión no declaraba SameSite ni Secure) y H7 (el sitio no enviaba cabeceras de
seguridad). Las cabeceras las pone Nginx, que no se puede arrancar en estas pruebas: aquí se lee `nginx/nginx.conf` como
texto y se comprueba que dice lo que debe, y que la CSP coincide con lo que las plantillas usan de verdad. La
comprobación sobre la RESPUESTA real de producción está en el workflow de deploy (paso "Security headers") y, para la
cookie, en la verificación manual del ticket.
"""
import re
from pathlib import Path

import pytest

from webhelpers import add_user, csrf_token

ROOT = Path(__file__).resolve().parents[2]
NGINX = ROOT / "nginx" / "nginx.conf"
TEMPLATES = ROOT / "app" / "templates"


# ---------- cookies de sesión (TC-SEC-01 / H4)

def _https(client):
    """Cliente cuyas peticiones van por https (como las ve el navegador del visitante): así una cookie Secure vuelve."""
    for verb in ("get", "post"):
        setattr(client, verb, _with_base_url(getattr(client, verb)))
    return client


def _with_base_url(fn):
    return lambda *a, **kw: fn(*a, base_url="https://localhost", **kw)


def _set_cookie_headers(resp):
    return resp.headers.getlist("Set-Cookie")


@pytest.fixture
def prod_like_app(make_app):
    """App con la configuración de cookies de PRODUCCIÓN (sin SESSION_COOKIE_SECURE definida)."""
    app = make_app(SESSION_COOKIE_SECURE="")
    add_user(app)
    return app


def test_session_cookie_config_in_production_is_secure_httponly_and_lax(prod_like_app):
    for prefix in ("SESSION", "REMEMBER"):
        assert prod_like_app.config[f"{prefix}_COOKIE_SECURE"] is True
        assert prod_like_app.config[f"{prefix}_COOKIE_HTTPONLY"] is True
        assert prod_like_app.config[f"{prefix}_COOKIE_SAMESITE"] == "Lax"


def test_the_session_cookie_that_the_login_really_sends_carries_the_three_flags(prod_like_app):
    client = _https(prod_like_app.test_client())
    token = csrf_token(client)

    # Flask-WTF exige Referer en peticiones https (WTF_CSRF_SSL_STRICT); un navegador real lo manda.
    resp = client.post("/admin/login", data={"username": "admin", "password": "clave-solo-para-pruebas", "csrf_token": token},
                       headers={"Referer": "https://localhost/admin/login"})

    assert resp.status_code == 302
    cookie = next(c for c in _set_cookie_headers(resp) if c.startswith("session="))
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie


def test_the_cookie_is_not_sent_back_over_plain_http_so_a_downgraded_request_has_no_session(prod_like_app):
    client = prod_like_app.test_client()                     # http
    client.get("/admin/login")                               # el servidor intenta fijar su cookie...
    # ...pero al ser Secure el cliente no la devuelve por http: no hay sesión y el token CSRF no se puede validar
    assert client.post("/admin/login", data={"username": "admin", "password": "x", "csrf_token": "cualquiera"}).status_code == 400


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "FALSE"])
def test_secure_can_be_turned_off_only_explicitly_for_local_http_development(make_app, value):
    app = make_app(SESSION_COOKIE_SECURE=value)
    assert app.config["SESSION_COOKIE_SECURE"] is False
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True and app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


@pytest.mark.parametrize("value", ["", "1", "true", "quizas", "2"])
def test_any_other_value_keeps_secure_on(make_app, value):
    assert make_app(SESSION_COOKIE_SECURE=value).config["SESSION_COOKIE_SECURE"] is True


# ---------- cabeceras de Nginx (TC-SEC-02 / H7)

def _strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _server_blocks(text):
    """Cuerpo de cada bloque `server { ... }` (con llaves emparejadas)."""
    blocks, i = [], 0
    while True:
        m = re.search(r"\bserver\s*\{", text[i:])
        if not m:
            return blocks
        start = i + m.end()
        depth, j = 1, start
        while depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        blocks.append(text[start:j - 1])
        i = j


@pytest.fixture(scope="module")
def servers():
    blocks = _server_blocks(_strip_comments(NGINX.read_text(encoding="utf-8")))
    by_port = {}
    for b in blocks:
        by_port[re.search(r"listen\s+(\d+)", b).group(1)] = b
    assert set(by_port) == {"80", "443"}, "se esperaban exactamente un server en 80 y otro en 443"
    return by_port


def _headers(block):
    """{nombre: valor} de los add_header del bloque (y si llevan `always`)."""
    out = {}
    for m in re.finditer(r'add_header\s+(\S+)\s+"([^"]*)"\s*(always)?\s*;', block):
        out[m.group(1).lower()] = (m.group(2), bool(m.group(3)))
    return out


REQUIRED = ["strict-transport-security", "x-content-type-options", "x-frame-options", "referrer-policy", "permissions-policy"]


@pytest.mark.parametrize("name", REQUIRED)
def test_the_https_server_sends_each_security_header_even_on_error_responses(servers, name):
    headers = _headers(servers["443"])
    assert name in headers, f"falta {name}"
    assert headers[name][1], f"{name} debe llevar `always` (si no, no sale en 404/502)"


def test_header_values_are_the_agreed_ones(servers):
    h = {k: v[0] for k, v in _headers(servers["443"]).items()}
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "strict-origin-when-cross-origin"


def test_hsts_is_long_enough_but_not_irreversible(servers):
    value = _headers(servers["443"])["strict-transport-security"][0]
    assert int(re.search(r"max-age=(\d+)", value).group(1)) >= 15552000        # al menos 180 días
    assert "includeSubDomains" not in value and "preload" not in value         # decisión: no se puede deshacer rápido


def test_hsts_is_only_sent_over_https(servers):
    assert "strict-transport-security" not in _headers(servers["80"])


def test_the_http_server_keeps_the_acme_challenge_and_the_redirect(servers):
    assert "/.well-known/acme-challenge/" in servers["80"] and "return 301 https://" in servers["80"]


@pytest.mark.parametrize("port", ["80", "443"])
def test_the_nginx_version_is_not_advertised(servers, port):
    assert re.search(r"server_tokens\s+off\s*;", servers[port])


def test_no_location_defines_its_own_add_header_because_it_would_drop_the_inherited_ones(servers):
    # Nginx no hereda los add_header del server a un location que defina alguno propio. Hoy ninguno lo hace.
    block = servers["443"]
    for loc in re.finditer(r"location\s+[^{]+\{([^}]*)\}", block):
        assert "add_header" not in loc.group(1)


# ---------- CSP: coincide con lo que las plantillas usan

def _csp(servers):
    headers = _headers(servers["443"])
    names = [n for n in ("content-security-policy", "content-security-policy-report-only") if n in headers]
    assert len(names) == 1, "debe haber exactamente una CSP (informe o enforzada)"
    return {d.split()[0]: d.split()[1:] for d in headers[names[0]][0].split(";") if d.strip()}, names[0]


def _template_sources():
    return {p: p.read_text(encoding="utf-8") for p in TEMPLATES.rglob("*.html")}


def _external_hosts_used():
    """Hosts de recursos (hoja de estilos, script, imagen) que las plantillas cargan de fuera de este sitio."""
    hosts = set()
    for text in _template_sources().values():
        for tag in re.findall(r"<(?:link|script|img|source|iframe)\b[^>]*>", text, flags=re.I):
            if re.search(r'rel="(?:preconnect|alternate|dns-prefetch)"', tag, flags=re.I):
                continue
            for url in re.findall(r'(?:href|src)="(https?://[^"/]+)', tag, flags=re.I):
                hosts.add(url)
    return hosts


def test_the_policy_allows_every_external_resource_the_templates_load(servers):
    policy, _ = _csp(servers)
    allowed = {src for sources in policy.values() for src in sources}
    used = _external_hosts_used()
    assert used, "las plantillas cargan Google Fonts: si esto queda vacío, el detector está roto"
    for host in used:
        assert host in allowed, f"las plantillas cargan {host} y la CSP no lo permite (se rompería al enforzarla)"


def test_the_policy_does_not_allow_hosts_the_templates_do_not_use(servers):
    policy, _ = _csp(servers)
    declared = {src for sources in policy.values() for src in sources if src.startswith("http")}
    assert declared <= _external_hosts_used() | {"https://fonts.gstatic.com"}, "la CSP permite hosts que nadie usa"


def test_the_policy_has_the_restrictive_basics(servers):
    policy, _ = _csp(servers)
    assert policy["default-src"] == ["'self'"]
    assert policy["object-src"] == ["'none'"] and policy["frame-ancestors"] == ["'none'"]
    assert policy["base-uri"] == ["'self'"] and policy["form-action"] == ["'self'"]
    assert "'unsafe-inline'" not in policy["script-src"] and "'unsafe-eval'" not in policy["script-src"]


def test_the_templates_have_no_inline_script_style_or_handlers_that_a_strict_policy_would_block():
    for path, text in _template_sources().items():
        rel = path.relative_to(ROOT)
        assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", text, flags=re.I), f"{rel}: <script> en línea"
        assert not re.search(r"<style\b", text, flags=re.I), f"{rel}: <style> en línea"
        assert not re.search(r"\sstyle=", text, flags=re.I), f"{rel}: atributo style en línea"
        assert not re.search(r"\son[a-z]+\s*=", text, flags=re.I), f"{rel}: manejador de evento en línea"


def test_the_site_script_is_served_and_the_pages_reference_it_instead_of_inlining_it(flask_app):
    client = flask_app.test_client()
    assert client.get("/static/site.js").status_code == 200
    html = client.get("/").get_data(as_text=True)
    assert 'src="/static/site.js"' in html and "showModal" not in html


def test_the_delete_confirmation_cannot_be_broken_out_of_by_a_project_title(flask_app):
    # Antes: onsubmit="return confirm('¿Borrar {{ título }}?')". Una comilla en el título se salía de la cadena de
    # JavaScript (y la CSP, al enforzarse, bloqueaba el atributo y borraba sin preguntar).
    from webhelpers import add_project, login
    add_user(flask_app)
    add_project(flask_app, title="x');alert(document.cookie);//")
    client = flask_app.test_client()
    login(client)

    html = client.get("/admin/").get_data(as_text=True)

    assert "onsubmit" not in html
    assert 'data-confirm="¿Borrar x&#39;);alert(document.cookie);//?"' in html     # solo texto de un atributo, escapado
    assert 'src="/static/admin.js"' in html and client.get("/static/admin.js").status_code == 200


def test_google_fonts_css_needs_its_font_files_host_in_font_src(servers):
    # La hoja de estilos de fonts.googleapis.com NO trae las fuentes: las descarga de fonts.gstatic.com (otro host, y
    # sin <link> en las plantillas, así que el detector de arriba no lo ve). Sin él, al enforzar la CSP el texto
    # caería a la fuente por defecto sin ningún error visible en el servidor.
    policy, _ = _csp(servers)
    if "https://fonts.googleapis.com" in _external_hosts_used():
        assert "https://fonts.gstatic.com" in policy["font-src"]
