"""Casos de estudio de API, CI/CD y BDD (QAP-9). El de UI vive en content.CASE_UI y su plantilla propia.

Todo lo que se afirma aquí sale de `qa-automation-portfolio` y se comprobó el 2026-10-10 (ver CHECKED): los fragmentos de
código son COPIA LITERAL de archivos de ese repo (app/tests/test_case_studies.py lo verifica cuando el repo hermano está en
la misma carpeta) y las cifras se midieron, no se estimaron. Si el repo de tests cambia, hay que volver a medir.

Estructura de cada caso (misma para los tres): problema, enfoque, decisiones, cómo corre, resultado (KPIs) y límites.
"""

CHECKED = "2026-10-10"

REPO = "https://github.com/anfelgonta201514/qa-portfolio-server"
TESTS_REPO = "https://github.com/anfelgonta201514/qa-automation-portfolio"

# ---- fragmentos literales (archivo de origen en el comentario)

# api-tests/restful-booker/tests/test_negative_cases.py (primer test)
API_SNIPPET = '''def test_create_booking_missing_required_field_returns_500(api_client):
    incomplete_payload = {
        "lastname": "Gonzalez",
        "totalprice": 150,
        "depositpaid": True,
        "bookingdates": {"checkin": "2026-08-01", "checkout": "2026-08-05"},
    }
    response = api_client.create_booking(incomplete_payload)
    attach_response(response, "Respuesta de POST /booking sin firstname")
    assert response.status_code == 500  # comportamiento real, aunque incorrecto'''

# .github/workflows/tests.yml (cabecera del job de UI)
CI_SNIPPET = '''  ui-tests:
    name: UI tests (${{ matrix.browser }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        browser: [chromium, firefox, webkit]'''

# ui-tests/booking-flow/features/admin_room.feature
BDD_SNIPPET = '''Feature: Gestión de habitaciones por el administrador
  Como administrador del hotel
  Quiero crear nuevas habitaciones
  Para mantener actualizado el inventario disponible

  Scenario: Crear una habitación con servicios
    Given que inicio sesión como administrador
    When que creo una habitación nueva con tipo, precio y servicios
    Then que la habitación aparece en el listado de habitaciones correctamente'''

# Fuente de cada fragmento (ruta dentro de qa-automation-portfolio): la usa la prueba de coincidencia.
SNIPPET_SOURCES = {
    "api": ("api-tests/restful-booker/tests/test_negative_cases.py", API_SNIPPET),
    "ci": (".github/workflows/tests.yml", CI_SNIPPET),
    "bdd": ("ui-tests/booking-flow/features/admin_room.feature", BDD_SNIPPET),
}

# Orden del recorrido entre casos de estudio (anterior/siguiente).
ORDER = ("case_ui", "case_api", "case_ci", "case_bdd")

# Etiqueta del CI que corresponde a cada caso (ver public.PROJECT_TAGS).
CI_TAG = {"case_api": "API", "case_ci": "CI/CD", "case_bdd": "BDD"}

