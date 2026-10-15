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
    # Semanas 8-14 (QAP-23): trabajo de qa-portfolio-server (este sitio). Sus traducciones al inglés están en
    # content.PROJECT_EN y su etiqueta en content.PROJECT_TAG_BY_TITLE, con el título como clave: cambiar un título
    # aquí exige cambiarlo en esos dos sitios (una prueba lo vigila). Los enlaces apuntan a rutas que existen en main.
    {
        "title": "Servidor propio — Docker + deploy automático",
        "description": "Este sitio corre en un servidor propio (Oracle Cloud Always Free, ARM): Nginx, Flask/Gunicorn y PostgreSQL en contenedores con Docker Compose y HTTPS con renovación automática. Cada push a main dispara GitHub Actions: corren las pruebas y solo si pasan se despliega por SSH, con una clave atada a un único script (forced command). También se comprobó el camino rojo: una prueba rota deja el deploy en «skipped».",
        "tech_stack": "Docker Compose,Nginx,PostgreSQL,GitHub Actions,Let's Encrypt,Oracle Cloud",
        "repo_url": "https://github.com/anfelgonta201514/qa-portfolio-server",
        "week": 8,
    },
    {
        "title": "Routines de Claude Code — CI y review de PRs",
        "description": "Dos agentes programados de Claude Code vigilan el repo de automatización: uno revisa cada noche el estado del CI y avisa a Slack; otro comenta cada PR abierto con un checklist de QA basado en las reglas del repo. El webhook de GitHub nunca disparó, así que el review corre por cron horario: un límite de la plataforma que quedó documentado.",
        "tech_stack": "Claude Code Routines,GitHub App,Slack,cron",
        "repo_url": "https://github.com/anfelgonta201514/qa-portfolio-server/blob/main/CLAUDE.md",
        "week": 11,
    },
    {
        "title": "MCP — del test fallido al ticket",
        "description": "Una falla real de Playwright se analiza a partir del aria snapshot, crea un bug en Jira y avisa a Slack mediante conectores MCP. Del flujo salió un hallazgo real: el test negativo de login partía de una premisa falsa (la app sí muestra «Invalid credentials»), corregido en QAP-7. Incluye un reporte de sprint generado desde Jira. Limitación conocida: los conectores solo envían texto, no adjuntos.",
        "tech_stack": "MCP,Jira,Slack,Playwright,Claude",
        "repo_url": "https://github.com/anfelgonta201514/qa-portfolio-server/blob/main/docs/reporte-qe-semana-12.md",
        "week": 12,
    },
    {
        "title": "Demos de IA aplicada a QA",
        "description": "Tres demos (casos de prueba, reporte de bugs y tests de API) con ejemplos pregenerados y un modo en vivo con Groq: capa de proveedor intercambiable, límite por visitante y tope diario, y respaldo a los ejemplos si el proveedor falla. Cada respuesta declara el modelo que la generó y que es un borrador sin verificar. La calidad se midió con una rúbrica de 30 puntos (14 → 21 → 21 tras dos rondas de ajustes), con lo que no mejoró documentado.",
        "tech_stack": "Groq,Flask,rate limiting,pytest,rúbrica de evaluación",
        "repo_url": "https://github.com/anfelgonta201514/qa-portfolio-server/blob/main/docs/rubrica-medicion-ia.md",
        "week": 13,
    },
    {
        "title": "Calidad del propio sitio — pruebas, seguridad y documentación",
        "description": "Más de 500 pruebas automáticas (algunas de red y de humo con PostgreSQL son opt-in) sobre la API, el login, el panel y la configuración: cookies HttpOnly/Secure/SameSite, cabeceras de seguridad (CSP en modo informe), límite de intentos de login, URLs https y vista previa para compartir. Las pruebas nuevas se validaron plantando fallos a propósito. Además, estrategia, plan de pruebas, reporte ejecutivo y análisis de historias, generados con Claude e indicando qué se ejecutó y qué solo se infirió.",
        "tech_stack": "pytest,Flask-WTF,Nginx,pruebas de mutación manuales,IEEE 829",
        "repo_url": "https://github.com/anfelgonta201514/qa-portfolio-server/tree/main/docs/qe",
        "week": 13,
    },
    {
        "title": "Backup y recuperación — PostgreSQL",
        "description": "Backup diario con systemd: pg_dump comprimido que solo se da por bueno si pasa gzip y una comprobación del pie del dump, rotación de 7 diarios y 4 semanales, y una prueba de restauración en una base temporal. Se probó contra un Postgres real y esa prueba encontró un fallo que las pruebas de texto no veían. Además, un snapshot del disco en Oracle y un script para bajar los dumps a otro equipo.",
        "tech_stack": "systemd,pg_dump,Bash,PowerShell,snapshot de OCI",
        "repo_url": "https://github.com/anfelgonta201514/qa-portfolio-server/blob/main/deploy/backup-db.sh",
        "week": 14,
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
