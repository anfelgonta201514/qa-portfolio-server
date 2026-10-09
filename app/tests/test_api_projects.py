"""Pruebas de la API /api/projects (QAP-20; casos TC-API-01 a TC-API-10 de docs/qe/plan-de-pruebas.md).

Son pruebas de integración con el cliente de Flask sobre SQLite en memoria; cada prueba parte de una app y una base
nuevas. Producción usa PostgreSQL (más estricto): la brecha se cubre con test_postgres_smoke.py (-m postgres).

Hallazgos de docs/qe/estrategia-de-pruebas.md que estas pruebas fijan: H2 (campos que faltan = 400, no 500), H3 (escribir
sin sesión = 401 JSON, no una redirección HTML), H4 (cuerpo que no es JSON = 415) y H5 (tipos y longitudes inválidos = 400).
"""
import pytest

from webhelpers import add_project, add_user, count_projects, login

VALID = {"title": "Proyecto nuevo", "description": "Qué hace", "tech_stack": ["pytest", "requests"],
         "repo_url": "https://github.com/x/y", "week": 8}


@pytest.fixture
def client(flask_app):
    add_user(flask_app)
    return flask_app.test_client()


@pytest.fixture
def admin(flask_app):
    """Cliente con sesión de admin iniciada por el formulario real."""
    add_user(flask_app)
    c = flask_app.test_client()
    assert login(c).status_code == 302
    return c


# ---------- TC-API-01 / 02: lectura pública

def test_list_projects_is_public_ordered_by_week_and_splits_the_stack(flask_app, client):
    add_project(flask_app, title="B", week=6, tech_stack="x,y")
    add_project(flask_app, title="A", week=4, tech_stack="z")
    add_project(flask_app, title="C", week=4, tech_stack="w")

    resp = client.get("/api/projects")

    assert resp.status_code == 200
    body = resp.get_json()
    assert [p["title"] for p in body] == ["A", "C", "B"]        # por semana y, en empate, por id
    assert body[2]["tech_stack"] == ["x", "y"]


def test_get_project_returns_it_or_404(flask_app, client):
    pid = add_project(flask_app, title="Uno")
    assert client.get(f"/api/projects/{pid}").get_json()["title"] == "Uno"
    assert client.get("/api/projects/9999").status_code == 404


# ---------- TC-API-03: escribir sin sesión (H3)

@pytest.mark.parametrize("method, path", [("post", "/api/projects"), ("put", "/api/projects/1"),
                                          ("delete", "/api/projects/1")])
def test_writes_without_session_return_401_json_and_change_nothing(flask_app, client, method, path):
    add_project(flask_app, title="Original")

    resp = getattr(client, method)(path, json=VALID)

    assert resp.status_code == 401                                  # antes: 302 hacia el login (HTML)
    assert resp.is_json and "error" in resp.get_json()
    assert count_projects(flask_app) == 1
    assert client.get("/api/projects/1").get_json()["title"] == "Original"


# ---------- TC-API-04: crear (camino feliz)

def test_create_project_returns_201_and_shows_up_in_the_list(flask_app, admin):
    resp = admin.post("/api/projects", json=VALID)

    assert resp.status_code == 201
    created = resp.get_json()
    assert created["title"] == "Proyecto nuevo" and created["week"] == 8
    assert created["tech_stack"] == ["pytest", "requests"]
    assert [p["title"] for p in admin.get("/api/projects").get_json()] == ["Proyecto nuevo"]


def test_create_accepts_the_stack_as_a_comma_separated_string_and_omits_optional_fields(admin):
    resp = admin.post("/api/projects", json={"title": "T", "description": "D", "tech_stack": "a, b"})

    assert resp.status_code == 201
    assert resp.get_json()["tech_stack"] == ["a", "b"]
    assert resp.get_json()["week"] is None and resp.get_json()["repo_url"] is None


# ---------- TC-API-05: campos obligatorios (H2)

@pytest.mark.parametrize("missing", ["title", "description", "tech_stack"])
def test_create_without_a_required_field_returns_400_naming_it(flask_app, admin, missing):
    payload = {k: v for k, v in VALID.items() if k != missing}

    resp = admin.post("/api/projects", json=payload)

    assert resp.status_code == 400                                  # antes: 500 (KeyError)
    assert missing in resp.get_json()["error"]
    assert count_projects(flask_app) == 0


@pytest.mark.parametrize("field", ["title", "description"])
@pytest.mark.parametrize("blank", ["", "   "])
def test_create_with_a_blank_required_text_returns_400(flask_app, admin, field, blank):
    resp = admin.post("/api/projects", json={**VALID, field: blank})
    assert resp.status_code == 400 and field in resp.get_json()["error"]
    assert count_projects(flask_app) == 0


