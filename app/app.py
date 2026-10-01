import os

from flask import Flask
from flask_login import LoginManager
from flask_wtf import CSRFProtect

from models import User, db


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
    # pool_pre_ping: antes de usar una conexión del pool, la prueba con un
    # "SELECT 1" liviano. Sin esto, si Postgres se reinicia (ej. un deploy
    # que recrea ese contenedor) mientras `app` sigue corriendo, el pool se
    # queda con conexiones muertas y el próximo request revienta con
    # "server closed the connection unexpectedly" en vez de reconectar solo.
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

    db.init_app(app)

    csrf = CSRFProtect()
    csrf.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "admin.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from admin import admin_bp
    from api import api_bp
    from public import public_bp

    # Sitio público (overview, experiencia, casos de estudio) en español e
    # inglés — rutas y textos en public.py / content.py.
    app.register_blueprint(public_bp)

    app.register_blueprint(api_bp)
    # La API es para consumo programático (frontend público, futuros
    # scripts/demos), no formularios de navegador con cookie de sesión, así
    # que no necesita el token CSRF que sí protege los formularios de /admin.
    csrf.exempt(api_bp)
    app.register_blueprint(admin_bp)

    # Sin Flask-Migrate todavía: mientras el schema sea chico y no haya
    # datos reales que no se puedan perder en un cambio de columnas,
    # create_all() alcanza. Introducir Alembic antes de que deje de serlo.
    with app.app_context():
        db.create_all()

    return app


app = create_app()
