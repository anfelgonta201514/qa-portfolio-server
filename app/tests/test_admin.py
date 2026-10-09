"""Pruebas del panel /admin (QAP-20; casos TC-ADM-01 a TC-ADM-08 de docs/qe/plan-de-pruebas.md).

Integración con el cliente de Flask sobre SQLite en memoria. El CSRF queda ACTIVO como en producción: cada POST usa el
token que trae una página real. Hallazgo que fijan: H6 (el login no tenía límite de intentos).
"""
import pytest

from webhelpers import PASSWORD, add_project, add_user, count_projects, csrf_token, login, post_form

BAD = "Usuario o contraseña incorrectos"
FORM = {"title": "Desde el formulario", "description": "Texto", "tech_stack": "a,b", "repo_url": "", "week": "9"}


@pytest.fixture
def client(flask_app):
    add_user(flask_app)
    return flask_app.test_client()


@pytest.fixture
def admin(client):
    assert login(client).status_code == 302
    return client


# ---------- TC-ADM-01 / 02: iniciar sesión

def test_valid_login_redirects_to_the_dashboard_and_lists_the_projects(flask_app, client):
    add_project(flask_app, title="Visible en el panel")

    resp = login(client)

    assert resp.status_code == 302 and resp.headers["Location"].endswith("/admin/")
    assert "Visible en el panel" in client.get("/admin/").get_data(as_text=True)


@pytest.mark.parametrize("username, password", [("admin", "equivocada"), ("nadie", PASSWORD), ("", ""), ("admin", "")])
def test_invalid_login_returns_401_with_the_same_generic_message(client, username, password):
    resp = login(client, username, password)

    assert resp.status_code == 401
    assert BAD in resp.get_data(as_text=True)               # no revela si falló el usuario o la contraseña
    assert client.get("/admin/").status_code == 302         # y no quedó ninguna sesión


def test_a_logged_in_visitor_who_opens_the_login_page_goes_to_the_dashboard(admin):
    assert admin.get("/admin/login").headers["Location"].endswith("/admin/")


# ---------- TC-ADM-03: CSRF

def test_login_without_a_csrf_token_returns_400(client):
    assert client.post("/admin/login", data={"username": "admin", "password": PASSWORD}).status_code == 400


def test_login_with_a_wrong_csrf_token_returns_400(client):
    resp = client.post("/admin/login", data={"username": "admin", "password": PASSWORD, "csrf_token": "falso"})
    assert resp.status_code == 400


def test_admin_forms_without_a_csrf_token_are_rejected_and_change_nothing(flask_app, admin):
    pid = add_project(flask_app)

    assert admin.post("/admin/projects/new", data=FORM).status_code == 400
    assert admin.post(f"/admin/projects/{pid}/delete").status_code == 400
    assert admin.post("/admin/logout").status_code == 400
    assert count_projects(flask_app) == 1
    assert admin.get("/admin/").status_code == 200           # la sesión sigue viva


# ---------- TC-ADM-04: rutas protegidas

@pytest.mark.parametrize("path", ["/admin/", "/admin/projects/new", "/admin/projects/1/edit"])
def test_protected_pages_redirect_to_the_login_without_a_session(flask_app, client, path):
    add_project(flask_app)

    resp = client.get(path)

    assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]


@pytest.mark.parametrize("path", ["/admin/projects/new", "/admin/projects/1/edit", "/admin/projects/1/delete",
                                  "/admin/logout"])
def test_protected_posts_with_a_valid_token_still_need_a_session(flask_app, client, path):
    add_project(flask_app, title="Intacto")

    resp = client.post(path, data={**FORM, "csrf_token": csrf_token(client)})

    assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]
    assert count_projects(flask_app) == 1


# ---------- TC-ADM-05: alta, edición y borrado desde el formulario

def test_create_edit_and_delete_from_the_forms_are_reflected_in_the_dashboard_and_the_api(flask_app, admin):
    assert post_form(admin, "/admin/projects/new", FORM).status_code == 302
    created = admin.get("/api/projects").get_json()
    assert [(p["title"], p["week"], p["repo_url"]) for p in created] == [("Desde el formulario", 9, None)]
    pid = created[0]["id"]

    assert post_form(admin, f"/admin/projects/{pid}/edit", {**FORM, "title": "Editado", "week": ""}).status_code == 302
    edited = admin.get(f"/api/projects/{pid}").get_json()
    assert edited["title"] == "Editado" and edited["week"] is None
    assert "Editado" in admin.get("/admin/").get_data(as_text=True)

    assert post_form(admin, f"/admin/projects/{pid}/delete", {}).status_code == 302
    assert admin.get(f"/api/projects/{pid}").status_code == 404


