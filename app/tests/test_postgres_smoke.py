"""Humo contra un PostgreSQL REAL (QAP-20; cubre la brecha SQLite vs. PostgreSQL de docs/qe/estrategia-de-pruebas.md, H5).

Las pruebas normales usan SQLite en memoria: es rápido, pero MÁS permisivo que producción (no limita VARCHAR(120), por
ejemplo). Estas pruebas repiten lo esencial contra la misma base que usa el sitio. Son opt-in: no corren salvo con
`-m postgres` y una base de PRUEBAS en POSTGRES_TEST_URL, por ejemplo:

    docker run --rm -d --name pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=portfolio_test -p 5432:5432 postgres:16-alpine
    POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5432/portfolio_test python -m pytest app/tests -m postgres -q

En CI (.github/workflows/deploy.yml) corren con un servicio postgres:16-alpine.

SEGURIDAD: cada prueba BORRA y recrea las tablas de esa base. Por eso se niega a correr si el nombre de la base no
contiene "test": nunca debe apuntar a la base real del sitio.
"""
import os

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DataError

from models import Project, db
from webhelpers import add_user, login

pytestmark = pytest.mark.postgres


@pytest.fixture
def pg_app(make_app, monkeypatch):
    url = os.environ.get("POSTGRES_TEST_URL")
    if not url:
        pytest.fail("Falta POSTGRES_TEST_URL (ver el docstring de este archivo).")
    parsed = make_url(url)
    if not parsed.get_backend_name() == "postgresql" or "test" not in (parsed.database or "").lower():
        pytest.fail(f"POSTGRES_TEST_URL debe ser PostgreSQL y su base debe llamarse algo con 'test' (es {parsed.database!r}): "
                    "estas pruebas borran las tablas.")
    monkeypatch.setenv("DATABASE_URL", url)
    app = make_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def test_the_app_really_runs_on_postgres(pg_app):
    with pg_app.app_context():
        assert db.engine.dialect.name == "postgresql"


def test_crud_through_the_api_round_trips_on_postgres(pg_app):
    add_user(pg_app)
    client = pg_app.test_client()
    assert login(client).status_code == 302

    created = client.post("/api/projects", json={"title": "En Postgres", "description": "D", "tech_stack": ["a", "b"],
                                                  "repo_url": "https://x.example/r", "week": 8})
    assert created.status_code == 201
    pid = created.get_json()["id"]

    assert client.get(f"/api/projects/{pid}").get_json()["tech_stack"] == ["a", "b"]
    assert client.put(f"/api/projects/{pid}", json={"week": None}).get_json()["week"] is None
    assert client.delete(f"/api/projects/{pid}").status_code == 204
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_the_title_limit_is_enforced_before_the_database_does(pg_app):
    # Este es el caso H5: SQLite guarda 121 caracteres, PostgreSQL no. La validación debe responder 400, no 500.
    add_user(pg_app)
    client = pg_app.test_client()
    login(client)

    resp = client.post("/api/projects", json={"title": "x" * 121, "description": "D", "tech_stack": "a"})

    assert resp.status_code == 400
    assert client.get("/api/projects").get_json() == []


def test_postgres_really_is_stricter_than_sqlite_here(pg_app):
    # Documenta la premisa de H5: sin la validación, la base rechaza el título largo (error de base de datos -> 500).
    with pg_app.app_context():
        db.session.add(Project(title="x" * 121, description="D", tech_stack="a"))
        with pytest.raises(DataError):
            db.session.commit()
        db.session.rollback()


def test_values_at_the_column_limits_are_accepted_on_postgres(pg_app):
    add_user(pg_app)
    client = pg_app.test_client()
    login(client)

    resp = client.post("/api/projects", json={"title": "x" * 120, "description": "D", "tech_stack": "a" * 255,
                                              "repo_url": "https://" + "u" * 247})

    assert resp.status_code == 201


def test_projects_with_a_week_come_ordered_by_week_on_postgres(pg_app):
    # Ojo: SQLite ordena los NULL primero y PostgreSQL al final; por eso solo se comprueba el orden de los que tienen semana.
    add_user(pg_app)
    client = pg_app.test_client()
    login(client)
    for title, week in (("seis", 6), ("sin semana", None), ("cuatro", 4)):
        assert client.post("/api/projects", json={"title": title, "description": "D", "tech_stack": "a", "week": week}).status_code == 201

    titles = [p["title"] for p in client.get("/api/projects").get_json() if p["week"] is not None]

    assert titles == ["cuatro", "seis"]


def test_admin_login_and_the_throttle_work_on_postgres(pg_app):
    add_user(pg_app)
    client = pg_app.test_client()

    assert login(client, "admin", "mal").status_code == 401
    assert login(client).status_code == 302
    assert client.get("/admin/").status_code == 200
