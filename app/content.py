"""Textos del sitio público en español e inglés.

Todo el copy vive acá (no en los templates) para que las dos versiones se
mantengan juntas: si se cambia una frase, se cambia en los dos idiomas en el
mismo lugar. Los proyectos siguen saliendo de la base de datos (panel admin);
PROJECT_EN solo traduce los textos de los proyectos ya cargados.
"""

LANGS = ("es", "en")

# Rutas públicas de cada página, por idioma. El selector ES/EN del header
# enlaza a la ruta equivalente en el otro idioma.
PAGES = {
    "overview": {"es": "/", "en": "/en/"},
    "experience": {"es": "/experiencia", "en": "/en/experience"},
    "case_ui": {"es": "/proyectos/ui-playwright", "en": "/en/projects/ui-playwright"},
}

LINKEDIN = "https://linkedin.com/in/andres-felipe-gonzalez-tamayo"
GITHUB = "https://github.com/anfelgonta201514"
REPO = "https://github.com/anfelgonta201514/qa-automation-portfolio"
EMAIL = "andresfelgonta@gmail.com"

# Proyecto (por repo_url) → página de caso de estudio. Los que no están acá
# enlazan directo a su código en GitHub.
CASE_STUDIES = {
    "https://github.com/anfelgonta201514/qa-automation-portfolio/tree/master/ui-tests/booking-flow": "case_ui",
}

