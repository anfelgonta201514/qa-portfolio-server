"""Ayudas comunes de las pruebas de la API y del panel admin (QAP-20)."""
import re

from werkzeug.security import generate_password_hash

from models import Project, User, db

PASSWORD = "clave-solo-para-pruebas"
# El hash por defecto (scrypt) tarda ~0,1 s: en cientos de pruebas suma decenas de segundos. Se calcula UNA vez y con un
# método barato; check_password_hash lee el método del propio hash, así que el código de producción se ejercita igual.
_HASH = generate_password_hash(PASSWORD, method="pbkdf2:sha256:1")

_TOKEN = re.compile(r'name="csrf_token" value="([^"]+)"')


def add_user(app, username="admin", password=PASSWORD):
    with app.app_context():
        user = User(username=username)
        user.password_hash = _HASH if password == PASSWORD else generate_password_hash(password, method="pbkdf2:sha256:1")
        db.session.add(user)
        db.session.commit()


def add_project(app, title="Proyecto", description="Descripción", tech_stack="a,b", week=None, repo_url=None):
    with app.app_context():
        project = Project(title=title, description=description, tech_stack=tech_stack, week=week, repo_url=repo_url)
        db.session.add(project)
        db.session.commit()
        return project.id


def count_projects(app):
    with app.app_context():
        return Project.query.count()


def csrf_token(client, path="/admin/login"):
    """Token CSRF tal como lo obtiene un navegador: del formulario de una página real."""
    page = client.get(path).get_data(as_text=True)
    match = _TOKEN.search(page)
    assert match, f"{path} no trae token CSRF"
    return match.group(1)


def login(client, username="admin", password=PASSWORD, headers=None):
    token = csrf_token(client)
    return client.post("/admin/login", data={"username": username, "password": password, "csrf_token": token},
                       headers=headers or {})


def post_form(client, path, data, token_page="/admin/"):
    """POST de formulario con un token CSRF válido (el token sale de una página que lo contenga)."""
    return client.post(path, data={**data, "csrf_token": csrf_token(client, token_page)})
