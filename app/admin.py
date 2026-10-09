from flask import Blueprint, current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from models import Project, User, db
from validators import parse_project

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

LOGIN_ERROR = "Usuario o contraseña incorrectos"
LOCKED_ERROR = "Demasiados intentos fallidos. Prueba de nuevo más tarde."


def _client_ip() -> str:
    """Dirección del visitante para el límite de intentos.

    Nginx fija X-Real-IP con la IP real (`proxy_set_header X-Real-IP $remote_addr`) y Flask solo recibe tráfico de
    Nginx (el puerto 8000 no está publicado). Nunca X-Forwarded-For: un cliente puede añadirle lo que quiera.
    """
    return (request.headers.get("X-Real-IP") or request.remote_addr or "desconocida").strip()[:64]


@admin_bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/login.html")


@admin_bp.post("/login")
def login_post():
    throttle = current_app.extensions["login_throttle"]
    ip = _client_ip()
    wait = throttle.retry_after(ip)
    if wait:
        # Bloqueada: ni se mira la contraseña (con la correcta tampoco entra) y el intento no extiende el bloqueo.
        return render_template("admin/login.html", error=LOCKED_ERROR), 429, {"Retry-After": str(wait)}

    username = request.form.get("username", "")
    password = request.form.get("password", "")
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        throttle.record_success(ip)
        login_user(user)
        return redirect(url_for("admin.dashboard"))
    throttle.record_failure(ip)
    return render_template("admin/login.html", error=LOGIN_ERROR), 401


@admin_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


@admin_bp.get("/")
@login_required
def dashboard():
    projects = Project.query.order_by(Project.week, Project.id).all()
    return render_template("admin/dashboard.html", projects=projects)


@admin_bp.get("/projects/new")
@login_required
def new_project():
    return _form(values={}, editing=False)


@admin_bp.post("/projects/new")
@login_required
def create_project():
    clean, errors, values = _read_form()
    if errors:
        return _form(values, editing=False, error="; ".join(errors)), 400
    db.session.add(Project(**clean))
    db.session.commit()
    return redirect(url_for("admin.dashboard"))


@admin_bp.get("/projects/<int:project_id>/edit")
@login_required
def edit_project(project_id):
    project = db.get_or_404(Project, project_id)
    return _form(values=_values_of(project), editing=True)


@admin_bp.post("/projects/<int:project_id>/edit")
@login_required
def update_project(project_id):
    project = db.get_or_404(Project, project_id)
    clean, errors, values = _read_form()
    if errors:
        return _form(values, editing=True, error="; ".join(errors)), 400
    for key, value in clean.items():
        setattr(project, key, value)
    db.session.commit()
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/projects/<int:project_id>/delete")
@login_required
def delete_project(project_id):
    project = db.get_or_404(Project, project_id)
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for("admin.dashboard"))


def _form(values, editing, error=None):
    return render_template("admin/project_form.html", values=values, editing=editing, error=error)


def _values_of(project: Project) -> dict:
    return {"title": project.title, "description": project.description, "tech_stack": project.tech_stack,
            "repo_url": project.repo_url or "", "week": "" if project.week is None else project.week}


def _read_form():
    """(campos_limpios, errores, valores_escritos). Los valores se devuelven tal cual para no perder lo que se tecleó."""
    values = {key: request.form.get(key, "") for key in ("title", "description", "tech_stack", "repo_url", "week")}
    data = {key: values[key] for key in ("title", "description", "tech_stack", "repo_url")}
    week = values["week"].strip()
    if week:
        # Los campos del formulario llegan como texto: un entero se convierte; cualquier otra cosa se pasa tal cual
        # para que la validación la rechace con un mensaje (antes int() lanzaba ValueError y la página daba 500).
        data["week"] = int(week) if week.isdigit() else week
    else:
        data["week"] = None
    clean, errors = parse_project(data)
    return clean, errors, values