T = {
    "es": {
        "html_title": "Andrés González — QA Automation Engineer",
        "meta_description": "QA Automation Engineer con 3.5+ años en automatización de pruebas: Python, Selenium, Playwright, pytest y CI/CD.",
        "nav_overview": "Overview",
        "nav_experience": "Experiencia",
        "nav_projects": "Proyectos",
        "nav_site": "Este sitio",
        "nav_demos": "Demos IA",
        "soon": "pronto",
        "available": "Disponible",
        "open_to": "Abierto a roles de QA Automation / SDET",
        "remote": "Remoto · GMT-5",
        "talk": "Hablemos",
        "cv_file": "CV_Andres_Gonzalez.pdf",
        "follow": "Sígueme",
        "lang_label": "Idioma",
        "menu": "Menú",
        "footer": "Hecho, desplegado y probado en andresqe.duckdns.org",
        "crumb_experience": "experiencia",
        "crumb_projects": "proyectos",
        # overview
        "eyebrow": "Hola, soy Andrés · QA Automation Engineer",
        "h1_a": "Calidad que se puede ",
        "h1_b": "demostrar",
        "lead": "Construyo frameworks de automatización escalables en Python, Selenium y Playwright, y los conecto a CI/CD para que cada pull request llegue con su regresión corrida. Hoy, como Software QA Engineer II en FLYR Labs.",
        "cta_experience": "Ver experiencia",
        "cta_case": "Leer un caso de estudio",
        "badge": "años en automatización",
        "exp_label": "Experiencia",
        "exp_title": "5+ años, 4 empresas",
        "exp_more": "Ver experiencia completa →",
        "current": "● Actual",
        "current_dates": "Feb 2023 — hoy",
        "current_text": "Framework Selenium + pytest con POM: regresión automatizada en el 75% de los flujos críticos de reserva y pricing, y ciclo reducido de 1h a 24 min.",
        "proj_label": "Proyectos públicos",
        "proj_title": "Código abierto para revisar cómo trabajo",
        "repo": "Repositorio en GitHub →",
        "read_case": "Leer caso de estudio →",
        "view_code": "Caso de estudio pronto · ver código",
        "no_projects": "Todavía no hay proyectos cargados.",
        "site_label": "Este sitio",
        "site_title": "Un portafolio que se prueba a sí mismo",
        "site_text": "Lo monté de punta a punta: servidor propio, Nginx, Flask y PostgreSQL en Docker, HTTPS real y un pipeline que lo despliega y verifica con un smoke test en cada push.",
        "demos_label": "Demos IA · Próximamente",
        "demos_title": "Generador de casos de prueba y analizador de bugs, en vivo.",
        "demos_text": "Con la API de Claude, en este mismo servidor.",
        "cta_title": "¿Tu equipo necesita más confianza en cada release?",
        "cta_text": "Manizales, Colombia · remoto · español nativo, inglés B2",
        "write": "Escríbeme",
        # experiencia
        "exp_h1_a": "5+ años entregando software, ",
        "exp_h1_b": "3.5+ automatizando",
        "exp_h1_c": " su calidad.",
        "exp_lead": "De implementar sistemas a diseñar los frameworks que los prueban. Equipos ágiles, distribuidos y remotos, hoy en travel tech.",
        "download_cv": "Descargar CV",
        "status_current": "● Actual",
        "status_previous": "Anterior",
        "edu_label": "Formación",
        "edu_1": "Tecnología en Análisis y Programación de Sistemas",
        "edu_1_status": "Finalizada · 2022",
        "edu_2": "Ingeniería de Sistemas",
        "edu_2_status": "En curso · 7.º semestre aprobado",
        "langs_label": "Idiomas",
        "lang_es": "Español",
        "lang_es_level": "Nativo",
        "lang_en": "Inglés",
        "lang_en_level": "B2 · competencia profesional",
        "back": "← Volver",
        "next": "Siguiente →",
        "prev": "← Anterior",
        "next_case_soon": "Siguiente caso · pronto →",
        "case_ui_short": "Caso de estudio: automatización UI",
        "case_api_short": "API Testing con pytest + requests",
        # caso de estudio UI
        "case_tag": "Caso de estudio · UI",
        "case_h1": "Automatización UI con Playwright y un Page Object Model estricto",
        "case_lead": "Suite de extremo a extremo sobre Restful Booker Platform, una app pública de práctica: reserva completa, panel de administración y datos parametrizados desde Excel.",
        "meta_role": "Rol",
        "meta_role_value": "Autor único",
        "meta_stack": "Stack",
        "meta_browsers": "Navegadores",
        "meta_code": "Código",
        "view_github": "Ver en GitHub →",
        "problem_label": "El problema",
        "problem": "Las suites UI suelen volverse frágiles: selectores repetidos por todos lados, datos de prueba metidos en el código y fallos imposibles de diagnosticar sin volver a correrlos.",
        "approach_label": "El enfoque",
        "approach": "Cada página es un objeto con sus acciones, los tests solo hablan el idioma del negocio, los datos viven fuera del código y cada fallo deja evidencia (captura + reporte Allure).",
        "decisions_title": "Decisiones clave",
        "run_title": "Cómo corre",
        "snippet_note": "Fragmento ilustrativo: reemplazar por un escenario real del repositorio.",
        "result_tests": "Tests en la suite",
        "result_browsers": "Navegadores por ejecución",
        "result_browsers_sub": "matrix en GitHub Actions",
        "result_time": "Tiempo de la suite en CI",
        "result_time_sub": "imagen Docker cacheada",
    },
    "en": {
        "html_title": "Andrés González — QA Automation Engineer",
        "meta_description": "QA Automation Engineer with 3.5+ years in test automation: Python, Selenium, Playwright, pytest and CI/CD.",
        "nav_overview": "Overview",
        "nav_experience": "Experience",
        "nav_projects": "Projects",
        "nav_site": "This site",
        "nav_demos": "AI demos",
        "soon": "soon",
        "available": "Available",
        "open_to": "Open to QA Automation / SDET roles",
        "remote": "Remote · GMT-5",
        "talk": "Let’s talk",
        "cv_file": "Resume_Andres_Gonzalez.pdf",
        "follow": "Follow me",
        "lang_label": "Language",
        "menu": "Menu",
        "footer": "Built, deployed and tested at andresqe.duckdns.org",
        "crumb_experience": "experience",
        "crumb_projects": "projects",
        "eyebrow": "Hi, I’m Andrés · QA Automation Engineer",
        "h1_a": "Quality you can ",
        "h1_b": "prove",
        "lead": "I build scalable test automation frameworks in Python, Selenium and Playwright, and wire them into CI/CD so every pull request ships with its regression already run. Currently a Software QA Engineer II at FLYR Labs.",
        "cta_experience": "View experience",
        "cta_case": "Read a case study",
        "badge": "years in test automation",
        "exp_label": "Experience",
        "exp_title": "5+ years, 4 companies",
        "exp_more": "See full experience →",
        "current": "● Current",
        "current_dates": "Feb 2023 — present",
        "current_text": "Selenium + pytest framework with POM: automated regression on 75% of critical booking and pricing flows, and the cycle cut from 1h to 24 min.",
        "proj_label": "Public projects",
        "proj_title": "Open source, so you can review how I work",
        "repo": "GitHub repository →",
        "read_case": "Read case study →",
        "view_code": "Case study soon · view code",
        "no_projects": "No projects loaded yet.",
        "site_label": "This site",
        "site_title": "A portfolio that tests itself",
        "site_text": "Built end to end: my own server, Nginx, Flask and PostgreSQL in Docker, real HTTPS, and a pipeline that deploys it and verifies it with a smoke test on every push.",
        "demos_label": "AI demos · Coming soon",
        "demos_title": "Live test case generator and bug analyzer.",
        "demos_text": "Powered by the Claude API, on this same server.",
        "cta_title": "Does your team need more confidence in every release?",
        "cta_text": "Manizales, Colombia · remote · native Spanish, B2 English",
        "write": "Email me",
        "exp_h1_a": "5+ years shipping software, ",
        "exp_h1_b": "3.5+ automating",
        "exp_h1_c": " its quality.",
        "exp_lead": "From implementing systems to designing the frameworks that test them. Agile, distributed, remote teams, now in travel tech.",
        "download_cv": "Download resume",
        "status_current": "● Current",
        "status_previous": "Previous",
        "edu_label": "Education",
        "edu_1": "Technology in Systems Analysis and Programming",
        "edu_1_status": "Completed · 2022",
        "edu_2": "Systems Engineering",
        "edu_2_status": "In progress · 7th semester completed",
        "langs_label": "Languages",
        "lang_es": "Spanish",
        "lang_es_level": "Native",
        "lang_en": "English",
        "lang_en_level": "B2 · professional working proficiency",
        "back": "← Back",
        "next": "Next →",
        "prev": "← Previous",
        "next_case_soon": "Next case · soon →",
        "case_ui_short": "Case study: UI automation",
        "case_api_short": "API testing with pytest + requests",
        "case_tag": "Case study · UI",
        "case_h1": "UI automation with Playwright and a strict Page Object Model",
        "case_lead": "End-to-end suite against Restful Booker Platform, a public practice app: full booking flow, admin panel and Excel-parametrized data.",
        "meta_role": "Role",
        "meta_role_value": "Sole author",
        "meta_stack": "Stack",
        "meta_browsers": "Browsers",
        "meta_code": "Code",
        "view_github": "View on GitHub →",
        "problem_label": "The problem",
        "problem": "UI suites tend to become brittle: selectors duplicated everywhere, test data hard-coded, and failures impossible to diagnose without re-running them.",
        "approach_label": "The approach",
        "approach": "Each page is an object with its own actions, tests speak only the business language, data lives outside the code, and every failure leaves evidence (screenshot + Allure report).",
        "decisions_title": "Key decisions",
        "run_title": "How it runs",
        "snippet_note": "Illustrative snippet: replace with a real scenario from the repository.",
        "result_tests": "Tests in the suite",
        "result_browsers": "Browsers per run",
        "result_browsers_sub": "GitHub Actions matrix",
        "result_time": "Suite time in CI",
        "result_time_sub": "cached Docker image",
    },
}

