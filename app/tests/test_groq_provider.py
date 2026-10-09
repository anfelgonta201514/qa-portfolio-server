"""Pruebas de GroqProvider con respuestas HTTP SIMULADAS (no se sale a la red ni se gasta nada).

Lo que se comprueba sale de la documentación oficial de Groq: URL, autenticación, nombres de
los parámetros y forma de la respuesta y de los errores. Lo que NO se puede comprobar aquí es
el comportamiento real del servicio (latencia, cuotas, razonamiento): eso lo cubre la prueba
`groq_live`, que necesita una clave real y solo corre a mano.
"""
import io
import json
import logging
import os
import socket
import urllib.error

import pytest

import ai_provider
from ai_provider import GroqProvider, ProviderError, ProviderQuotaExceeded, build_provider
from ai_service import DemoService, AIConfig, build_service

import demo_content
from ai_limits import DemoLimiter

KEY = "gsk_CLAVE-SECRETA-DE-PRUEBA-123"


class FakeHTTPResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def ok_payload(content="respuesta", prompt=10, completion=20, with_usage=True):
    p = {"choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}]}
    if with_usage:
        p["usage"] = {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion}
    return p


@pytest.fixture
def http(monkeypatch):
    """Reemplaza urlopen: registra la petición y responde lo que se configure."""
    class Http:
        requests = []
        timeouts = []
        behavior = staticmethod(lambda: FakeHTTPResponse(json.dumps(ok_payload()).encode()))

    def fake_urlopen(request, timeout=None):
        Http.requests.append(request)
        Http.timeouts.append(timeout)
        result = Http.behavior()
        if isinstance(result, Exception):
            raise result
        return result

    Http.requests, Http.timeouts = [], []
    monkeypatch.setattr(ai_provider.urllib.request, "urlopen", fake_urlopen)
    return Http


def http_error(code):
    return urllib.error.HTTPError("https://api.groq.com/x", code, "msg", {}, io.BytesIO(b'{"error":{"message":"eco de la ENTRADA del usuario","type":"x"}}'))


def provider(model="openai/gpt-oss-20b"):
    return GroqProvider(model, KEY)


# ---------- forma de la petición (según la documentación oficial)

def test_request_goes_to_the_documented_endpoint_with_bearer_auth(http):
    provider().generate("sistema", "usuario", max_tokens=300, timeout=9)
    req = http.requests[0]
    assert req.full_url == "https://api.groq.com/openai/v1/chat/completions"
    assert req.get_method() == "POST"
    assert req.get_header("Authorization") == f"Bearer {KEY}"
    assert req.get_header("Content-type") == "application/json"


def test_request_body_uses_max_completion_tokens_not_the_deprecated_max_tokens(http):
    provider().generate("sistema", "usuario", max_tokens=300, timeout=9)
    body = json.loads(http.requests[0].data)
    assert body["max_completion_tokens"] == 300
    assert "max_tokens" not in body


def test_system_and_user_messages_are_separate_and_in_order(http):
    provider().generate("SISTEMA", "USUARIO", max_tokens=100, timeout=9)
    body = json.loads(http.requests[0].data)
    assert body["messages"] == [
        {"role": "system", "content": "SISTEMA"},
        {"role": "user", "content": "USUARIO"},
    ]
    assert body["model"] == "openai/gpt-oss-20b"
    assert body["temperature"] == 0.3
    assert "stream" not in body or body["stream"] is False


def test_the_timeout_is_passed_to_the_http_call(http):
    provider().generate("s", "u", max_tokens=100, timeout=7.5)
    assert http.timeouts == [7.5]


def test_api_key_only_travels_in_the_header_never_in_the_body(http):
    provider().generate("s", "u", max_tokens=100, timeout=9)
    assert KEY.encode() not in http.requests[0].data


def test_reasoning_models_ask_for_low_effort_and_no_reasoning_text(http):
    provider("openai/gpt-oss-120b").generate("s", "u", max_tokens=100, timeout=9)
    body = json.loads(http.requests[0].data)
    assert body["reasoning_effort"] == "low"
    assert body["include_reasoning"] is False


def test_non_reasoning_models_do_not_get_reasoning_parameters(http):
    provider("llama-modelo-cualquiera").generate("s", "u", max_tokens=100, timeout=9)
    body = json.loads(http.requests[0].data)
    assert "reasoning_effort" not in body and "include_reasoning" not in body


# ---------- forma de la respuesta

def test_successful_answer_is_normalized(http):
    c = provider().generate("s", "u", max_tokens=100, timeout=9)
    assert (c.text, c.provider, c.model) == ("respuesta", "groq", "openai/gpt-oss-20b")
    assert (c.input_tokens, c.output_tokens) == (10, 20)


def test_missing_usage_gives_none_tokens_not_a_crash(http):
    http.behavior = lambda: FakeHTTPResponse(json.dumps(ok_payload(with_usage=False)).encode())
    c = provider().generate("s", "u", max_tokens=100, timeout=9)
    assert (c.input_tokens, c.output_tokens) == (None, None)


def test_null_content_becomes_empty_text_so_the_service_can_fall_back(http):
    # Caso real posible: el razonamiento consume todo el tope y `content` llega vacío.
    http.behavior = lambda: FakeHTTPResponse(json.dumps(ok_payload(content=None)).encode())
    assert provider().generate("s", "u", max_tokens=100, timeout=9).text == ""


# ---------- errores: todo se traduce a ProviderError, 429 a cuota

def test_http_429_is_a_quota_error(http):
    http.behavior = lambda: http_error(429)
    with pytest.raises(ProviderQuotaExceeded):
        provider().generate("s", "u", max_tokens=100, timeout=9)


@pytest.mark.parametrize("code", [400, 401, 403, 404, 413, 422, 424, 498, 499, 500, 502, 503])
def test_other_http_errors_are_provider_errors_not_quota(http, code):
    http.behavior = lambda: http_error(code)
    with pytest.raises(ProviderError) as info:
        provider().generate("s", "u", max_tokens=100, timeout=9)
    assert not isinstance(info.value, ProviderQuotaExceeded)
    assert str(code) in str(info.value)


@pytest.mark.parametrize("error", [
    urllib.error.URLError("sin red"), socket.timeout("lento"), TimeoutError("lento"), ConnectionResetError("reset"),
])
def test_network_failures_and_timeouts_are_provider_errors(http, error):
    http.behavior = lambda: error
    with pytest.raises(ProviderError):
        provider().generate("s", "u", max_tokens=100, timeout=9)


@pytest.mark.parametrize("raw", [b"no es json", b"", b"<html>502</html>"])
def test_non_json_body_is_a_provider_error(http, raw):
    http.behavior = lambda: FakeHTTPResponse(raw)
    with pytest.raises(ProviderError):
        provider().generate("s", "u", max_tokens=100, timeout=9)


@pytest.mark.parametrize("payload", [{}, {"choices": []}, {"choices": [{}]}, {"choices": [{"message": None}]}, [], {"choices": "x"}])
def test_unexpected_response_shape_is_a_provider_error(http, payload):
    http.behavior = lambda: FakeHTTPResponse(json.dumps(payload).encode())
    with pytest.raises(ProviderError):
        provider().generate("s", "u", max_tokens=100, timeout=9)


# ---------- seguridad: ni la clave ni lo que escribió el visitante se filtran

def test_error_messages_and_logs_never_contain_the_key_or_the_server_echo(http, caplog):
    for code in (401, 429, 500):
        http.behavior = lambda code=code: http_error(code)
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ProviderError) as info:
                provider().generate("s", "ENTRADA-DEL-USUARIO", max_tokens=100, timeout=9)
        assert KEY not in str(info.value)
        assert "eco de la ENTRADA" not in str(info.value)        # el cuerpo del error no se propaga
    assert KEY not in caplog.text
    assert "eco de la ENTRADA" not in caplog.text


