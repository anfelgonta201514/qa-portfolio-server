from flask import Blueprint, jsonify, request
from flask_login import login_required

from models import Project, db

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _tech_stack_to_str(value) -> str:
    return ",".join(value) if isinstance(value, list) else str(value or "")


@api_bp.get("/projects")
def list_projects():
    projects = Project.query.order_by(Project.week, Project.id).all()
    return jsonify([p.to_dict() for p in projects])


@api_bp.get("/projects/<int:project_id>")
def get_project(project_id):
    project = db.get_or_404(Project, project_id)
    return jsonify(project.to_dict())


# Los tres endpoints de abajo requieren sesión de admin (@login_required,
# la misma cookie que usa el panel /admin). El server es público: sin esto
# cualquiera podría reescribir el contenido del portafolio.


@api_bp.post("/projects")
@login_required
def create_project():
    data = request.get_json(force=True)
    project = Project(
        title=data["title"],
        description=data["description"],
        tech_stack=_tech_stack_to_str(data.get("tech_stack")),
        repo_url=data.get("repo_url"),
        week=data.get("week"),
    )
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@api_bp.put("/projects/<int:project_id>")
@login_required
def update_project(project_id):
    project = db.get_or_404(Project, project_id)
    data = request.get_json(force=True)
    project.title = data.get("title", project.title)
    project.description = data.get("description", project.description)
    if "tech_stack" in data:
        project.tech_stack = _tech_stack_to_str(data["tech_stack"])
    project.repo_url = data.get("repo_url", project.repo_url)
    project.week = data.get("week", project.week)
    db.session.commit()
    return jsonify(project.to_dict())


@api_bp.delete("/projects/<int:project_id>")
@login_required
def delete_project(project_id):
    project = db.get_or_404(Project, project_id)
    db.session.delete(project)
    db.session.commit()
    return "", 204
