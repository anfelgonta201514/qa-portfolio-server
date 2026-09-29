from app import app
from models import Project, db

# Contenido real de qa-automation-portfolio (semanas 4-7), una entrada por
# deliverable en vez de una sola combinada — así se puede enlazar cada uno
# a su carpeta específica del repo.
PROJECTS = [
    {
        "title": "UI Testing — Playwright + Page Object Model",
        "description": "Suite Playwright + pytest contra Restful Booker Platform (app pública de práctica): flujo completo de reserva, panel de administración, batería de datos parametrizada desde Excel y BDD con pytest-bdd. Page Object Model estricto, capturas de fallo automáticas y reportes Allure.",
        "tech_stack": "Playwright,pytest,Page Object Model,Allure,pytest-bdd",
        "repo_url": "https://github.com/anfelgonta201514/qa-automation-portfolio/tree/master/ui-tests/booking-flow",
        "week": 4,
    },
    {
        "title": "API Testing — pytest + requests",
        "description": "Suite pytest + requests contra Restful-booker (API pública de práctica): CRUD completo con validación de schema vía pydantic, autenticación por token, y casos negativos documentando inconsistencias reales de la API (status codes que no siguen REST).",
        "tech_stack": "pytest,requests,pydantic",
        "repo_url": "https://github.com/anfelgonta201514/qa-automation-portfolio/tree/master/api-tests/restful-booker",
        "week": 5,
    },
    {
        "title": "CI/CD — GitHub Actions",
        "description": "Pipeline de CI con dos jobs paralelos (API y UI en matrix cross-browser Chromium/Firefox/WebKit), corriendo dentro de la misma imagen Docker que se usa en local, con caché de capas y badge de estado en el README.",
        "tech_stack": "GitHub Actions,Docker,cross-browser testing",
        "repo_url": "https://github.com/anfelgonta201514/qa-automation-portfolio/blob/master/.github/workflows/tests.yml",
        "week": 6,
    },
    {
        "title": "Docker + BDD",
        "description": "Una sola imagen Docker reutilizada en local y en CI (nunca se instala Python/Playwright nativo en el runner). Escenarios de negocio en Gherkin (pytest-bdd) que reutilizan los mismos Page Objects que la suite \"plana\", legibles por alguien sin conocimientos técnicos.",
        "tech_stack": "Docker,pytest-bdd,Gherkin",
        "repo_url": "https://github.com/anfelgonta201514/qa-automation-portfolio",
        "week": 7,
    },
]

OLD_COMBINED_TITLE = "qa-automation-portfolio"

with app.app_context():
    db.create_all()

    old = Project.query.filter_by(title=OLD_COMBINED_TITLE).first()
    if old:
        db.session.delete(old)
        db.session.commit()
        print(f"eliminada la entrada combinada anterior ('{OLD_COMBINED_TITLE}')")

    for data in PROJECTS:
        if not Project.query.filter_by(title=data["title"]).first():
            db.session.add(Project(**data))
            print(f"seeded: {data['title']}")
        else:
            print(f"ya existía: {data['title']}")

    db.session.commit()
