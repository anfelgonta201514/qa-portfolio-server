from app import app
from models import Project, db

SAMPLE = {
    "title": "qa-automation-portfolio",
    "description": "UI testing (Playwright), API testing (pytest+requests), CI/CD (GitHub Actions), Docker y BDD (pytest-bdd), todo contra apps publicas de practica.",
    "tech_stack": "Playwright,pytest,requests,Docker,GitHub Actions,pytest-bdd",
    "repo_url": "https://github.com/anfelgonta201514/qa-automation-portfolio",
    "week": 7,
}

with app.app_context():
    db.create_all()
    if not Project.query.filter_by(title=SAMPLE["title"]).first():
        db.session.add(Project(**SAMPLE))
        db.session.commit()
        print("seeded")
    else:
        print("already seeded")