# ---------- bug REAL hallado en la primera llamada a Groq (403 de Cloudflare, error 1010)

def http_error_body(code, body: bytes):
    return urllib.error.HTTPError("https://api.groq.com/x", code, "msg", {}, io.BytesIO(body))


def test_request_sends_its_own_user_agent_never_the_python_urllib_default(http):
    """REGRESIÓN. Sin User-Agent propio, urllib se anuncia como "Python-urllib/3.x" y Cloudflare, que
    protege la API de Groq, lo bloquea con un 403 "error code: 1010" ANTES de mirar la clave. Se
    descubrió con la primera llamada real; una prueba simulada no podía verlo, y este es el registro."""
    provider().generate("s", "u", max_tokens=100, timeout=9)
    agent = http.requests[0].get_header("User-agent")
    assert agent and not agent.startswith("Python-urllib")


def test_cloudflare_block_is_reported_with_its_code(http):
    http.behavior = lambda: http_error_body(403, b"error code: 1010 \n")
    with pytest.raises(ProviderError) as info:
        provider().generate("s", "u", max_tokens=100, timeout=9)
    assert "403" in str(info.value) and "cloudflare 1010" in str(info.value)


def test_groq_error_code_and_type_are_kept_as_safe_diagnostics_but_never_the_free_text(http):
    body = b'{"error":{"message":"ECO-DE-LA-ENTRADA-DEL-VISITANTE","type":"invalid_request_error","code":"invalid_api_key"}}'
    http.behavior = lambda: http_error_body(401, body)
    with pytest.raises(ProviderError) as info:
        provider().generate("s", "u", max_tokens=100, timeout=9)
    text = str(info.value)
    assert "401" in text and "invalid_api_key" in text and "invalid_request_error" in text
    assert "ECO-DE-LA-ENTRADA-DEL-VISITANTE" not in text


