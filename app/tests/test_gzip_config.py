"""Pruebas de la compresión gzip de los estáticos en Nginx (QAP-26).

Nginx no se puede arrancar en estas pruebas: se lee `nginx/nginx.conf` y `.github/workflows/deploy.yml` como texto y se
comprueba que dicen lo que deben. Lo que NO prueban: que la sintaxis sea válida para Nginx (eso lo dice `nginx -t`, que se
corrió aparte con el binario real) ni que la respuesta de producción salga comprimida (lo comprueba el paso "Static
compression" del deploy, con GET). El comportamiento real se verificó el 2026-10-15 con nginx:1.27-alpine y un upstream
falso: CSS 22 052 -> 5 025 bytes, HTML sin comprimir, cabeceras de seguridad conservadas; y el paso del deploy falla con
tres configuraciones rotas a propósito.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONF = (ROOT / "nginx" / "nginx.conf").read_text(encoding="utf-8")
DEPLOY = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")


def _code(text):
    """La configuración sin comentarios (los comentarios mencionan `gzip on` y `add_header` para explicar las reglas)."""
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


CODE = _code(CONF)


def _block(code, header):
    """Cuerpo de un bloque `header { ... }` con llaves equilibradas."""
    start = code.index(header)
    depth, i = 0, code.index("{", start)
    begin = i
    while True:
        depth += code[i] == "{"
        depth -= code[i] == "}"
        i += 1
        if depth == 0:
            return code[begin + 1:i - 1]


# Los location del servidor HTTPS (el de HTTP, que solo redirige, también tiene un `location /`: no es el que interesa).
HTTPS_CODE = CODE[CODE.index("listen 443"):]
STATIC = _block(HTTPS_CODE, "location /static/")
ROOT_LOCATION = _block(HTTPS_CODE, "location / ")


def test_braces_are_balanced_so_a_typo_cannot_break_the_whole_file():
    assert CODE.count("{") == CODE.count("}")


def test_gzip_is_enabled_only_inside_the_static_location():
    assert re.search(r"^\s*gzip on;", STATIC, flags=re.M)
    outside = CODE.replace(STATIC, "")
    assert not re.search(r"\bgzip\s+on\b", outside), "gzip a nivel de servidor comprimiría también el HTML (BREACH)"


def test_the_html_location_never_enables_gzip():
    assert "proxy_pass" in ROOT_LOCATION, "se está mirando el location equivocado (el de HTTP solo redirige)"
    assert "gzip" not in ROOT_LOCATION


def test_only_text_assets_are_compressed_and_never_html_images_or_documents():
    types = re.search(r"gzip_types\s+([^;]+);", STATIC).group(1).split()
    assert {"text/css", "text/javascript", "application/javascript"} <= set(types)
    for forbidden in ("text/html", "*", "image/jpeg", "image/png", "application/pdf", "application/x-www-form-urlencoded"):
        assert forbidden not in types, forbidden


def test_compressed_and_plain_versions_do_not_get_mixed_up_by_caches():
    assert re.search(r"^\s*gzip_vary on;", STATIC, flags=re.M)


def test_tiny_files_are_not_compressed_because_it_would_not_pay_off():
    assert int(re.search(r"gzip_min_length\s+(\d+);", STATIC).group(1)) >= 256


def test_the_static_location_does_not_define_add_header_or_it_would_lose_the_security_headers():
    # Nginx NO hereda los add_header del servidor a un location que defina los suyos (QAP-21).
    assert "add_header" not in STATIC


def test_the_server_keeps_defining_every_security_header_that_the_static_location_inherits():
    server_only = CODE.replace(STATIC, "").replace(ROOT_LOCATION, "")
    for header in ("Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy",
                   "Permissions-Policy", "Content-Security-Policy-Report-Only"):
        assert re.search(rf"add_header {header} ", server_only), header


@pytest.mark.parametrize("directive", [
    r"set \$upstream_app app:8000;",
    r"proxy_pass http://\$upstream_app;",
    r"proxy_set_header Host \$host;",
    r"proxy_set_header X-Real-IP \$remote_addr;",
    r"proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;",
    r"proxy_set_header X-Forwarded-Proto \$scheme;",
])
def test_the_static_location_repeats_the_proxy_settings_of_the_main_location(directive):
    # Un location no hereda los proxy_* del anterior. Sin X-Real-IP / X-Forwarded-Proto cambiaría el comportamiento.
    assert re.search(directive, STATIC), directive
    assert re.search(directive, ROOT_LOCATION), directive


def test_the_http_server_block_is_untouched_and_still_only_redirects():
    assert "gzip" not in CODE.split("server {")[1]


# ---------- el deploy comprueba la respuesta REAL de producción

def test_the_deploy_checks_static_compression_with_a_real_get_that_asks_for_gzip():
    step = DEPLOY[DEPLOY.index("- name: Static compression"):]
    step = step.split("\n      - name:")[0]
    assert "-D - -o /dev/null" in step, "GET con las cabeceras volcadas a la salida"
    assert "curl -fsSI" not in step, "HEAD no ejercita el cuerpo real (se eligió GET a propósito)"
    assert "Accept-Encoding: gzip" in step
    assert re.search(r"/static/site\.css", step)


def test_the_deploy_step_checks_gzip_vary_security_headers_and_that_html_is_not_compressed():
    step = DEPLOY[DEPLOY.index("- name: Static compression"):].split("\n      - name:")[0]
    # No basta con que las palabras aparezcan: cada comprobación debe hacer FALLAR el paso si no se cumple (`|| missing=`).
    for fragment in ("content-encoding: gzip", "vary:.*accept-encoding", "x-content-type-options", "strict-transport-security"):
        line = next((l for l in step.splitlines() if f"grep -qi '^{fragment}'" in l), None)
        assert line is not None, f"no se comprueba {fragment}"
        assert "|| missing=" in line, f"{fragment}: la comprobación no hace fallar el paso"
    assert re.search(r"if echo \"\$html\" \| grep -qi '\^content-encoding'; then missing=", step), "el HTML no debe salir comprimido"
    assert re.search(r'if \[ -n "\$missing" \]; then\s+echo "Falla:\$missing"\s+exit 1', step), "si falta algo, el paso debe fallar"
    assert "BREACH" in step, "debe explicar por qué el HTML no se comprime"