# ---------- TC-API-06: tipos y longitudes inválidos (H5)

@pytest.mark.parametrize("field, value", [
    ("title", "x" * 121),                  # la columna es VARCHAR(120)
    ("title", 123),
    ("description", ["lista"]),
    ("tech_stack", []),
    ("tech_stack", [1, 2]),
    ("tech_stack", ["a" * 256]),           # el stack se guarda unido por comas en VARCHAR(255)
    ("tech_stack", {"a": 1}),
    ("repo_url", "https://" + "u" * 248),  # VARCHAR(255): 256 caracteres
    ("repo_url", "javascript:alert(1)"),   # el sitio público lo usa como enlace: solo http(s)
    ("repo_url", "github.com/x/y"),
    ("repo_url", 5),
    ("week", "abc"),
    ("week", 1.5),
    ("week", True),                        # bool es int en Python, pero no es una semana
    ("week", 0),
    ("week", -1),
])
def test_create_with_an_invalid_field_returns_400_and_stores_nothing(flask_app, admin, field, value):
    resp = admin.post("/api/projects", json={**VALID, field: value})

    assert resp.status_code == 400
    assert field in resp.get_json()["error"]
    assert count_projects(flask_app) == 0


@pytest.mark.parametrize("field, value", [("title", "x" * 120), ("repo_url", "https://" + "u" * 247), ("week", 1)])
def test_create_accepts_the_values_at_the_limits(admin, field, value):
    assert admin.post("/api/projects", json={**VALID, field: value}).status_code == 201


# ---------- TC-API-07 / 10: el cuerpo tiene que ser JSON (H4)

def test_create_with_invalid_json_returns_400(admin):
    resp = admin.post("/api/projects", data="esto no es json", content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.parametrize("body", ["[]", "null", '"texto"', "5"])
def test_create_with_a_json_body_that_is_not_an_object_returns_400(admin, body):
    resp = admin.post("/api/projects", data=body, content_type="application/json")
    assert resp.status_code == 400


def test_create_rejects_a_body_that_is_not_declared_as_json_with_415(flask_app, admin):
    # Antes la API aceptaba cualquier Content-Type (get_json(force=True)). Un formulario de otro sitio solo puede
    # enviar text/plain o form-urlencoded: así queda fuera de lo que la API acepta.
    resp = admin.post("/api/projects", data='{"title": "x", "description": "d", "tech_stack": "a"}',
                      content_type="text/plain")

    assert resp.status_code == 415
    assert count_projects(flask_app) == 0


# ---------- TC-API-08: actualizar

def test_update_changes_only_the_fields_that_were_sent(flask_app, admin):
    pid = add_project(flask_app, title="Antes", description="Desc", tech_stack="a,b", week=4)

    resp = admin.put(f"/api/projects/{pid}", json={"title": "Después"})

    assert resp.status_code == 200
    body = admin.get(f"/api/projects/{pid}").get_json()
    assert body["title"] == "Después"
    assert (body["description"], body["tech_stack"], body["week"]) == ("Desc", ["a", "b"], 4)


def test_update_can_clear_the_optional_fields(flask_app, admin):
    pid = add_project(flask_app, week=4, repo_url="https://x")

    resp = admin.put(f"/api/projects/{pid}", json={"week": None, "repo_url": None})

    assert resp.status_code == 200
    assert resp.get_json()["week"] is None and resp.get_json()["repo_url"] is None


@pytest.mark.parametrize("payload", [{"title": ""}, {"title": "x" * 121}, {"week": "abc"}, {"tech_stack": []}])
def test_update_with_an_invalid_field_returns_400_and_changes_nothing(flask_app, admin, payload):
    pid = add_project(flask_app, title="Intacto", week=4)

    resp = admin.put(f"/api/projects/{pid}", json=payload)

    assert resp.status_code == 400
    assert admin.get(f"/api/projects/{pid}").get_json()["title"] == "Intacto"


def test_update_of_a_missing_project_returns_404(admin):
    assert admin.put("/api/projects/9999", json={"title": "x"}).status_code == 404


# ---------- TC-API-09: borrar

def test_delete_removes_the_project_and_a_second_delete_is_404(flask_app, admin):
    pid = add_project(flask_app)

    assert admin.delete(f"/api/projects/{pid}").status_code == 204
    assert admin.get(f"/api/projects/{pid}").status_code == 404
    assert admin.delete(f"/api/projects/{pid}").status_code == 404
    assert count_projects(flask_app) == 0
