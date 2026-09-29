import os

from flask import Flask, jsonify

from models import Project, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
db.init_app(app)

# Sin Flask-Migrate todavía: con un solo modelo y sin datos reales en
# producción, create_all() alcanza. Introducir migraciones (Alembic) antes
# de que el schema deje de ser trivial o haya datos reales que no se puedan
# perder en un cambio de columnas.
with app.app_context():
    db.create_all()


@app.get("/")
def index():
    return {"status": "ok", "message": "qa-portfolio-server: hello world"}


@app.get("/api/projects")
def list_projects():
    projects = Project.query.order_by(Project.week, Project.id).all()
    return jsonify([p.to_dict() for p in projects])


@app.get("/api/projects/<int:project_id>")
def get_project(project_id):
    project = db.get_or_404(Project, project_id)
    return jsonify(project.to_dict())


# Sin endpoints de escritura (POST/PUT/DELETE) todavía a propósito: el
# server está expuesto públicamente y no hay autenticación hasta el panel
# admin de la semana 10 (Flask-Login). Publicar escritura sin auth ahora
# dejaría la base editable por cualquiera.