@pytest.mark.parametrize("unsafe", [
    "ECO del visitante 123",                      # texto libre con espacios y mayúsculas
    "gsk_" + "A" * 50,                            # algo con forma de clave
    "a" * 200,                                    # demasiado largo
    "con\nsalto",                                 # salto de línea
    "<script>alert(1)</script>",
])
def test_error_detail_discards_anything_that_is_not_a_short_identifier(http, unsafe):
    body = json.dumps({"error": {"message": "m", "type": unsafe, "code": unsafe}}).encode()
    http.behavior = lambda: http_error_body(400, body)
    with pytest.raises(ProviderError) as info:
        provider().generate("s", "u", max_tokens=100, timeout=9)
    assert str(info.value) == "groq: HTTP 400"


@pytest.mark.parametrize("body", [b"", b"<html>502</html>", b'{"error": "solo texto"}', b'{"error": null}', b"[]", b"\xff\xfe", b"error code: abc"])
def test_error_detail_survives_unreadable_or_odd_bodies(http, body):
    http.behavior = lambda: http_error_body(500, body)
    with pytest.raises(ProviderError) as info:
        provider().generate("s", "u", max_tokens=100, timeout=9)
    assert str(info.value) == "groq: HTTP 500"


# ---------- registro y configuración

def test_groq_is_registered_and_built_from_environment():
    assert set(ai_provider.PROVIDERS) == {"groq"}
    p = build_provider(" Groq ", " openai/gpt-oss-20b ", f" {KEY} ")
    assert isinstance(p, GroqProvider) and p.model == "openai/gpt-oss-20b"


def test_build_service_from_environment_wires_groq():
    svc = build_service({"AI_PROVIDER": "groq", "AI_MODEL": "openai/gpt-oss-20b", "AI_API_KEY": KEY})
    assert isinstance(svc.provider, GroqProvider)


def test_groq_without_a_key_stays_off():
    assert build_service({"AI_PROVIDER": "groq", "AI_MODEL": "openai/gpt-oss-20b"}).provider is None


# ---------- de punta a punta con el servicio (HTTP simulado)

def service(**cfg):
    config = AIConfig(**cfg)
    return DemoService(provider(), DemoLimiter(config.per_visitor, config.window_seconds, config.daily_cap),
                       config, demo_content.EXAMPLES)


def test_end_to_end_live_answer(http):
    r = service().run("testcases", "una historia", "v1", "es")
    assert (r.mode, r.provider, r.model, r.text) == ("live", "groq", "openai/gpt-oss-20b", "respuesta")
    sent = json.loads(http.requests[0].data)
    assert sent["messages"][1]["content"] == "una historia"
    assert "una historia" not in sent["messages"][0]["content"]