def test_editing_or_deleting_a_missing_project_returns_404(admin):
    assert admin.get("/admin/projects/9999/edit").status_code == 404
    assert post_form(admin, "/admin/projects/9999/delete", {}).status_code == 404


# ---------- TC-ADM-06: datos inválidos en el formulario

@pytest.mark.parametrize("override", [
    {"week": "abc"},                       # antes: ValueError -> 500
    {"week": "0"},
    {"week": "1.5"},
    {"title": ""},
    {"title": "x" * 121},                  # en PostgreSQL daría un error de base de datos
    {"description": "   "},
    {"tech_stack": ""},
    {"repo_url": "https://" + "u" * 248},
    {"repo_url": "javascript:alert(1)"},
])
def test_invalid_form_data_shows_an_error_and_stores_nothing(flask_app, admin, override):
    resp = post_form(admin, "/admin/projects/new", {**FORM, **override})

    assert resp.status_code == 400
    assert 'class="error"' in resp.get_data(as_text=True)
    assert count_projects(flask_app) == 0


def test_invalid_form_data_keeps_what_the_admin_typed(admin):
    resp = post_form(admin, "/admin/projects/new", {**FORM, "week": "abc", "title": "Lo que escribí"})

    assert resp.status_code == 400
    assert "Lo que escribí" in resp.get_data(as_text=True)


def test_an_invalid_edit_changes_nothing(flask_app, admin):
    pid = add_project(flask_app, title="Intacto", week=4)

    resp = post_form(admin, f"/admin/projects/{pid}/edit", {**FORM, "week": "abc"})

    assert resp.status_code == 400
    assert admin.get(f"/api/projects/{pid}").get_json()["title"] == "Intacto"


def test_a_form_without_a_title_field_is_a_400_not_a_500(flask_app, admin):
    data = {k: v for k, v in FORM.items() if k != "title"}
    assert post_form(admin, "/admin/projects/new", data).status_code == 400
    assert count_projects(flask_app) == 0


# ---------- TC-ADM-07: cerrar sesión

def test_logout_ends_the_session(admin):
    resp = post_form(admin, "/admin/logout", {})

    assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]
    assert admin.get("/admin/").status_code == 302
    assert admin.post("/api/projects", json={"title": "t", "description": "d", "tech_stack": "a"}).status_code == 401


def test_logout_is_post_only(admin):
    assert admin.get("/admin/logout").status_code == 405


# ---------- TC-ADM-08: límite de intentos fallidos (H6)

def _fail(client, n, headers=None):
    return [login(client, "admin", "mal", headers=headers).status_code for _ in range(n)]


def test_after_too_many_failures_the_login_is_blocked_with_429_and_retry_after(make_app):
    app = make_app(LOGIN_MAX_FAILURES=3, LOGIN_WINDOW_SECONDS=600)
    add_user(app)
    client = app.test_client()

    assert _fail(client, 3) == [401, 401, 401]
    blocked = login(client, "admin", "mal")

    assert blocked.status_code == 429
    assert 0 < int(blocked.headers["Retry-After"]) <= 600
    assert BAD not in blocked.get_data(as_text=True)


def test_a_blocked_address_cannot_log_in_even_with_the_right_password(make_app):
    app = make_app(LOGIN_MAX_FAILURES=2)
    add_user(app)
    client = app.test_client()
    _fail(client, 2)

    assert login(client).status_code == 429
    assert client.get("/admin/").status_code == 302          # sigue sin sesión


def test_the_limit_is_per_address_so_one_attacker_does_not_lock_out_everyone(make_app):
    app = make_app(LOGIN_MAX_FAILURES=2)
    add_user(app)
    attacker, owner = app.test_client(), app.test_client()
    _fail(attacker, 2, headers={"X-Real-IP": "203.0.113.7"})

    assert login(attacker, headers={"X-Real-IP": "203.0.113.7"}).status_code == 429
    assert login(owner, headers={"X-Real-IP": "198.51.100.2"}).status_code == 302


def test_a_successful_login_clears_the_failures_of_that_address(make_app):
    app = make_app(LOGIN_MAX_FAILURES=3)
    add_user(app)
    client = app.test_client()
    _fail(client, 2)
    assert login(client).status_code == 302
    post_form(client, "/admin/logout", {})

    assert _fail(client, 2) == [401, 401]                    # vuelve a tener sus 3 intentos
    assert login(client, "admin", "mal").status_code == 401


def test_the_limit_has_a_sane_default(flask_app):
    add_user(flask_app)
    client = flask_app.test_client()
    results = _fail(client, 5)

    assert results == [401] * 5                              # por defecto se permiten 5 fallos...
    assert login(client, "admin", "mal").status_code == 429  # ...y el sexto intento se frena
