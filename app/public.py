from pathlib import Path

from flask import Blueprint, current_app, render_template, send_from_directory

import ci_status
import content
from models import Project

public_bp = Blueprint("public", __name__)

PROJECT_TAGS = {4: "UI", 5: "API", 6: "CI/CD", 7: "BDD"}


def _cv_url():
    """URL del CV público (sin teléfono), o None si el PDF no está en static/cv/."""
    name = "cv/CV_Andres_Gonzalez.pdf"
    if (Path(current_app.static_folder) / name).is_file():
        return f"/static/{name}"
    return None


def _projects(lang: str, ci: dict):
    """Proyectos de la base, listos para el template (traducidos si es EN).

    `ci` es el snapshot de ci_status.get_status(): cada proyecto trae el estado
    real de su parte del CI (passing / failing / unknown), no un texto fijo.
    """
    items = []
    for p in Project.query.order_by(Project.week, Project.id).all():
        title, description = p.title, p.description
        if lang == "en" and p.title in content.PROJECT_EN:
            title, description = content.PROJECT_EN[p.title]
        case_page = content.CASE_STUDIES.get(p.repo_url or "")
        tag = PROJECT_TAGS.get(p.week, "QA")
        items.append({
            "title": title,
            "description": description,
            "tag": tag,
            "ci": ci["states"].get(tag, ci_status.UNKNOWN),
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
        cv_url=_cv_url(),
        **extra,
    )


def _overview(lang):
    ci = ci_status.get_status()
    return _render(
        "overview", lang, "site/overview.html",
        kpis=content.KPIS[lang],
        past_roles=content.PAST_ROLES[lang],
        projects=_projects(lang, ci),
        ci=ci,
    )


def _experience(lang):
    return _render("experience", lang, "site/experience.html", jobs=content.JOBS[lang])


def _case_ui(lang):
    ci = ci_status.get_status()
    return _render(
        "case_ui", lang, "site/case_ui.html",
        case=content.CASE_UI[lang],
        ci=ci,
        ci_state=ci["states"].get("UI", ci_status.UNKNOWN),
    )


@public_bp.get("/favicon.ico")
def favicon():
    return send_from_directory(Path(current_app.static_folder) / "img", "favicon.ico", mimetype="image/vnd.microsoft.icon")


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