KPIS = {
    "es": [
        ("Experiencia", "5+ años", "3.5+ en automatización"),
        ("Ciclo de regresión", "1h → 24m", "−60% con pytest en paralelo"),
        ("Flujos críticos cubiertos", "75%", "+60% de regresión automatizada"),
        ("Defectos en producción", "−15%", "regresión en cada pull request"),
    ],
    "en": [
        ("Experience", "5+ years", "3.5+ in test automation"),
        ("Regression cycle", "1h → 24m", "−60% with parallel pytest"),
        ("Critical flows covered", "75%", "+60% automated regression"),
        ("Production defects", "−15%", "regression on every pull request"),
    ],
}

PAST_ROLES = {
    "es": [
        ("QA Analyst", "Netactica", "2022 — 2023"),
        ("QA Analyst", "Transfiriendo S.A.", "2022"),
        ("Líder de Desarrollo e Implementación", "Sigma Ingeniería", "2020 — 2021"),
    ],
    "en": [
        ("QA Analyst", "Netactica", "2022 — 2023"),
        ("QA Analyst", "Transfiriendo S.A.", "2022"),
        ("Development & Implementation Lead", "Sigma Ingeniería", "2020 — 2021"),
    ],
}

JOBS = {
    "es": [
        {
            "current": True, "dates": "Feb 2023 — hoy", "place": "Remoto · Travel / airline tech",
            "role": "Software QA Engineer II", "company": "FLYR Labs",
            "points": [
                "Diseñé un framework escalable de Selenium + pytest con Page Object Model que subió la cobertura de regresión automatizada un 60%, hasta el 75% de los flujos críticos de reserva y pricing.",
                "Reduje el ciclo de regresión un 60% (de 1h a 24 min) parametrizando y paralelizando las suites de pytest, acelerando la cadencia de releases.",
                "Bajé un 15% la fuga de defectos a producción integrando las suites a pipelines de GitHub Actions que corren la regresión en cada pull request.",
            ],
            "stack": ["Selenium", "pytest", "POM", "GitHub Actions", "Python"],
        },
        {
            "current": False, "dates": "Oct 2022 — Feb 2023", "place": "Remoto",
            "role": "QA Analyst", "company": "Netactica",
            "points": [
                "Ejecuté casos de prueba manuales y los primeros automatizados para aplicaciones web y API.",
                "Contribuí al diseño de casos de prueba y a los primeros esfuerzos de automatización del equipo.",
            ],
            "stack": ["Web", "API", "Diseño de casos"],
        },
        {
            "current": False, "dates": "Feb 2022 — Oct 2022", "place": "Remoto",
            "role": "QA Analyst", "company": "Transfiriendo S.A.",
            "points": [
                "Reduje un 37% el tiempo de ejecución automatizando casos recurrentes de UI y API con Stela.",
                "Bajé un 18% la fuga de defectos reforzando la validación y la trazabilidad en todo el STLC.",
                "Subí un 22% la cobertura de requerimientos con casos mapeados directamente a reglas de negocio.",
                "Gestioné el ciclo de vida completo de defectos en Azure DevOps, mejorando el tiempo de triage.",
            ],
            "stack": ["Stela", "Azure DevOps", "Regresión", "Integración"],
        },
        {
            "current": False, "dates": "Jun 2020 — Dic 2021", "place": "Colombia",
            "role": "Líder de Desarrollo e Implementación", "company": "Sigma Ingeniería S.A.",
            "points": [
                "Mejoré un 55% la eficiencia operativa construyendo herramientas internas y administrando bases PostgreSQL en producción.",
                "Reduje un 20% el tiempo de onboarding de clientes con soporte técnico, documentación y capacitación en 4 cuentas.",
                "Lideré un equipo de 3 personas en implementaciones de punta a punta.",
            ],
            "stack": ["PostgreSQL", "Herramientas internas", "Liderazgo"],
        },
    ],
    "en": [
        {
            "current": True, "dates": "Feb 2023 — present", "place": "Remote · Travel / airline tech",
            "role": "Software QA Engineer II", "company": "FLYR Labs",
            "points": [
                "Architected a scalable Selenium + pytest framework with the Page Object Model, increasing automated regression coverage by 60% to reach 75% of critical booking and pricing flows.",
                "Cut regression cycle time by 60% (from 1h to 24 min) by parametrizing and parallelizing pytest suites, accelerating release cadence.",
                "Reduced production defect leakage by 15% by integrating the suites into GitHub Actions pipelines that trigger regression on every pull request.",
            ],
            "stack": ["Selenium", "pytest", "POM", "GitHub Actions", "Python"],
        },
        {
            "current": False, "dates": "Oct 2022 — Feb 2023", "place": "Remote",
            "role": "QA Analyst", "company": "Netactica",
            "points": [
                "Executed manual and early automated test cases for web and API applications.",
                "Contributed to test case design and the team’s first automation efforts.",
            ],
            "stack": ["Web", "API", "Test design"],
        },
        {
            "current": False, "dates": "Feb 2022 — Oct 2022", "place": "Remote",
            "role": "QA Analyst", "company": "Transfiriendo S.A.",
            "points": [
                "Reduced test execution time by 37% by automating recurring UI and API test cases with Stela.",
                "Reduced defect leakage by 18% by strengthening validation and traceability across the STLC.",
                "Increased requirement coverage by 22% with test cases mapped directly to business requirements.",
                "Managed the full defect life cycle in Azure DevOps, improving triage turnaround.",
            ],
            "stack": ["Stela", "Azure DevOps", "Regression", "Integration"],
        },
        {
            "current": False, "dates": "Jun 2020 — Dec 2021", "place": "Colombia",
            "role": "Development & Implementation Lead", "company": "Sigma Ingeniería S.A.",
            "points": [
                "Improved operational efficiency by 55% by building internal tools and managing PostgreSQL databases for production systems.",
                "Reduced client onboarding time by 20% through technical support, documentation and training across 4 client accounts.",
                "Led a 3-person team on end-to-end implementations.",
            ],
            "stack": ["PostgreSQL", "Internal tools", "Leadership"],
        },
    ],
}

