"""Pruebas del modo en vivo de los demos de IA (QAP-18): formulario, endpoint, límites, respaldo, escape y privacidad.

Todas usan un proveedor SIMULADO (fakes.FakeProvider): ninguna llama a un servicio real ni gasta cuota. El modo en vivo
viene APAGADO por defecto (sin AI_PROVIDER); aquí se activa a mano con webhelpers.enable_live. Reglas del proyecto que
estas pruebas protegen (CLAUDE.md, "Enfoque de IA del portafolio"): un ejemplo pregenerado nunca se presenta como en
vivo; lo generado en vivo lleva la etiqueta del modelo y la advertencia de borrador sin verificar; la entrada del
visitante no se registra en ningún log ni se mezcla con el prompt del sistema; ante cualquier fallo se muestra el
ejemplo pregenerado, nunca un error.
"""
import logging
import re

import pytest

from ai_provider import ProviderError, ProviderQuotaExceeded
from fakes import FakeProvider
from webhelpers import csrf_token, enable_live

PATHS = {"es": "/demos", "en": "/en/demos"}
LIVE = {"es": "/demos/live", "en": "/en/demos/live"}
STORY = "Historia: como visitante quiero reservar una habitación."


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()


def post_live(client, demo="testcases", text=STORY, lang="es", headers=None, token=True):
    data = {"demo": demo, "input": text}
    if token:
        data["csrf_token"] = csrf_token(client, "/admin/login")      # el token de sesión sirve para cualquier formulario
    return client.post(LIVE[lang], data=data, headers=headers or {})


def page(resp):
    return resp.get_data(as_text=True)


def live_block(html, demo):
    """Solo el recuadro del resultado en vivo de un demo (el formulario y los ejemplos quedan fuera)."""
    start = html.index(f'data-live-result="{demo}"')
    return html[start:html.index("</div>", start)]


# ---------- apagado por defecto: la página queda exactamente como antes

def test_live_mode_is_off_by_default_so_there_is_no_form_and_no_endpoint(client):
    html = page(client.get("/demos"))

    assert "data-live-form" not in html and "<textarea" not in html
    assert post_live(client).status_code == 404


def test_the_off_page_still_says_that_nothing_is_generated_from_what_you_type(client):
    assert "no hay un cuadro de entrada libre" in page(client.get("/demos"))


# ---------- encendido: formulario con avisos

@pytest.mark.parametrize("lang, privacy, unverified", [
    ("es", "No pegues datos reales ni confidenciales", "borrador sin verificar"),
    ("en", "Do not paste real or confidential data", "unverified draft"),
])
def test_with_live_mode_on_each_demo_has_a_form_with_the_privacy_notice(app, client, lang, privacy, unverified):
    enable_live(app)

    html = page(client.get(PATHS[lang]))

    assert html.count("data-live-form") == 3
    for demo in ("testcases", "bugs", "apitests"):
        assert f'name="demo" value="{demo}"' in html
    assert html.count(privacy) >= 3 and unverified in html
    assert re.search(r'<textarea[^>]*maxlength="4000"', html)       # el tope de entrada llega al navegador
    assert 'name="csrf_token"' in html


def test_with_live_mode_on_the_page_no_longer_claims_there_is_no_input_box_but_still_labels_the_examples(app, client):
    enable_live(app)

    html = page(client.get("/demos"))

    assert "no hay un cuadro de entrada libre" not in html
    assert "pregenerad" in html and "Generado con Claude Sonnet 5.5" in html      # los ejemplos siguen siendo pregenerados
    assert "Generado ahora por" not in html                                        # y nada se presenta como en vivo todavía


# ---------- camino feliz

def test_a_live_answer_is_shown_with_the_model_label_and_the_unverified_warning(app, client):
    provider = enable_live(app, FakeProvider(model="modelo-x", text="TC01 Reservar con datos válidos"))

    resp = post_live(client)
    html = page(resp)

    assert resp.status_code == 200
    assert 'data-live-mode="live"' in html and "TC01 Reservar con datos válidos" in html
    assert "Generado ahora por" in html and "modelo-x" in html
    assert "borrador sin verificar" in live_block(html, "testcases")  # la advertencia va EN el resultado, no solo en el formulario
    assert "Generado con Claude Sonnet 5.5" in html                  # los ejemplos pregenerados siguen debajo
    assert len(provider.calls) == 1


