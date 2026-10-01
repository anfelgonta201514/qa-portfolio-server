from pathlib import Path

from flask import Blueprint, current_app, render_template

import content
from models import Project

public_bp = Blueprint("public", __name__)

PROJECT_TAGS = {4: "UI", 5: "API", 6: "CI/CD", 7: "BDD"}


def _cv_url(lang: str):
    """URL del CV del idioma pedido, o None si todavía no se subió el PDF.

    El CV no se versiona hasta tener una versión pública (sin teléfono): el
    botón de descarga solo aparece cuando existe el archivo en static/cv/.
    """
    name = f"cv/CV_Andres_Gonzalez_{lang}.pdf"
    if (Path(current_app.static_folder) / name).is_file():
        return f"/static/{name}"
    return None


def _projects(lang: str):
    """Proyectos de la base, listos para el template (traducidos si es EN)."""
    items = []
    for p in Project.query.order_by(Project.week, Project.id).all():
        title, description = p.title, p.description
        if lang == "en" and p.title in content.PROJECT_EN:
            title, description = content.PROJECT_EN[p.title]
        case_page = content.CASE_STUDIES.get(p.repo_url or "")
        items.append({
            "title": title,
            "description": description,
            "tag": PROJECT_TAGS.get(p.week, "QA"),
            "stack": [s.strip() for s in p.tech_stack.split(",") if s.strip()],
            "repo_url": p.repo_url,
            "case_url": content.PAGES[case_page][lang] if case_page else None,
        })
    return items


def _render(page: str, lang: str, template: str, **extra):
    other = "en" if lang == "es" else "es"
    return render_template(
        template,
        lang=lang,
        page=page,
        t=content.T[lang],
        urls={key: paths[lang] for key, paths in content.PAGES.items()},
        lang_urls={lang: content.PAGES[page][lang], other: content.PAGES[page][other]},
        alternates=content.PAGES[page],
        links={"linkedin": content.LINKEDIN, "github": content.GITHUB, "repo": content.REPO, "email": content.EMAIL},
        cv_url=_cv_url(lang),
        **extra,
    )


def _overview(lang):
    return _render(
        "overview", lang, "site/overview.html",
        kpis=content.KPIS[lang],
        past_roles=content.PAST_ROLES[lang],
        projects=_projects(lang),
    )


def _experience(lang):
    return _render("experience", lang, "site/experience.html", jobs=content.JOBS[lang])


def _case_ui(lang):
    return _render("case_ui", lang, "site/case_ui.html", case=content.CASE_UI[lang])


VIEWS = {"overview": _overview, "experience": _experience, "case_ui": _case_ui}

# Una regla por página e idioma (ej. /experiencia y /en/experience), con
# endpoints public.<página>_<idioma>.
for _page, _paths in content.PAGES.items():
    for _lang in content.LANGS:
        public_bp.add_url_rule(
            _paths[_lang],
            endpoint=f"{_page}_{_lang}",
            view_func=(lambda view, lang: lambda: view(lang))(VIEWS[_page], _lang),
        )
