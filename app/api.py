from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import current_user

from models import Project, db
from validators import parse_project

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/projects")
def list_projects():
    projects = Project.query.order_by(Project.week, Project.id).all()
    return jsonify([p.to_dict() for p in projects])


@api_bp.get("/projects/<int:project_id>")
def get_project(project_id):
    project = db.get_or_404(Project, project_id)
    return jsonify(project.to_dict())


# Los tres endpoints de abajo requieren sesión de admin (la misma cookie que usa
# el panel /admin). El server es público: sin esto cualquiera podría reescribir
# el contenido del portafolio.
#
# Se usa un decorador propio en vez de flask_login.login_required porque ese
# redirige al formulario de login (302 + HTML): un cliente de la API necesita un
# 401 con cuerpo JSON (QAP-20, H3).


def api_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify(error="Se requiere iniciar sesión como administrador."), 401
        return view(*args, **kwargs)
    return wrapped


def _json_body():
    """(objeto, None) si el cuerpo es un objeto JSON; (None, respuesta_de_error) si no.

    Se exige `Content-Type: application/json` (415 si no). La API está exenta de CSRF porque la usan clientes
    programáticos; rechazar otros tipos de contenido deja fuera lo único que un formulario de OTRO sitio puede
    enviar (text/plain o form-urlencoded) y evita que el CSRF exento sea explotable (QAP-20, H4).
    """
    if not request.is_json:
        return None, (jsonify(error="El cuerpo debe ser JSON (Content-Type: application/json)."), 415)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify(error="El cuerpo debe ser un objeto JSON válido."), 400)
    return data, None


def _invalid(errors):
    return jsonify(error="; ".join(errors)), 400


@api_bp.post("/projects")
@api_login_required
def create_project():
    data, error = _json_body()
    if error:
        return error
    clean, errors = parse_project(data)
    if errors:
        return _invalid(errors)
    project = Project(**clean)
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@api_bp.put("/projects/<int:project_id>")
@api_login_required
def update_project(project_id):
    project = db.get_or_404(Project, project_id)
    data, error = _json_body()
    if error:
        return error
    clean, errors = parse_project(data, partial=True)
    if errors:
        return _invalid(errors)
    for key, value in clean.items():
        setattr(project, key, value)
    db.session.commit()
    return jsonify(project.to_dict())


@api_bp.delete("/projects/<int:project_id>")
@api_login_required
def delete_project(project_id):
    project = db.get_or_404(Project, project_id)
    db.session.delete(project)
    db.session.commit()
    return "", 204
