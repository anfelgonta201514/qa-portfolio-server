from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from models import Project, User, db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/login.html")


@admin_bp.post("/login")
def login_post():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        login_user(user)
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/login.html", error="Usuario o contraseña incorrectos"), 401


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
    return render_template("admin/project_form.html", project=None)


@admin_bp.post("/projects/new")
@login_required
def create_project():
    _save_project_from_form(Project())
    return redirect(url_for("admin.dashboard"))


@admin_bp.get("/projects/<int:project_id>/edit")
@login_required
def edit_project(project_id):
    project = db.get_or_404(Project, project_id)
    return render_template("admin/project_form.html", project=project)


@admin_bp.post("/projects/<int:project_id>/edit")
@login_required
def update_project(project_id):
    project = db.get_or_404(Project, project_id)
    _save_project_from_form(project)
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/projects/<int:project_id>/delete")
@login_required
def delete_project(project_id):
    project = db.get_or_404(Project, project_id)
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for("admin.dashboard"))


def _save_project_from_form(project: Project) -> None:
    project.title = request.form["title"]
    project.description = request.form["description"]
    project.tech_stack = request.form["tech_stack"]
    project.repo_url = request.form.get("repo_url") or None
    week = request.form.get("week")
    project.week = int(week) if week else None
    if project.id is None:
        db.session.add(project)
    db.session.commit()