@pytest.mark.parametrize("behavior, reason", [
    (lambda: http_error(429), "provider_quota"),
    (lambda: http_error(503), "provider_error"),
    (lambda: urllib.error.URLError("x"), "provider_error"),
    (lambda: FakeHTTPResponse(json.dumps(ok_payload(content="")).encode()), "empty_response"),
])
def test_end_to_end_failures_fall_back_to_the_labeled_example(http, behavior, reason):
    http.behavior = behavior
    r = service().run("bugs", "traza", "v1", "es")
    assert (r.mode, r.reason) == ("fallback", reason)
    assert r.example == demo_content.EXAMPLES["bugs"]["es"][0]


# ---------- prueba REAL contra Groq (solo a mano, con clave en el entorno)

@pytest.mark.groq_live
def test_real_groq_answers_a_tiny_prompt():
    """Necesita GROQ_API_KEY en el entorno de quien la corre (NUNCA en el repo ni en el chat):
        GROQ_API_KEY=... GROQ_MODEL=openai/gpt-oss-20b python -m pytest app/tests -m groq_live -q -s
    Consume una cantidad mínima de cuota (un prompt corto)."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        pytest.skip("falta GROQ_API_KEY")
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    c = GroqProvider(model, key).generate(
        "You are a QA engineer. Answer in one short sentence.",
        "Name one boundary value to test for an input that accepts 11 to 21 characters.",
        max_tokens=400, timeout=30,
    )
    print(f"\nmodelo={c.model} tokens_entrada={c.input_tokens} tokens_salida={c.output_tokens}\nrespuesta={c.text[:200]!r}")
    assert c.text.strip(), "respuesta vacía: ¿el razonamiento consumió todo el tope? subir max_tokens"
    assert (c.output_tokens or 0) > 0


@pytest.mark.groq_live
def test_real_groq_on_the_demo_examples():
    """MIDE con la clave real lo que costaría usar de verdad los 3 demos (6 entradas, en español).

    Pasa cada entrada por el servicio real (prompts, tope de salida y timeout de producción) y deja
    los resultados completos en .groq-measure/results.json (ignorado por git) para revisarlos:
        GROQ_API_KEY=... python -m pytest app/tests/test_groq_provider.py -m groq_live -q -s
    Gasta unos 15.000 tokens de los 200.000 diarios del plan gratis. Tarda ~2 minutos porque
    espera 20 s entre llamadas para no pasar el tope de 8.000 tokens por minuto.
    """
    import pathlib
    import time

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        pytest.skip("falta GROQ_API_KEY")
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

    cfg = AIConfig(per_visitor=50, daily_cap=50)
    svc = DemoService(GroqProvider(model, key), DemoLimiter(cfg.per_visitor, cfg.window_seconds, cfg.daily_cap),
                      cfg, demo_content.EXAMPLES)

    cases = [(demo, ex) for demo in demo_content.DEMO_ORDER for ex in demo_content.EXAMPLES[demo]["es"]]
    rows = []
    for i, (demo, ex) in enumerate(cases):
        if i:
            time.sleep(20)  # respeta el tope de tokens por minuto del plan gratis
        started = time.time()
        r = svc.run(demo, ex["input"], "medicion", "es")
        rows.append({
            "demo": demo, "example": ex["id"], "mode": r.mode, "reason": r.reason,
            "seconds": round(time.time() - started, 2),
            "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
            "chars": len(r.text or ""), "text": r.text,
        })

    out = pathlib.Path(__file__).resolve().parents[2] / ".groq-measure"
    out.mkdir(exist_ok=True)
    (out / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nmodelo={model}")
    print(f"{'demo':10} {'ejemplo':9} {'modo':9} {'motivo':16} {'seg':>6} {'tok_in':>7} {'tok_out':>8} {'chars':>6}")
    for r in rows:
        print(f"{r['demo']:10} {r['example']:9} {r['mode']:9} {str(r['reason'] or '-'):16} {r['seconds']:>6} "
              f"{str(r['input_tokens']):>7} {str(r['output_tokens']):>8} {r['chars']:>6}")
    live = [r for r in rows if r["mode"] == "live"]
    print(f"TOTAL tokens: entrada={sum(r['input_tokens'] or 0 for r in live)} salida={sum(r['output_tokens'] or 0 for r in live)}"
          f" | respuestas en vivo: {len(live)} de {len(rows)}")
    assert len(live) == len(rows), "alguna llamada cayó en respaldo: revisa el motivo en la tabla y en results.json"