CASES = {
    "es": {
        "case_api": {
            "short": "API Testing con pytest + requests",
            "slug": "api-pytest",
            "tag": "Caso de estudio · API",
            "h1": "Pruebas de API con pytest + requests: verificar lo que la API hace de verdad, no lo que REST dice",
            "lead": "10 tests contra Restful-booker, una API pública de práctica: autenticación, CRUD, validación de esquema y casos negativos. Varias de sus respuestas no siguen REST, y los tests las fijan tal cual son.",
            "meta": [
                ("Rol", "Autor único", None),
                ("Stack", "pytest · requests · pydantic · Allure", None),
                ("API bajo prueba", "restful-booker.herokuapp.com", "https://restful-booker.herokuapp.com/apidoc"),
                ("Código", "Ver en GitHub →", TESTS_REPO + "/tree/master/api-tests/restful-booker"),
            ],
            "problem": "Una suite de API escrita \"de memoria\" según cómo deberían responder los servicios REST falla por las razones equivocadas: espera 200, 201, 204, 401 o 400 que la API no devuelve, y se acaba retocando el test hasta que pasa sin saber qué hace realmente el servidor.",
            "approach": "Cada endpoint se probó primero a mano (curl o Postman) y lo observado se convirtió en la aserción. Un cliente HTTP hace de \"Page Object\" de la API, cada test crea y borra sus propios datos, la forma de las respuestas se valida con pydantic y la respuesta se adjunta al reporte solo en el punto de validación.",
            "table_title": "Lo que la API responde de verdad",
            "table_head": ("Endpoint", "Lo que esperaría REST", "Lo que responde"),
            "table": [
                ("GET /ping", "200", "201"),
                ("POST /booking", "201", "200 (y crea el recurso)"),
                ("DELETE /booking/{id}", "204", "201"),
                ("POST /auth con credenciales inválidas", "401", "200 con {\"reason\": \"Bad credentials\"}: hay que mirar el cuerpo, no solo el código"),
                ("PUT / DELETE sin token", "401", "403; el token va en la cookie token=…, no en Authorization"),
                ("POST /booking sin un campo requerido", "400", "500: un defecto real de la API"),
            ],
            "decisions": [
                ("01", "Verificar antes de asertar", "Nada se asume por convención. Seis comportamientos que no siguen REST quedaron documentados y fijados en tests, no \"corregidos\" en la suite."),
                ("02", "Un método por endpoint", "BookingClient encapsula las llamadas HTTP: el test nunca arma URLs ni cabeceras a mano, igual que un Page Object en UI."),
                ("03", "Cada test es dueño de sus datos", "La fixture crea la reserva y la borra al terminar; la API es pública y compartida, y los datos de otro test no pueden afectar al mío."),
            ],
            "steps": ["curl / Postman", "BookingClient", "pytest + pydantic", "adjunto en Allure", "job de API en CI"],
            "snippet": API_SNIPPET,
            "snippet_note": "Test real de api-tests/restful-booker/tests/test_negative_cases.py.",
            "snippet_href": TESTS_REPO + "/blob/master/api-tests/restful-booker/tests/test_negative_cases.py",
            "kpis": [
                ("Tests de API", "10", "2 de autenticación · 5 de CRUD · 3 negativos"),
                ("Comportamientos fuera de REST", "6", "documentados y fijados en tests"),
                ("Duración de la suite", "~3 s", f"medida el {CHECKED}: 3,16 s en local"),
            ],
            "limits_title": "Límites",
            "limits": [
                "La API es pública y compartida: sus datos se reinician y puede estar lenta o caída. Por eso cada test crea los suyos, y aun así la suite necesita red (también el job de API en CI).",
                "Los tests fijan defectos de la API (por ejemplo el 500). Si algún día la corrigen, esos tests fallarán: es intencional, avisan del cambio.",
                "Cubre los endpoints que usa el portafolio; no hay pruebas de carga ni de seguridad.",
            ],
        },
        "case_ci": {
            "short": "CI/CD con GitHub Actions",
            "slug": "ci-cd",
            "tag": "Caso de estudio · CI/CD",
            "h1": "CI/CD con GitHub Actions: la misma imagen de Docker en mi máquina y en el pipeline",
            "lead": "Un workflow con 4 jobs en paralelo (API y UI en Chromium, Firefox y WebKit) que corre dentro de la imagen oficial de Playwright, con caché de capas, reportes como artefactos y un criterio explícito para lo que no depende de mí.",
            "meta": [
                ("Rol", "Autor único", None),
                ("Stack", "GitHub Actions · Docker · Allure", None),
                ("Disparadores", "push y pull request a master, y a mano", None),
                ("Código", "Ver tests.yml →", TESTS_REPO + "/blob/master/.github/workflows/tests.yml"),
            ],
            "problem": "El clásico \"en mi máquina pasa\": instalar Python y los navegadores a mano en el runner da un entorno distinto al local, con versiones que se desalinean y fallos que nadie puede reproducir.",
            "approach": "Una sola imagen (la oficial de Playwright para Python, con la versión fijada) se construye una vez y se usa igual en local y en CI: el pipeline solo construye y ejecuta docker run. Los reportes de Allure y, si algo falla, las trazas de Playwright se suben como artefactos.",
            "decisions": [
                ("01", "Una imagen, dos usos", "Playwright y la imagen base cambian siempre juntos y a la misma versión exacta: si no, el navegador de la imagen deja de ser compatible con la librería y no arranca."),
                ("02", "Matrix de 3 navegadores sin fail-fast", "Un navegador roto no oculta el resultado de los otros dos: cada ejecución termina y se puede comparar."),
                ("03", "Lo externo no bloquea, pero no se esconde", "El flujo de reserva dependía de un sitio de práctica que falló repetidas veces solo desde los runners de GitHub, así que va con continue-on-error: queda en el log y en los artefactos, pero no ensucia el badge."),
            ],
            "steps": ["git push / PR", "docker build (caché de capas)", "API · UI × 3 navegadores", "Allure + trazas como artefactos", "badge de este sitio"],
            "snippet": CI_SNIPPET,
            "snippet_note": "Cabecera real del job de UI en .github/workflows/tests.yml.",
            "snippet_href": TESTS_REPO + "/blob/master/.github/workflows/tests.yml",
            "kpis": [
                ("Jobs por ejecución", "4", "1 de API + 3 de UI, en paralelo"),
                ("Navegadores", "3", "Chromium · Firefox · WebKit"),
                ("Duración de una ejecución", "6-11 min", f"últimas 8 ejecuciones leídas de GitHub el {CHECKED}"),
            ],
            "struggles_title": "Lo que falló en el camino",
            "struggles": [
                ("Versión de Playwright vs. imagen", "El requirements.txt aceptaba cualquier versión reciente y la imagen estaba fijada a una anterior: Playwright se negaba a lanzar el navegador. Se fijó la versión exacta, y el tag de la imagen cambia a la vez."),
                ("Dos plugins de Allure que no conviven", "allure-pytest y allure-pytest-bdd registran la misma opción y pytest revienta al cargarlos juntos (es una incompatibilidad conocida del ecosistema, no un error propio). Se desactivan los dos por defecto y se activa uno a la vez."),
                ("El flujo de reserva solo falla en CI", "El mismo test pasa en local y fallaba desde los runners de GitHub; la hipótesis más probable es que el sitio de práctica limita IPs de centros de datos (sin confirmar). En ejecuciones recientes pasó."),
            ],
            "history": f"Historial real (leído de la API de GitHub el {CHECKED}): de los 13 pushes a master que muestra la lista, 6 fallaron durante el desarrollo y los 5 más recientes pasaron.",
            "extra_title": "El mismo patrón en este sitio",
            "extra": "El sitio que estás leyendo tiene su propio pipeline: las pruebas (incluida una pasada contra PostgreSQL real) corren antes de cada despliegue y, si fallan, no se publica nada; tras desplegar, un smoke test y una comprobación de cabeceras de seguridad miran la respuesta real. En un pull request solo se prueba, nunca se despliega. Se comprobó con un PR de prueba con un test roto a propósito: Tests en rojo y Deploy omitido.",
            "extra_href": REPO + "/blob/main/.github/workflows/deploy.yml",
            "extra_link": "Ver deploy.yml →",
            "limits_title": "Límites",
            "limits": [
                "Este repositorio es CI: no despliega nada. El despliegue continuo real vive en el repositorio del sitio (bloque de arriba).",
                "El pipeline depende de un sitio de práctica externo; el flujo de reserva sigue siendo la parte frágil.",
                "Las duraciones salen de las marcas de tiempo de GitHub e incluyen la espera en cola: son aproximadas.",
            ],
        },
        "case_bdd": {
            "short": "BDD con pytest-bdd",
            "slug": "bdd",
            "tag": "Caso de estudio · BDD",
            "h1": "BDD con pytest-bdd: escenarios legibles que reutilizan los mismos Page Objects",
            "lead": "Dos escenarios en Gherkin (la reserva de un visitante y el alta de una habitación por el administrador) cuyos pasos llaman a las mismas clases que los tests normales: una sola fuente de verdad para dos audiencias.",
            "meta": [
                ("Rol", "Autor único", None),
                ("Stack", "pytest-bdd · Playwright · allure-pytest-bdd", None),
                ("Escenarios", "2, escritos en español", None),
                ("Código", "Ver en GitHub →", TESTS_REPO + "/tree/master/ui-tests/booking-flow/tests/bdd"),
            ],
            "problem": "El BDD mal hecho acaba siendo un segundo framework: pasos duplicados, selectores repetidos y escenarios que nadie lee. Es doble mantenimiento sin el beneficio de que negocio entienda las pruebas.",
            "approach": "Los archivos .feature describen el comportamiento en lenguaje de negocio y los step definitions son capas finas que llaman a los Page Objects que ya existen. pytest-bdd genera un test por escenario, así que corren con el mismo pytest, las mismas fixtures y el mismo CI.",
            "decisions": [
                ("01", "Los .feature viven junto a los tests", "Están dentro de ui-tests/booking-flow y no en la raíz del repo: así los pasos importan los Page Objects sin manipular sys.path."),
                ("02", "Los pasos validan de verdad", "Tras el login se espera lo nuevo (el botón de salir) y que desaparezcan lo viejo (el formulario) y el indicador de carga antes de capturar la evidencia: en una SPA, confiar solo en que algo apareció da capturas a medias."),
                ("03", "Capturas solo donde se valida", "La evidencia se adjunta en los pasos Then y en las aserciones, no en cada acción: el reporte muestra lo confirmado, no un flipbook."),
            ],
            "steps": ["Gherkin (.feature)", "step definitions", "Page Objects", "Playwright", "Allure con Given/When/Then"],
            "snippet": BDD_SNIPPET,
            "snippet_note": "Feature real de ui-tests/booking-flow/features/admin_room.feature (en español).",
            "snippet_href": TESTS_REPO + "/blob/master/ui-tests/booking-flow/features/admin_room.feature",
            "kpis": [
                ("Escenarios BDD", "2", "de los 15 casos de la suite de UI"),
                ("Navegadores", "3", "ambos corren en la matrix de CI"),
                ("Bloquean el build", "1 de 2", "el de administración sí; el de reserva no"),
            ],
            "struggles_title": "Lo que costó",
            "struggles": [
                ("El reporte con Given/When/Then", "allure-pytest-bdd da el desglose por paso, pero no puede estar activo a la vez que allure-pytest, y por sí solo no sirve para los tests que no son BDD. Por eso se ejecutan con comandos distintos y carpetas de resultados separadas."),
            ],
            "limits_title": "Límites",
            "limits": [
                "Hay un solo escenario por feature: cubre el flujo principal, no los casos negativos (esos viven en tests normales, por ejemplo el teléfono inválido o el login incorrecto).",
                "El escenario de reserva comparte la fragilidad del flujo de reserva con el sitio de práctica y por eso no bloquea el build en CI.",
            ],
        },
    },
    "en": {
        "case_api": {
            "short": "API testing with pytest + requests",
            "slug": "api-pytest",
            "tag": "Case study · API",
            "h1": "API testing with pytest + requests: verify what the API really does, not what REST says",
            "lead": "10 tests against Restful-booker, a public practice API: authentication, CRUD, schema validation and negative cases. Several of its responses do not follow REST, and the tests pin them exactly as they are.",
            "meta": [
                ("Role", "Sole author", None),
                ("Stack", "pytest · requests · pydantic · Allure", None),
                ("API under test", "restful-booker.herokuapp.com", "https://restful-booker.herokuapp.com/apidoc"),
                ("Code", "View on GitHub →", TESTS_REPO + "/tree/master/api-tests/restful-booker"),
            ],
            "problem": "An API suite written \"from memory\" about how REST services should respond fails for the wrong reasons: it expects 200, 201, 204, 401 or 400 that the API never returns, and the test gets tweaked until it passes without anyone knowing what the server actually does.",
            "approach": "Every endpoint was first tried by hand (curl or Postman) and what was observed became the assertion. An HTTP client plays the role of a \"Page Object\" for the API, each test creates and deletes its own data, response shape is validated with pydantic, and the response is attached to the report only at the validation point.",
            "table_title": "What the API really answers",
            "table_head": ("Endpoint", "What REST would expect", "What it returns"),
            "table": [
                ("GET /ping", "200", "201"),
                ("POST /booking", "201", "200 (and it creates the resource)"),
                ("DELETE /booking/{id}", "204", "201"),
                ("POST /auth with invalid credentials", "401", "200 with {\"reason\": \"Bad credentials\"}: you must read the body, not just the status"),
                ("PUT / DELETE without a token", "401", "403; the token goes in the token=… cookie, not in Authorization"),
                ("POST /booking missing a required field", "400", "500: a real defect in the API"),
            ],
            "decisions": [
                ("01", "Verify before asserting", "Nothing is assumed by convention. Six behaviors that do not follow REST were documented and pinned in tests, not \"fixed\" in the suite."),
                ("02", "One method per endpoint", "BookingClient wraps the HTTP calls: a test never builds URLs or headers by hand, just like a Page Object in UI."),
                ("03", "Every test owns its data", "The fixture creates the booking and deletes it at the end; the API is public and shared, and another test's data cannot affect mine."),
            ],
            "steps": ["curl / Postman", "BookingClient", "pytest + pydantic", "Allure attachment", "API job in CI"],
            "snippet": API_SNIPPET,
            "snippet_note": "Real test from api-tests/restful-booker/tests/test_negative_cases.py (comments in Spanish).",
            "snippet_href": TESTS_REPO + "/blob/master/api-tests/restful-booker/tests/test_negative_cases.py",
            "kpis": [
                ("API tests", "10", "2 authentication · 5 CRUD · 3 negative"),
                ("Non-REST behaviors", "6", "documented and pinned in tests"),
                ("Suite duration", "~3 s", f"measured on {CHECKED}: 3.16 s locally"),
            ],
            "limits_title": "Limits",
            "limits": [
                "The API is public and shared: its data resets and it can be slow or down. That is why every test creates its own, and the suite still needs network access (the CI API job too).",
                "The tests pin the API's defects (for example the 500). If they ever fix it, those tests will fail: that is intentional, they flag the change.",
                "It covers the endpoints this portfolio uses; there is no load or security testing.",
            ],
        },
        "case_ci": {
            "short": "CI/CD with GitHub Actions",
            "slug": "ci-cd",
            "tag": "Case study · CI/CD",
            "h1": "CI/CD with GitHub Actions: the same Docker image on my machine and in the pipeline",
            "lead": "A workflow with 4 parallel jobs (API, and UI on Chromium, Firefox and WebKit) that runs inside the official Playwright image, with layer caching, reports as artifacts and an explicit rule for what is out of my hands.",
            "meta": [
                ("Role", "Sole author", None),
                ("Stack", "GitHub Actions · Docker · Allure", None),
                ("Triggers", "push and pull request to master, and manual", None),
                ("Code", "View tests.yml →", TESTS_REPO + "/blob/master/.github/workflows/tests.yml"),
            ],
            "problem": "The classic \"it works on my machine\": installing Python and the browsers by hand on the runner gives an environment different from the local one, with versions drifting apart and failures nobody can reproduce.",
            "approach": "A single image (the official Playwright one for Python, with its version pinned) is built once and used the same way locally and in CI: the pipeline only builds and runs docker run. Allure reports and, when something fails, Playwright traces are uploaded as artifacts.",
            "decisions": [
                ("01", "One image, two uses", "Playwright and the base image always change together and to the same exact version: otherwise the image's browser stops being compatible with the library and will not start."),
                ("02", "A 3-browser matrix without fail-fast", "A broken browser does not hide the result of the other two: every run finishes and can be compared."),
                ("03", "External issues do not block, but are not hidden", "The booking flow depended on a practice site that failed repeatedly only from GitHub runners, so it runs with continue-on-error: it stays in the log and in the artifacts, but does not dirty the badge."),
            ],
            "steps": ["git push / PR", "docker build (layer cache)", "API · UI × 3 browsers", "Allure + traces as artifacts", "this site's badge"],
            "snippet": CI_SNIPPET,
            "snippet_note": "Real header of the UI job in .github/workflows/tests.yml.",
            "snippet_href": TESTS_REPO + "/blob/master/.github/workflows/tests.yml",
            "kpis": [
                ("Jobs per run", "4", "1 API + 3 UI, in parallel"),
                ("Browsers", "3", "Chromium · Firefox · WebKit"),
                ("Run duration", "6-11 min", f"last 8 runs read from GitHub on {CHECKED}"),
            ],
            "struggles_title": "What went wrong along the way",
            "struggles": [
                ("Playwright version vs. image", "requirements.txt accepted any recent version while the image was pinned to an older one: Playwright refused to launch the browser. The exact version was pinned, and the image tag changes with it."),
                ("Two Allure plugins that cannot coexist", "allure-pytest and allure-pytest-bdd register the same option and pytest blows up when both load (a known ecosystem incompatibility, not a mistake of mine). Both are disabled by default and one is enabled at a time."),
                ("The booking flow only fails in CI", "The same test passes locally and was failing from GitHub runners; the most likely cause is the practice site throttling datacenter IPs (unconfirmed). In recent runs it passed."),
            ],
            "history": f"Real history (read from the GitHub API on {CHECKED}): of the 13 pushes to master in the list, 6 failed during development and the 5 most recent passed.",
            "extra_title": "The same pattern on this site",
            "extra": "The site you are reading has its own pipeline: tests (including a pass against a real PostgreSQL) run before every deploy and, if they fail, nothing is published; after deploying, a smoke test and a security-header check look at the real response. On a pull request it only tests, it never deploys. This was checked with a test PR containing a deliberately broken test: Tests red and Deploy skipped.",
            "extra_href": REPO + "/blob/main/.github/workflows/deploy.yml",
            "extra_link": "View deploy.yml →",
            "limits_title": "Limits",
            "limits": [
                "This repository is CI: it deploys nothing. The real continuous deployment lives in the site's repository (block above).",
                "The pipeline depends on an external practice site; the booking flow is still the fragile part.",
                "Durations come from GitHub timestamps and include queue time: they are approximate.",
            ],
        },
        "case_bdd": {
            "short": "BDD with pytest-bdd",
            "slug": "bdd",
            "tag": "Case study · BDD",
            "h1": "BDD with pytest-bdd: readable scenarios that reuse the same Page Objects",
            "lead": "Two Gherkin scenarios (a visitor booking, and an admin adding a room) whose steps call the same classes as the plain tests: one source of truth for two audiences.",
            "meta": [
                ("Role", "Sole author", None),
                ("Stack", "pytest-bdd · Playwright · allure-pytest-bdd", None),
                ("Scenarios", "2, written in Spanish", None),
                ("Code", "View on GitHub →", TESTS_REPO + "/tree/master/ui-tests/booking-flow/tests/bdd"),
            ],
            "problem": "Badly done BDD ends up as a second framework: duplicated steps, repeated selectors and scenarios nobody reads. It is double maintenance without the payoff of business people understanding the tests.",
            "approach": ".feature files describe behavior in business language and the step definitions are thin layers calling the Page Objects that already exist. pytest-bdd generates one test per scenario, so they run with the same pytest, the same fixtures and the same CI.",
            "decisions": [
                ("01", "The .feature files live next to the tests", "They are inside ui-tests/booking-flow and not at the repo root: that way the steps import the Page Objects without tampering with sys.path."),
                ("02", "Steps really validate", "After login the test waits for the new thing (the logout button) and for the old thing (the form) and the loading indicator to go away before capturing evidence: in a SPA, trusting that something appeared gives half-loaded screenshots."),
                ("03", "Screenshots only where it validates", "Evidence is attached in Then steps and assertions, not on every action: the report shows what was confirmed, not a flipbook."),
            ],
            "steps": ["Gherkin (.feature)", "step definitions", "Page Objects", "Playwright", "Allure with Given/When/Then"],
            "snippet": BDD_SNIPPET,
            "snippet_note": "Real feature from ui-tests/booking-flow/features/admin_room.feature (in Spanish).",
            "snippet_href": TESTS_REPO + "/blob/master/ui-tests/booking-flow/features/admin_room.feature",
            "kpis": [
                ("BDD scenarios", "2", "out of the 15 cases in the UI suite"),
                ("Browsers", "3", "both run in the CI matrix"),
                ("Block the build", "1 of 2", "the admin one does; the booking one does not"),
            ],
            "struggles_title": "What was hard",
            "struggles": [
                ("The report with Given/When/Then", "allure-pytest-bdd gives the per-step breakdown, but it cannot be active together with allure-pytest, and on its own it does not work for non-BDD tests. That is why they run with separate commands and separate result folders."),
            ],
            "limits_title": "Limits",
            "limits": [
                "There is one scenario per feature: it covers the main flow, not negative cases (those live in plain tests, for example the invalid phone or the wrong login).",
                "The booking scenario shares the booking flow's fragility with the practice site, which is why it does not block the build in CI.",
            ],
        },
    },
}