CASE_UI = {
    "es": {
        "decisions": [
            ("01", "Page Object Model estricto", "Los selectores viven en un solo lugar: si la UI cambia, se toca un archivo, no veinte tests."),
            ("02", "Datos fuera del código", "La batería de datos se parametriza desde Excel, así negocio puede sumar casos sin tocar Python."),
            ("03", "BDD sobre los mismos objetos", "Los escenarios Gherkin reutilizan los Page Objects: una sola fuente de verdad para dos audiencias."),
        ],
        "steps": ["git push", "imagen Docker", "Chromium · Firefox · WebKit", "reporte Allure", "badge ✓"],
        "snippet": (
            "Scenario: Un huésped reserva una habitación disponible\n"
            "  Given estoy en la página principal del hotel\n"
            "  When elijo una habitación y fechas libres\n"
            "  And completo mis datos de contacto\n"
            "  Then veo la confirmación de la reserva"
        ),
    },
    "en": {
        "decisions": [
            ("01", "Strict Page Object Model", "Selectors live in one place: when the UI changes, you edit one file, not twenty tests."),
            ("02", "Data outside the code", "Test data is parametrized from Excel, so business can add cases without touching Python."),
            ("03", "BDD on the same objects", "Gherkin scenarios reuse the Page Objects: one source of truth for two audiences."),
        ],
        "steps": ["git push", "Docker image", "Chromium · Firefox · WebKit", "Allure report", "badge ✓"],
        "snippet": (
            "Scenario: A guest books an available room\n"
            "  Given I am on the hotel home page\n"
            "  When I pick a room and free dates\n"
            "  And I fill in my contact details\n"
            "  Then I see the booking confirmation"
        ),
    },
}