def test_the_visitor_text_travels_as_the_user_message_and_never_inside_the_system_prompt(app, client):
    provider = enable_live(app)

    post_live(client, demo="bugs", text="Traza: ValueError secreto-123")

    system, user, max_tokens, timeout = provider.calls[0]
    assert user == "Traza: ValueError secreto-123"
    assert "secreto-123" not in system
    assert "Spanish" in system


def test_the_live_answer_is_shown_inside_the_section_of_the_demo_that_was_used(app, client):
    enable_live(app, FakeProvider(text="SALIDA-UNICA"))

    html = page(post_live(client, demo="bugs"))

    assert html.count("SALIDA-UNICA") == 1
    start = html.index('id="demo-bugs"')
    end = html.index('id="demo-apitests"')
    assert start < html.index("SALIDA-UNICA") < end


def test_the_api_tests_answer_warns_that_the_code_was_not_executed(app, client):
    enable_live(app, FakeProvider(text="# NOT EXECUTED - review before using\ndef test_x(): pass"))

    html = page(post_live(client, demo="apitests", text="POST /auth"))

    assert "no se ejecutó" in live_block(html, "apitests")


def test_english_route_answers_in_english(app, client):
    provider = enable_live(app, FakeProvider(model="m1"))

    html = page(post_live(client, lang="en"))

    assert "Generated just now by" in html and "unverified draft" in live_block(html, "testcases")
    assert "English" in provider.calls[0][0]


def test_a_truncated_answer_is_marked_as_cut(app, client):
    enable_live(app, FakeProvider(text="texto del modelo", truncated=True))

    html = page(post_live(client))

    assert 'data-live-truncated="true"' in html and "cortada" in live_block(html, "testcases")


# ---------- escape de HTML (lo que escribe el visitante y lo que devuelve el modelo)

def test_html_in_the_model_answer_and_in_the_visitor_text_is_escaped(app, client):
    enable_live(app, FakeProvider(text='<script>alert("x")</script><img src=x onerror=alert(1)>'))

    html = page(post_live(client, text="<b>negrita</b> & <script>alert(2)</script>"))

    assert "<script>alert" not in html and "<img src=x" not in html
    assert "&lt;script&gt;alert(" in html
    assert "&lt;b&gt;negrita&lt;/b&gt; &amp; &lt;script&gt;alert(2)&lt;/script&gt;" in html    # el texto se devuelve al formulario, escapado


# ---------- entrada inválida

def test_an_unknown_demo_is_a_400_and_the_provider_is_not_called(app, client):
    provider = enable_live(app)

    resp = post_live(client, demo="otro")

    assert resp.status_code == 400 and provider.calls == []


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_empty_input_is_a_400_with_a_message_and_the_provider_is_not_called(app, client, text):
    provider = enable_live(app)

    resp = post_live(client, text=text)

    assert resp.status_code == 400 and 'data-live-mode="rejected"' in page(resp) and 'data-live-reason="empty"' in page(resp)
    assert provider.calls == []


def test_input_longer_than_the_limit_is_rejected_not_truncated(app, client):
    provider = enable_live(app, max_input_chars=50)

    resp = post_live(client, text="x" * 51)

    assert resp.status_code == 400 and 'data-live-reason="too_long"' in page(resp) and "50" in page(resp)
    assert provider.calls == []


def test_a_request_body_far_above_the_limit_is_a_413(app, client):
    provider = enable_live(app)
    big = "x" * 200_000

    resp = client.post(LIVE["es"], data={"demo": "testcases", "input": big, "csrf_token": csrf_token(client, "/admin/login")})

    assert resp.status_code == 413 and provider.calls == []


def test_without_a_csrf_token_the_post_is_a_400_and_the_provider_is_not_called(app, client):
    provider = enable_live(app)

    assert post_live(client, token=False).status_code == 400
    assert provider.calls == []


# ---------- respaldo: ante cualquier fallo se ven los ejemplos pregenerados, nunca un error

@pytest.mark.parametrize("raises, reason", [
    (ProviderError("caído"), "provider_error"),
    (ProviderQuotaExceeded("cuota"), "provider_quota"),
    (RuntimeError("bug del proveedor"), "provider_error"),
])
def test_a_provider_failure_shows_the_pregenerated_examples_and_never_claims_to_be_live(app, client, raises, reason):
    enable_live(app, FakeProvider(raises=raises))

    resp = post_live(client)
    html = page(resp)

    assert resp.status_code == 200
    assert 'data-live-mode="fallback"' in html and f'data-live-reason="{reason}"' in html
    assert "Generado ahora por" not in html
    assert "Generado con Claude Sonnet 5.5" in html


