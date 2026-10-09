import math
from pathlib import Path

from flask import Blueprint, abort, current_app, render_template, request, send_from_directory, url_for

import ci_status
import content
import demo_content
from models import Project
from request_ip import client_ip

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


def _demos(lang, live=None):
    """Página de demos. `live` es el resultado de un intento en vivo (None al abrir la página)."""
    service = current_app.extensions["demo_service"]
    live_enabled = service.provider is not None
    return _render(
        "demos", lang, "site/demos.html",
        d=demo_content.UI[lang],
        model=demo_content.MODEL,
        order=demo_content.DEMO_ORDER,
        examples={key: demo_content.EXAMPLES[key][lang] for key in demo_content.DEMO_ORDER},
        # Todo lo de abajo solo se usa con el modo en vivo encendido; apagado, la página es la de siempre.
        live_enabled=live_enabled,
        live=live,
        live_action=url_for(f"public.demo_live_{lang}") if live_enabled else None,
        live_max=service.config.max_input_chars,
        live_provider=service.provider.name.title() if live_enabled else "",
    )


def _live_message(lang, result, service):
    """Texto para el visitante cuando NO hubo respuesta en vivo (entrada inválida, límite o fallo del proveedor)."""
    template = demo_content.UI[lang]["live_messages"].get(result.reason, demo_content.UI[lang]["live_messages"]["provider_error"])
    minutes = max(1, math.ceil((result.retry_after or 0) / 60))
    return template.format(max=service.config.max_input_chars, minutes=minutes)


def _demo_live(lang):
    """POST del formulario de un demo: genera una respuesta en vivo o, si no se puede, deja los ejemplos pregenerados.

    La entrada del visitante va solo al servicio (que la manda al proveedor como mensaje de usuario); aquí no se
    registra ni se guarda. El CSRF lo exige CSRFProtect como en cualquier formulario.
    """
    service = current_app.extensions["demo_service"]
    if service.provider is None:
        abort(404)                      # modo en vivo apagado: este endpoint no existe

    demo = request.form.get("demo", "")
    text = request.form.get("input", "")
    result = service.run(demo, text, visitor_id=client_ip(), lang=lang)

    live = {
        "key": demo if demo in demo_content.DEMO_ORDER else None,
        "mode": result.mode,
        "reason": result.reason,
        "text": result.text,
        "provider": (result.provider or "").title(),
        "model": result.model,
        "truncated": result.truncated,
        "typed": text,
        "message": None if result.mode == "live" else _live_message(lang, result, service),
    }
    status, headers = 200, {}
    if result.mode == "rejected":
        status = 400
    elif result.mode == "fallback" and result.reason in ("visitor_limit", "daily_limit"):
        status, headers = 429, {"Retry-After": str(result.retry_after or 60)}
    return _demos(lang, live=live), status, headers


@public_bp.get("/favicon.ico")
def favicon():
    return send_from_directory(Path(current_app.static_folder) / "img", "favicon.ico", mimetype="image/vnd.microsoft.icon")


VIEWS = {"overview": _overview, "experience": _experience, "case_ui": _case_ui, "demos": _demos}

# Una regla por página e idioma (ej. /experiencia y /en/experience), con
# endpoints public.<página>_<idioma>.
for _page, _paths in content.PAGES.items():
    for _lang in content.LANGS:
        public_bp.add_url_rule(
            _paths[_lang],
            endpoint=f"{_page}_{_lang}",
            view_func=(lambda view, lang: lambda: view(lang))(VIEWS[_page], _lang),
        )

# Endpoint de los formularios de los demos en vivo (QAP-18): POST /demos/live y POST /en/demos/live.
# Solo existe (si no, 404) con el modo en vivo encendido.
for _lang, _path in (("es", "/demos/live"), ("en", "/en/demos/live")):
    public_bp.add_url_rule(
        _path,
        endpoint=f"demo_live_{_lang}",
        methods=["POST"],
        view_func=(lambda lang: lambda: _demo_live(lang))(_lang),
    )