# Traducción al inglés de los proyectos ya cargados en la base (por título).
# La base guarda un solo idioma; un proyecto nuevo que no esté acá se muestra
# en inglés con el texto original hasta que se agregue su traducción.
PROJECT_EN = {
    "UI Testing — Playwright + Page Object Model": (
        "UI Testing — Playwright + Page Object Model",
        "Playwright + pytest suite against Restful Booker Platform (a public practice app): full booking flow, admin panel, Excel-parametrized data and BDD with pytest-bdd. Strict Page Object Model, automatic failure screenshots and Allure reports.",
    ),
    "API Testing — pytest + requests": (
        "API Testing — pytest + requests",
        "pytest + requests suite against Restful-booker (a public practice API): full CRUD with pydantic schema validation, token auth, and negative cases documenting real API inconsistencies (status codes that don’t follow REST).",
    ),
    "CI/CD — GitHub Actions": (
        "CI/CD — GitHub Actions",
        "CI pipeline with two parallel jobs (API and UI on a cross-browser Chromium/Firefox/WebKit matrix), running inside the same Docker image used locally, with layer caching and a status badge in the README.",
    ),
    "Docker + BDD": (
        "Docker + BDD",
        "A single Docker image reused locally and in CI (Python/Playwright never installed natively on the runner). Business scenarios in Gherkin (pytest-bdd) reusing the same Page Objects as the plain suite, readable by non-technical people.",
    ),
}