def test_an_empty_model_answer_falls_back(app, client):
    enable_live(app, FakeProvider(text="   "))

    html = page(post_live(client))

    assert 'data-live-reason="empty_response"' in html and "Generado ahora por" not in html


# ---------- límites

def test_the_per_visitor_limit_returns_429_with_retry_after_and_the_fallback(app, client):
    provider = enable_live(app, per_visitor=2)

    assert [post_live(client).status_code for _ in range(2)] == [200, 200]
    resp = post_live(client)

    assert resp.status_code == 429 and int(resp.headers["Retry-After"]) > 0
    assert 'data-live-reason="visitor_limit"' in page(resp) and "Generado ahora por" not in page(resp)
    assert len(provider.calls) == 2


def test_the_daily_cap_returns_429_for_everyone(app):
    provider = enable_live(app, per_visitor=10, daily_cap=2)

    codes = [post_live(app.test_client(), headers={"X-Real-IP": f"198.51.100.{n}"}).status_code for n in range(3)]

    assert codes == [200, 200, 429] and len(provider.calls) == 2


def test_visitors_are_told_apart_by_x_real_ip(app):
    enable_live(app, per_visitor=1)
    a, b = app.test_client(), app.test_client()

    assert post_live(a, headers={"X-Real-IP": "203.0.113.1"}).status_code == 200
    assert post_live(a, headers={"X-Real-IP": "203.0.113.1"}).status_code == 429
    assert post_live(b, headers={"X-Real-IP": "203.0.113.2"}).status_code == 200


def test_x_forwarded_for_cannot_be_used_to_dodge_the_limit(app, client):
    enable_live(app, per_visitor=1)
    same_real_ip = {"X-Real-IP": "203.0.113.9"}

    assert post_live(client, headers={**same_real_ip, "X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert post_live(client, headers={**same_real_ip, "X-Forwarded-For": "2.2.2.2"}).status_code == 429


def test_a_rejected_request_does_not_consume_the_visitors_quota(app, client):
    enable_live(app, per_visitor=1)

    assert post_live(client, text="").status_code == 400
    assert post_live(client).status_code == 200


# ---------- privacidad

SECRET = "TEXTO-PRIVADO-DEL-VISITANTE-9f3a"


@pytest.mark.parametrize("provider", [
    FakeProvider(),                                   # camino feliz
    FakeProvider(raises=ProviderError("x")),          # fallo del proveedor
    FakeProvider(raises=RuntimeError("x")),           # excepción inesperada (se registra con traceback)
])
def test_the_visitor_text_is_never_written_to_any_log(app, client, caplog, provider):
    enable_live(app, provider)
    caplog.set_level(logging.DEBUG)

    post_live(client, text=SECRET)

    assert SECRET not in caplog.text


def test_the_visitor_text_is_not_logged_when_rate_limited_or_rejected(app, client, caplog):
    enable_live(app, per_visitor=1, max_input_chars=len(SECRET) + 5)
    caplog.set_level(logging.DEBUG)

    post_live(client, text=SECRET)
    post_live(client, text=SECRET)                                   # limitada
    post_live(client, text=SECRET + "x" * 50)                        # demasiado larga

    assert SECRET not in caplog.text


# ---------- el servicio se arma desde el entorno

def test_the_service_is_built_from_the_environment_and_is_off_without_a_provider(make_app):
    app = make_app(AI_PROVIDER="", AI_MODEL="", AI_API_KEY="")
    assert app.extensions["demo_service"].provider is None


def test_a_misconfigured_provider_leaves_the_site_up_with_live_mode_off(make_app):
    app = make_app(AI_PROVIDER="no-existe", AI_MODEL="m", AI_API_KEY="k")
    assert app.extensions["demo_service"].provider is None
    assert app.test_client().get("/demos").status_code == 200


def test_the_configuration_reaches_the_service(make_app):
    app = make_app(AI_PROVIDER="groq", AI_MODEL="openai/gpt-oss-20b", AI_API_KEY="clave-falsa", AI_DAILY_CAP="12",
                   AI_MAX_INPUT_CHARS="777")
    service = app.extensions["demo_service"]
    assert service.provider is not None and service.provider.model == "openai/gpt-oss-20b"
    assert service.config.daily_cap == 12 and service.config.max_input_chars == 777
