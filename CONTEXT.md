# CONTEXT.md — qa-portfolio-server

> Documento de continuidad para retomar este proyecto en cualquier sesión nueva sin perder contexto. Creado el 2026-09-18. Las reglas y convenciones estables viven en [`CLAUDE.md`](CLAUDE.md).

---

## 1. OBJETIVO

Servidor + portafolio web personal de Andres, semanas 8-14 del plan de estudio. Ver `CLAUDE.md` para la descripción completa y la decisión de arquitectura (todo dockerizado).

---

## 2. ESTADO ACTUAL

### ✅ Hecho
- Servidor Oracle Cloud verificado y accesible por SSH (`ubuntu@<IP>`, ver `SERVER_INFO.local.md`).
- Estado del servidor relevado (solo lectura, sin cambios aplicados todavía):
  - Ubuntu 20.04.6 LTS, ARM/aarch64, kernel `5.15.0-1081-oracle`.
  - Docker 26.1.3 instalado, sin contenedores corriendo.
  - 191GB libres de 194G.
  - Firewall (Oracle Security List + iptables local): solo `22/tcp` y `8211/udp` (Palworld, sin uso) permitidos en ambas capas.
- Decisión de arquitectura tomada con Andres: todo dockerizado (Nginx + Gunicorn/Flask + Postgres como contenedores, systemd solo para levantar el compose al boot).
- Proyecto local creado (`C:\Users\andre\Documents\qa-portfolio-server`), git inicializado, `.gitignore` con `SERVER_INFO.local.md` excluido desde el commit inicial.

- **iptables local del servidor actualizado (2026-09-18):** se insertó una regla `ACCEPT` para `tcp/80,443` (nuevas conexiones) antes del `REJECT` catch-all del chain `INPUT` (quedó en la línea 6, empujando el `REJECT` a la línea 7). Persistida con `netfilter-persistent save` — confirmado que sobrevive a un `iptables-save` (queda en `/etc/iptables/rules.v4`, sobrevive reinicio del server).
- **Security List de Oracle Cloud actualizada (2026-09-29):** Andres agregó las dos reglas de ingress (`0.0.0.0/0` → TCP → 80 y 443) desde la consola web. Verificado desde afuera con `curl` a ambos puertos: **"Connection refused"** en los dos — confirma que las DOS capas de firewall (Security List + iptables local) ya dejan pasar el tráfico; el "refused" (no timeout) es esperado porque todavía no hay ningún servicio escuchando en esos puertos.

- **Docker Compose confirmado (2026-09-29):** el plugin ya venía con la instalación de Docker (`docker compose version` → v5.1.2), no hizo falta instalar nada extra para el usuario `ubuntu`.
- **Hello world dockerizado, funcionando end-to-end (2026-09-29):** `docker-compose.yml` con 2 servicios — `app` (Flask mínimo + Gunicorn, `app/Dockerfile`) y `nginx` (imagen oficial `nginx:1.27-alpine`, reverse proxy vía `nginx/nginx.conf`, publica `80:80`). Copiado al servidor (`/home/ubuntu/qa-portfolio-server/`, no vía git todavía — ver pendientes) y levantado con `docker compose up -d --build`. Verificado con `curl` externo a `http://<IP>/`: `200 OK`, JSON de Flask, headers de Nginx — la cadena completa (Security List → iptables → Nginx → Gunicorn → Flask) funciona de punta a punta.
- **systemd unit creado y funcionando (2026-09-29):** `deploy/qa-portfolio.service` (`Type=oneshot`, `RemainAfterExit=yes`, `ExecStart=/usr/bin/docker compose up -d` en `/home/ubuntu/qa-portfolio-server`), instalado en `/etc/systemd/system/`, `enabled` y `active (exited)`. **Nota importante:** el plugin `docker compose` estaba instalado solo para el usuario `ubuntu` (`~/.docker/cli-plugins/docker-compose`), así que root (con quien corre systemd) no lo encontraba — `sudo docker compose` fallaba con "'compose' is not a docker command". Se resolvió copiando el binario a `/usr/local/lib/docker/cli-plugins/docker-compose` (instalación a nivel de sistema, visible para cualquier usuario). **No se probó con un reinicio real del servidor** — `systemctl is-enabled` confirma que arrancaría al boot, pero un reboot de verdad queda pendiente si Andres quiere validarlo con evidencia 100% real.

- **Regla de Palworld eliminada (2026-09-29):** borrada de las dos capas — iptables local (`sudo iptables -D INPUT 1`, repersistida con `netfilter-persistent save`) y Security List de Oracle Cloud (Andres la borró manualmente desde la consola). El `INPUT` chain hoy solo tiene: loopback/ESTABLISHED/ICMP, `22/tcp`, `80,443/tcp` y el `REJECT` catch-all.
- **Repo público creado y deploy vía git armado (2026-09-29):** `github.com/anfelgonta201514/qa-portfolio-server` (público — ver `CLAUDE.md` regla 1 sobre por qué es seguro: nunca lleva secretos, solo código+config). Primer commit pusheado (sin trailer `Co-Authored-By`, mismo criterio que `qa-automation-portfolio`). En el servidor: se guardó la copia manual (`mv` a `.manual-backup`), se clonó el repo real en su lugar (mismo path `/home/ubuntu/qa-portfolio-server`, así el `systemd` unit no necesitó cambios), se reconstruyó con `docker compose up -d --build` y se verificó con `curl` externo que sigue respondiendo igual. Backup manual eliminado una vez confirmado. Deploy de ahora en más: `git pull && docker compose up -d --build` en el servidor (documentado en `README.md`).

- **PostgreSQL + Flask-SQLAlchemy + API REST funcionando end-to-end (2026-09-29):** modelo `Project` (`app/models.py`), API de solo lectura (`GET /api/projects`, `GET /api/projects/<id>`) — sin endpoints de escritura a propósito (sin auth todavía, server público, se agregan en semana 10 junto con el panel admin). Servicio `postgres` (imagen `postgres:16-alpine`, volumen `postgres_data` para persistencia) agregado a `docker-compose.yml`. Secretos manejados vía `.env` gitignorado en el servidor (`.env.example` commiteado como plantilla, contraseña real generada con `openssl rand -hex 24` — **no usar `-base64`**, puede generar `/`, `+`, `=` que rompen el parseo de la URL de conexión). Seed idempotente (`app/seed.py`) insertó un ejemplo real (`qa-automation-portfolio`). Verificado con `curl` externo: `GET /api/projects` devuelve el JSON completo desde la base real.
- **Dos bugs de infraestructura encontrados y resueltos durante el deploy (2026-09-29)**, ambos documentados en detalle en `README.md` (sección troubleshooting):
  1. **Nginx cachea la IP del upstream.** `proxy_pass http://app:8000` (URL literal) resuelve el hostname una sola vez al arrancar Nginx; si `app` se recrea (nueva IP interna de Docker), Nginx sigue apuntando a la IP vieja → `502 Bad Gateway`. Fix permanente: `resolver 127.0.0.11 valid=10s;` + `proxy_pass` a una variable (`nginx.conf`), para que resuelva de nuevo en cada request.
  2. **El pool de conexiones de SQLAlchemy se queda con conexiones muertas si Postgres se reinicia sin que `app` también lo haga.** Síntoma: `OperationalError: server closed the connection unexpectedly` en el primer query después del reinicio de Postgres. Fix: `SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}` en `app.py`.
- Esta ronda de deploy se hizo **guiando a Andres paso a paso por su propia terminal SSH** (a pedido suyo, para entender el proceso), no ejecutando los comandos por SSH desde la sesión de Claude Code — por eso el troubleshooting fue más largo de lo normal (se fueron encontrando los bugs en tiempo real, uno por uno, en vez de resolverlos todos de una).

- **Dominio + HTTPS reales (2026-09-29):** `andresqe.duckdns.org` (DuckDNS, elegido por Andres tras comparar 3 opciones), apuntando a la IP fija del servidor. Certificado real de Let's Encrypt vía Certbot (modo `webroot`, en 3 rondas por el problema del huevo y la gallina — Nginx no puede levantar con un cert que no existe). HTTP redirige a HTTPS. Renovación automática (`certbot renew` cada 12h) verificada con `--dry-run` sin gastar cuota real. Confirmado con `openssl s_client`: certificado real, `issuer=Let's Encrypt`, no autofirmado.
- **Panel admin con Flask-Login + CRUD completo funcionando end-to-end (2026-09-29):** modelo `User` (password hasheado con Werkzeug), blueprints `admin` (`/admin/*` — login, logout, dashboard, alta/edición/borrado vía formularios HTML) y `api` (`/api/*` — lectura pública, escritura con `@login_required`), CSRF (Flask-WTF) en los formularios de admin. `app.py` pasó a app-factory (`create_app()`) para poder registrar blueprints sin imports circulares. Usuario admin creado con `create_admin.py` (interactivo, `getpass`, la contraseña real nunca pasó por el chat ni por ningún archivo). Frontend público (`/`) reescrito: consume `GET /api/projects` por `fetch` desde JS vanilla (sin framework), con escape manual de los valores antes de meterlos al DOM. Sección "Demos" agregada como placeholder ("Próximamente") — los demos de IA reales son semana 13, acá solo se dejó el lugar en el frontend.
- **Contenido real cargado:** `seed.py` reescrito para insertar 4 entradas (una por semana 4-7 de `qa-automation-portfolio`, cada una con su propio link a la subcarpeta/archivo real del repo) en vez de la única entrada combinada de la semana pasada — que se borra automáticamente al re-correr el seed.
- **Verificado en producción, con el navegador real:** captura de pantalla del dashboard de admin logueado mostrando las 4 entradas con Editar/Borrar; Andres probó crear y borrar una entrada de prueba con éxito (CRUD de escritura confirmado, no solo lectura).
- **Bug nuevo encontrado y corregido (2026-09-29):** al copiar el `SECRET_KEY` al `.env`, Andres incluyó literalmente los símbolos `<` `>` de la notación de placeholder de la instrucción (`SECRET_KEY=<valor-real>` en vez de `SECRET_KEY=valor-real`) — no rompió nada (Flask acepta cualquier string), pero se corrigió por prolijidad. En el camino se confirmó otro detalle importante: `docker compose up -d` no siempre recrea un contenedor solo porque cambió un valor de `.env`; la forma confiable de confirmar qué valor tiene el proceso corriendo de verdad es `docker compose exec <servicio> printenv <VAR>`, no leer el archivo `.env` ni confiar en el mensaje de Compose.
- **Rediseño del sitio público (2026-10-01):** a partir de un prototipo en un canvas de diseño (4 direcciones exploradas, elegido el estilo "dashboard" con menú lateral). Pasó de una sola página (`index.html` + `fetch` a la API) a un sitio multipágina renderizado en el servidor (blueprint `public` en `app/public.py`): Overview, Experiencia y un caso de estudio (`/proyectos/ui-playwright`), en español e inglés con el idioma en la URL (`/en/...`) y textos centralizados en `app/content.py`. Contenido tomado de la HV de Andres (5+ años en software, 3.5+ en automatización, métricas de FLYR/Transfiriendo/Sigma). Foto en `app/static/img/andres.jpg` (recortada para quitar la marca de agua de Gemini). El panel admin sigue igual (`base.html` + `style.css`). Verificado localmente con SQLite + seed: las 6 rutas responden 200, capturas con Playwright en escritorio y móvil, sin scroll horizontal. Pendiente de completar en `content.py`/templates: `[N]` tests y `[X] min` del caso de estudio, escenario Gherkin real, y subir el CV público (sin teléfono) a `app/static/cv/`. **Completado (2026-10-01):** CV público sin teléfono en `app/static/cv/CV_Andres_Gonzalez.pdf`; el caso de estudio muestra datos reales de `qa-automation-portfolio` — 8 escenarios UI (6 tests + 2 escenarios BDD), que con las baterías de Excel (4 reservas + 5 habitaciones) son 15 casos por navegador, ~9 min de pipeline (dato de Andres) y el escenario real de `features/booking.feature`.
- **HV actualizada (2026-10-01):** nuevo CV en `app/static/cv/CV_Andres_Gonzalez.pdf` (sin teléfono, título interno `CV_Andres_Gonzalez`). Cambian los números del sitio a **6+ años en software / 4+ en automatización**, FLYR desde **Feb 2024** y Netactica **Oct 2022 – Feb 2024**. Se corrigió además la atribución de logros por empresa (la extracción de texto del PDF anterior los mezclaba): FLYR suma las validaciones API de recargas/vouchers y el −30% en resolución de defectos; Netactica tiene el −18% de fuga de defectos y Azure DevOps; Transfiriendo el −37% con Stela, +22% de cobertura de requerimientos y los ciclos de regresión/integración. Fuente de verdad: `JOBS` en `app/content.py`.

- **HV versión final (2026-10-01):** reemplaza al CV anterior en `app/static/cv/CV_Andres_Gonzalez.pdf`. Cambios llevados a la web: cargo en FLYR "Quality Engineer II | QA Automation Engineer", Netactica "QA Engineer (Manual & Automation)", y Formación con la Universidad Autónoma de Manizales (Ingeniería de Sistemas en curso; Tecnología en Análisis y Programación de Sistemas **2020** —no 2022—; Técnico Profesional en Programación de Computadores 2017–2019).
### ❌ Todavía no empezado
- Validar el systemd unit con un reinicio real del servidor (opcional, decisión de Andres — es una acción con impacto real en un server que ya tiene datos reales en Postgres).
- ~~Deploy automático~~ — **hecho 2026-09-30** con GitHub Actions (no con una Routine). Ver sección 3d y sección 4.
- Flask-Migrate/Alembic — hoy el schema se crea con `db.create_all()` (simplificación documentada a propósito, ver `app.py`); introducir migraciones de verdad antes de que el schema deje de ser trivial.
- Demos de IA reales (SDK Anthropic) — semana 13, el placeholder ya está en el frontend.
- Semanas 11-14: fuera de alcance por ahora (Routines, Cowork/MCP, demos IA, lanzamiento) — ver el plan completo en `C:\Users\andre\Documents\proyecto_claude\plan-estudio-andres-qe-ia-contexto-v2.md`.

**✅ Hito: la semana 8 del plan queda funcionalmente completa** (SSH, puertos OCI + iptables, Nginx, Gunicorn/Python, systemd service — todo dockerizado en vez de nativo, decisión tomada con Andres).

**✅ Hito: la semana 9 del plan (PostgreSQL + Flask-SQLAlchemy + API REST + dominio + HTTPS) queda completa.**

**✅ Hito: la semana 10 del plan (frontend público + panel admin con auth real + contenido real cargado) queda completa.** Único punto no implementado a propósito: los demos de IA en vivo, que son contenido explícito de la semana 13.

---

## 3. PENDIENTES INMEDIATOS (semana 8)

Todos los pendientes de la semana 8 (incluidos los menores) están cerrados:

- [x] Abrir `80/443 tcp` en iptables local — **hecho 2026-09-18**, persistido en `/etc/iptables/rules.v4`.
- [x] Abrir `80/443 tcp` en la **Security List de Oracle Cloud** — **hecho 2026-09-29**.
- [x] Instalar/verificar Docker Compose en el servidor — **hecho 2026-09-29**, ya venía con la instalación de Docker.
- [x] Armar un `docker-compose.yml` inicial con un servicio "hello world" — **hecho 2026-09-29**.
- [x] Escribir y activar el systemd unit — **hecho 2026-09-29**.
- [x] Limpiar la regla de `8211/udp` (Palworld) — **hecho 2026-09-29**, en las dos capas.
- [x] Repo público en GitHub + deploy vía git (`git clone`/`git pull`) en vez de `scp` manual — **hecho 2026-09-29**.
- [ ] (Opcional, no bloqueante) Validar el systemd unit con un reinicio real del servidor.

---

## 3b. PENDIENTES INMEDIATOS (semana 9)

Todos los pendientes de la semana 9 están cerrados:

- [x] PostgreSQL containerizado con volumen persistente — **hecho 2026-09-29**.
- [x] Modelo Flask-SQLAlchemy (`Project`) — **hecho 2026-09-29**.
- [x] API REST Flask (lectura) — **hecho 2026-09-29**, `GET /api/projects` y `GET /api/projects/<id>`.
- [x] Dominio gratuito — **hecho 2026-09-29**, DuckDNS (`andresqe.duckdns.org` → `158.247.123.101`).
- [x] Nginx + SSL (Let's Encrypt/Certbot) — **hecho 2026-09-29**, certificado real emitido y HTTP→HTTPS redirigiendo, renovación automática verificada con `--dry-run`.
- [x] Endpoints de escritura del API (POST/PUT/DELETE) — **hecho 2026-09-29**, protegidos con `@login_required`.
- [ ] Flask-Migrate/Alembic — hoy usa `db.create_all()`, simplificación documentada a propósito mientras el schema sea trivial.

---

## 3c. PENDIENTES INMEDIATOS (semana 10)

Todos los pendientes de la semana 10 están cerrados:

- [x] Frontend HTML/CSS consumiendo la API — **hecho 2026-09-29**, fetch a `/api/projects` desde JS vanilla, sin framework.
- [x] Panel admin con Flask-Login — **hecho 2026-09-29**, login/logout, CRUD completo vía formularios, CSRF.
- [x] Primera sección de demos interactivos — **hecho 2026-09-29** como placeholder a propósito ("Próximamente"); los demos reales con IA son semana 13.
- [x] Insertar en la BD todo lo documentado en semanas 4-7 — **hecho 2026-09-29**, 4 entradas reales (UI/Playwright, API testing, CI/CD, Docker+BDD), cada una linkeando a su carpeta/archivo específico del repo.

---

## 3d. PENDIENTES INMEDIATOS (semana 11)

- [x] Routine nocturna: analiza fallos de CI, identifica flaky tests, notifica Slack — **hecho 2026-09-29**, `trig_018RKk64jV8zHmsMQtNvq1ZB`, corre 11pm hora Bogotá, canal `#ci-alerts`.
- [x] Review automático de PRs con checklist QA — **hecho 2026-09-30**, `trig_0142zKmhVNHWazPjBgrVPpfi`, vía **cron horario** (`33 * * * *`) en vez del webhook (que nunca disparó). Verificado con un PR real (#2): comentó con la herramienta MCP de GitHub y detectó las violaciones plantadas. Ver sección 4.
- [x] Deploy automático del `qa-portfolio-server` — **hecho 2026-09-30**: GitHub Actions + clave SSH dedicada con forced command (no una Routine). Primera corrida manual en verde (deploy + smoke test en 6s). Ver sección 4.
- [ ] (Opcional) Confirmar el disparo por `push` real con el próximo cambio que no sea solo `.md` — hasta ahora solo se probó el disparo manual (`workflow_dispatch`).

---

## 4. ÚLTIMO PUNTO DE TRABAJO

**2026-09-18 — Arranque de la semana 8.**

Se retomó el plan de estudio después de cerrar completamente `qa-automation-portfolio` (semanas 4-7, sin pendientes). Antes de tocar el servidor:

1. Se calibró el nivel de Andres en administración Linux (conoce lo básico, experiencia previa administrando un server de Palworld en esta misma instancia — sin experiencia "seria" con Nginx/systemd/iptables).
2. Se confirmó que el servidor Oracle Cloud ya existe y está listo (Andres pasó IP, usuario y ruta de la clave SSH).
3. Se decidió crear este proyecto en un directorio nuevo y separado de `qa-automation-portfolio` (`C:\Users\andre\Documents\qa-portfolio-server`), ya que es un entregable distinto del plan (portafolio web, no suite de testing).
4. Se conectó por SSH y se relevó el estado real del servidor (ver sección 2) — se encontró una discrepancia con el plan original (asumía Ubuntu 24.04, el server real es 20.04) y se corrigió acá.
5. Se preguntó explícitamente por la arquitectura de deploy (dockerizado vs. nativo vs. híbrido) en vez de asumir el plan original al pie de la letra — Andres preguntó si el enfoque nativo (Nginx/systemd a mano) era necesario para su rol; se le explicó que no (Docker es prioridad de mercado explícita para QA Automation/SDET, administración nativa de Nginx no lo es) y se acordó ir con **todo dockerizado**.
6. Se creó el proyecto local: `CLAUDE.md`, `CONTEXT.md` (este archivo), `.gitignore` y `SERVER_INFO.local.md` (gitignorado, con los datos reales de conexión y el relevamiento del servidor).

**Todavía no se aplicó ningún cambio real al servidor** — todo lo hecho hasta ahora es lectura/verificación y documentación local.

---

**2026-09-29 — Cierre funcional de la semana 8 (continuación, misma sesión).**

1. Andres confirmó abrir `80` y `443` juntos (ambas capas). Se aplicó iptables local primero (inserción antes del `REJECT`, persistida), y se le dieron a Andres los pasos exactos para la Security List de Oracle (Claude no tiene acceso a su consola OCI) — lo hizo él mismo paso a paso, con capturas de pantalla, y se verificó juntos con `curl` externo ("Connection refused" en ambos puertos, confirma las dos capas abiertas).
2. Se armó el hello world dockerizado (Flask+Gunicorn detrás de Nginx), se copió al server y se levantó con `docker compose up -d --build` — confirmado con `curl` externo real (`200 OK`, JSON de Flask, headers de Nginx).
3. Se escribió el systemd unit para levantar el compose al boot. Primer intento falló (`exit-code 125`, `journalctl` mostró que `docker compose` imprimía el help general en vez de ejecutar — el plugin de Compose estaba instalado solo para el usuario `ubuntu`, invisible para root/systemd). Se diagnosticó comparando `ls ~/.docker/cli-plugins/` vs `/usr/lib(exec)/docker/cli-plugins/` y se resolvió instalando el plugin a nivel de sistema (`/usr/local/lib/docker/cli-plugins/docker-compose`). Reintentado: `active (exited)`, `enabled`, verificado que la app seguía respondiendo.

**Con esto, la semana 8 queda funcionalmente cerrada** (ver hito en sección 2).

---

**2026-09-29 — Cierre de pendientes menores (misma sesión, continuación).**

Andres pidió cerrar los pendientes menores antes de pasar a la semana 9. Se preguntó primero qué hacer con cada uno (no se asumió):

1. **Regla de Palworld:** Andres eligió eliminarla. Se borró de iptables local primero (`sudo iptables -D INPUT 1` + `netfilter-persistent save`), y se le dieron a Andres los pasos para borrarla también de la Security List de Oracle (la borró él mismo desde la consola).
2. **Deploy vía git:** Andres eligió crear un repo en GitHub ahora (en vez de git local sin GitHub, o dejarlo para después). Sin `gh` CLI disponible en el entorno, Andres creó el repo manualmente desde la web de GitHub (`qa-portfolio-server`, público, sin README/gitignore inicial para poder pushear el contenido local sin conflictos).
3. Antes de pushear a un repo **público**, Andres preguntó explícitamente si era seguro dado que ahí va a vivir "toda la web, cosas personales" — pregunta válida. Se le explicó la distinción: el contenido del portafolio (bio, proyectos) es lo que se busca que sea público; lo que nunca debe estar en git (público o privado) son los secretos reales (contraseñas, API keys, `SECRET_KEY` de Flask) — eso ya estaba resuelto de entrada con `SERVER_INFO.local.md` gitignorado, y se documentó como regla dura para cuando lleguen los secretos de Postgres/Anthropic en semanas 9 y 13. Se verificó con `grep` que la IP/clave no se habían colado en ningún archivo trackeado antes de pushear.
4. Se agregaron a `CLAUDE.md` las mismas reglas de `qa-automation-portfolio` que todavía faltaban acá (sin trailer `Co-Authored-By`, Claude no comitea/pushea sin permiso puntual) — aplicadas por el mismo criterio ya establecido en el repo hermano, sin volver a preguntarlas.
5. Primer commit pusheado a `github.com/anfelgonta201514/qa-portfolio-server` (con permiso explícito de Andres para ese push puntual).
6. En el servidor: se respaldó la copia manual (`mv` a `.manual-backup`), se clonó el repo real en el mismo path, se reconstruyó el stack (`docker compose up -d --build`) y se confirmó con `curl` externo que responde igual que antes. Backup eliminado tras confirmar.

**Todos los pendientes de la semana 8, incluidos los menores, están cerrados.** Solo queda el reinicio de validación (opcional) y todo lo de HTTPS/dominio, que es contenido de la semana 9, no de la 8.

---

**2026-09-29 — Semana 9: Postgres + Flask-SQLAlchemy + API REST (misma sesión, continuación).**

Andres pidió arrancar la semana 9. Se preguntó primero por el dominio/SSL (dependencia externa, necesita que Andres cree una cuenta) — eligió dejarlo para después y arrancar por la parte de datos (Postgres + modelos + API), que no depende de eso.

Se armó el código (modelo `Project`, API de solo lectura, Postgres containerizado, manejo de secretos vía `.env` gitignorado) y se dejó listo. **Andres pidió hacer el deploy él mismo, paso a paso, guiado, para entender el proceso** — cambio de modalidad respecto a semanas anteriores, donde Claude ejecutaba los comandos por SSH directamente. A partir de acá, Claude da instrucciones y explica el porqué; Andres las corre en su propia terminal y pega el resultado.

El deploy guiado encontró y resolvió, en vivo, tres problemas reales (no simulados — bugs genuinos de una primera integración con Postgres):

1. **Contraseña de Postgres generada con `openssl rand -base64`** contenía `/` y `+`, caracteres que rompen el parseo de una URL de conexión (`postgresql://user:PASSWORD@host/db`) si no se escapan. Se corrigió a `openssl rand -hex 24` antes de escribir el `.env` — lección aplicable a cualquier secreto que vaya a vivir dentro de una URL.
2. **`app` crasheaba en loop al conectar a Postgres la primera vez** (`Connection refused`) — `depends_on: - postgres` solo espera a que el *contenedor* exista, no a que Postgres esté listo para aceptar conexiones. Se agregó un `healthcheck` (`pg_isready`) a `postgres` y `depends_on: postgres: condition: service_healthy` a `app`.
3. Aun con eso, aparecieron dos bugs más al verificar (`502 Bad Gateway` primero, `OperationalError` después) — ambos por el mismo patrón general ("algo en el stack sigue apuntando a un estado viejo tras un reinicio de otra pieza"): Nginx cacheaba la IP vieja de `app` (fix: `resolver` dinámico en `nginx.conf`), y el pool de SQLAlchemy tenía conexiones muertas hacia el Postgres viejo (fix: `pool_pre_ping=True`). Ambos documentados en detalle en `README.md` porque son gotchas clásicos de Docker Compose que van a volver a aparecer.
4. En el medio, la sesión SSH de Andres se colgó (no relacionado con el código — problema de red/terminal). Se resolvió abriendo una sesión nueva; el servidor nunca dejó de funcionar.

Al final: `docker compose exec app python seed.py` insertó el ejemplo real (`qa-automation-portfolio`), y se verificó con `curl` externo que `GET /api/projects` devuelve el dato completo desde Postgres.

**Con esto, la parte de datos de la semana 9 (Postgres + SQLAlchemy + API REST) queda funcionalmente completa.** Falta dominio/SSL (pospuesto) y todo lo de semana 10 (panel admin, auth, escritura, insertar el resto del contenido real).

---

**2026-09-29 — Dominio + HTTPS (misma sesión, continuación final).**

Andres retomó el dominio/SSL que había pospuesto. Antes de elegir, preguntó explícitamente por las opciones porque le preocupaba que fuera "difícil de escribir" (asumía que quizás le tocaría usar su nombre completo o algo largo) — se le aclaró que el texto del subdominio lo elige él mismo, no lo asigna nadie, y se compararon 3 opciones (DuckDNS gratis, dominio propio pago, otros DNS dinámicos gratis no recomendados por mala fama/renovación manual). Eligió **DuckDNS**, gratis, para esta etapa del plan.

1. Andres creó `andresqe.duckdns.org` él mismo (cuenta + subdominio + IP apuntando al server) — verificado con `nslookup` que resuelve exacto a `158.247.123.101`.
2. Se armó el flujo de Let's Encrypt en 3 rondas, por el problema clásico del huevo y la gallina (Nginx no puede levantar con un certificado que todavía no existe):
   - **Ronda A:** se agregó a `nginx.conf` un location para servir el desafío ACME (`/.well-known/acme-challenge/`) desde un webroot compartido, y a `docker-compose.yml` un servicio `certbot` con un loop de renovación automática (`certbot renew` cada 12h) ya armado desde el principio, aunque todavía no hubiera ningún certificado que renovar.
   - **Ronda B:** se preguntó a Andres qué email usar para el registro en Let's Encrypt (preguntó si importaba — se le explicó que nunca queda público, solo se usa para avisos de renovación fallida, y se recomendó usar el email real para no perderse ese aviso). Se emitió el certificado real con `docker compose run --rm --entrypoint certbot certbot certonly --webroot ...` (hubo que pisar el entrypoint custom del servicio, que por defecto corre el loop de renovación, no `certonly`).
   - **Ronda C:** se activó el bloque HTTPS real en `nginx.conf` (puerto 443, certificado emitido, HTTP redirige a HTTPS) y se agregó `443:443` a los puertos de `nginx` en el compose (el firewall ya estaba abierto en ambas capas desde la semana 8, no hizo falta tocarlo).
3. Verificado end-to-end: `https://andresqe.duckdns.org/` y `/api/projects` responden bien, certificado real de Let's Encrypt (`issuer=Let's Encrypt`, no autofirmado, confirmado con `openssl s_client`), redirect `301` de HTTP a HTTPS confirmado, y la renovación automática probada con `certbot renew --dry-run` ("Congratulations, all simulated renewals succeeded") sin gastar cuota real ni esperar 90 días.

**Con esto, la semana 9 completa (Postgres + SQLAlchemy + API REST + dominio + HTTPS) queda cerrada.** El deploy guiado paso a paso (iniciado en la sesión de datos) se mantuvo para todo el trabajo de dominio/SSL también — Andres corrió cada comando en su propia terminal SSH.

---

**2026-09-29 — Semana 10: frontend, panel admin y contenido real (misma sesión, continuación final).**

Andres pidió seguir directo a la semana 10. Dado el tamaño (auth real, CRUD completo, frontend, contenido), se reestructuró la app Flask a un patrón más prolijo desde el vamos: app-factory (`create_app()`) + blueprints (`admin`, `api`) en vez de seguir agregando todo a un único `app.py` plano — justificado porque la app va a seguir creciendo (demos de IA en semana 13).

1. Se armó todo el código de una vez (modelo `User`, blueprints, CSRF, templates, CSS, `create_admin.py` interactivo, `seed.py` con las 4 entradas reales) y se dejó listo para el mismo flujo de deploy guiado que ya se venía usando.
2. En el deploy aparecieron dos problemas más, ninguno grave pero ambos con lección real:
   - Andres tipeó literal los símbolos `<` `>` de un placeholder de instrucción al completar el `.env` (`SECRET_KEY=<valor>` en vez de `SECRET_KEY=valor`) — se corrigió el placeholder para el futuro (usar notación que no se preste a confusión) y se explicó por qué no era grave pero sí valía la pena arreglarlo.
   - Quedó la duda de si `docker compose up -d` había recreado `app` con el `.env` corregido — se verificó con la fuente de verdad real (`docker compose exec app printenv SECRET_KEY`) en vez de asumir por el mensaje de Compose o por el contenido del archivo `.env`.
3. Se creó el usuario admin (`create_admin.py`, interactivo con `getpass` — la contraseña real de Andres nunca pasó por este chat ni quedó en ningún archivo) y se recargó el seed con las 4 entradas reales.
4. Verificación final con el navegador real (no simulada): captura de pantalla de Andres logueado en `/admin` viendo las 4 entradas con Editar/Borrar, y confirmación de que pudo crear y borrar una entrada de prueba sin errores — cierra el circuito completo de lectura Y escritura en producción.

**Con esto, la semana 10 completa (frontend público + panel admin con auth real + escritura protegida + contenido real cargado) queda cerrada**, salvo los demos de IA en vivo, que son contenido explícito de la semana 13 y quedaron como placeholder a propósito en el frontend.

---

**2026-09-29 — Semana 11: Routine nocturna de CI + Slack (misma sesión, continuación).**

Andres pidió arrancar la semana 11 (Claude Code avanzado + Routines). De las 3 piezas que pide el plan (routine nocturna de CI→Slack, review automático en PRs, deploy automático del server), se relevaron las limitaciones reales de la herramienta de Routines disponible en esta sesión antes de prometer nada:
- Sin acceso a la lista de conectores de claude.ai desde esta sesión (permiso faltante) — Andres no tenía ningún conector conectado todavía. Se le explicó que Slack/Jira se pueden crear gratis como persona individual, sin ser empresa.
- La API de Routines solo soporta disparo por horario (cron) o corrida única — no por evento de GitHub (PR abierta) directo, salvo una acción `create_webhook_trigger` no explorada todavía (candidata para la pieza de PRs, pendiente).
- El deploy automático del servidor implicaría darle a un agente en la nube la clave SSH de producción — pospuesto a propósito, es una decisión de seguridad que merece su propia conversación.

Se arrancó por la routine nocturna (la única de las 3 sin decisiones pendientes):

1. Andres conectó el conector de Slack en claude.ai y creó un canal `#ci-alerts` vía un workspace propio gratuito.
2. Se probó un webhook de Incoming Webhooks de Slack — funcionó desde esta sesión, pero **la routine en la nube no pudo usarlo**: el sandbox tiene un proxy de salida que bloquea conexiones directas a dominios externos como `hooks.slack.com` (`connect_rejected... organization policy`). Se cambió al conector MCP de Slack (`mcp__Slack__slack_send_message`, nombre distinto al de esta sesión — cada entorno nombra la herramienta distinto según el campo `name` del conector) agregándolo a `allowed_tools` de la routine.
3. Primera corrida de prueba: la routine se adaptó sola (usó `ToolSearch` para encontrar el nombre real de la herramienta de Slack) y mandó un resumen real al canal.
4. Andres preguntó si la routine seguiría funcionando si se agregan/quitan/editan casos de prueba — se le explicó la diferencia entre detección a nivel de *step* de GitHub Actions (lo que hacía) vs. a nivel de *test individual* de pytest (lo que no hacía). Pidió la versión más profunda.
5. Se mejoró el prompt para bajar el log de cada job candidato y extraer el nombre EXACTO del test que falló (buscando la línea `FAILED ruta::test - excepción` que imprime pytest con `-v`). La descarga directa por `curl` al blob storage de logs de GitHub también estaba bloqueada por el mismo proxy — la routine encontró sola una herramienta MCP de GitHub (`get_job_logs`) como alternativa. Resultado real: identificó que varios fallos "bloqueantes" históricos eran en realidad el conflicto de plugins de Allure (ya resuelto hoy más temprano en la sesión) y encontró el test exacto de una flakiness real en `test_room_battery.py` (colisión de ID conocida, documentada en el README de esa suite).
6. Andres notó que el diseño mezclaba "¿cómo está el sitio ahora?" con "¿hubo flakiness en las últimas semanas?", y que estar reportando historial ya resuelto cada noche no tenía sentido. Se reestructuró el prompt: el titular del mensaje es siempre el run MÁS RECIENTE (esa es la respuesta real a "¿cómo está el sitio?"), y el análisis de flakiness profundo solo se dispara si hubo actividad NUEVA en las últimas 24-48hs — si no, una sola línea aclarando que no hay nada nuevo, sin desenterrar historia vieja.
7. Verificado con una corrida real: mensaje limpio "✅ run más reciente OK (fecha, commit), todos los steps bloqueantes pasaron... no hubo actividad en 24-48hs, no se buscó flakiness".

**Routine activa:** `trig_018RKk64jV8zHmsMQtNvq1ZB` — corre todas las noches a las 11pm hora Bogotá (`0 4 * * *` UTC), repo `qa-automation-portfolio`, canal Slack `#ci-alerts`. Link: https://claude.ai/code/routines/trig_018RKk64jV8zHmsMQtNvq1ZB

**Pendiente de la semana 11:** review automático en PRs (evaluar `create_webhook_trigger`) y deploy automático del servidor (pendiente de decisión de seguridad sobre SSH).

---

**2026-09-29 — Semana 11: intento de review automático en PRs vía webhook (misma sesión, continuación — sin resolver, queda documentado para retomar).**

Andres pidió seguir con la pieza de PRs. Resumen de lo hecho, lo que funcionó, y dónde quedó trabado:

1. **Se creó una segunda routine** (`trig_0142zKmhVNHWazPjBgrVPpfi`, "qa-automation-portfolio: review automatico de PRs") con un prompt de checklist QA basado en las reglas reales de `qa-automation-portfolio/CLAUDE.md` (naming de tests, jerarquía de locators, no `time.sleep()`, datos únicos, cosas que no se tocan sin consultar, sync playwright/Dockerfile, uso de `attach_screenshot`). Como `RemoteTrigger.create` exige `cron_expression` o `run_once_at` (no hay opción "solo webhook, sin horario"), se le puso un `run_once_at` en el futuro lejano (2027-01-01) como placeholder inofensivo.
2. **`create_webhook_trigger`** no está documentado en el skill de `/schedule` más allá de una línea genérica. Se descubrió el schema real a prueba y error (cada intento fallido devolvió el nombre del campo que faltaba o sobraba):
   - `filter.actions` → rechazado, no existe filtro por tipo de acción (`opened` vs `synchronize` vs `closed`) — el trigger dispara con CUALQUIER acción del evento.
   - `scope`/`repository` como objeto o string libre → rechazados.
   - Shape que sí funcionó:
     ```json
     {
       "routine_trigger_id": "<id de la routine>",
       "hook_type": "app",
       "source": "github",
       "scope_id": "<owner>/<repo>",
       "events": ["pull_request"]
     }
     ```
   - Primer intento con esta shape reveló que hacía falta instalar la **GitHub App "Claude"** en el repo (`https://github.com/apps/claude/installations/select_target`) — Andres la instaló (con acceso a "All repositories", permisos de lectura/escritura sobre PRs/issues/actions/etc., visible en `github.com/settings/installations`).
   - Con la app instalada, `create_webhook_trigger` devolvió `200 OK` sin warnings — quedó registrado (`trigger_id` del webhook: `a4a7861b-a6ab-47ab-9aad-920ea6814968`).
3. **Prueba real, sin éxito:** se creó una rama (`test/pr-review-routine`, ya borrada) con un archivo dummy (`PR_REVIEW_TEST.md`, nunca llegó a `master`) y se abrió el PR #1. Se generaron 3 eventos reales distintos (`opened`, `closed`, `reopened`) y **ninguno disparó la routine** (`list_runs` siguió vacío los 3 veces). No hay manera, desde las herramientas de esta sesión, de ver los logs de entrega de webhooks de GitHub ni del lado de Anthropic — no se pudo diagnosticar la causa raíz.
4. **PR de prueba cerrado y rama borrada** (local y remoto) a pedido de Andres — no quedó nada de esto en `master`.

**Hipótesis no descartadas para la próxima sesión** (en orden de probabilidad, sin verificar):
- El primer evento (`opened`) puede haber ocurrido mientras la instalación de la GitHub App todavía no estaba 100% propagada (la captura de Andres decía "installed 10 minutes ago" en un momento posterior a cuando se abrió el PR por primera vez) — pero los eventos posteriores (`closed`, `reopened`), varios minutos después, tampoco dispararon nada, lo que debilita esta hipótesis.
- Puede ser un problema específico de esta función (`create_webhook_trigger`) todavía inmaduro en la plataforma — no hay forma de confirmarlo sin soporte de Anthropic.
- Puede haber un desfasaje entre el `scope_id` que devolvió la API (`"github.com/anfelgonta201514/qa-automation-portfolio"`, con el prefijo `github.com/` agregado por el server) y cómo GitHub identifica el repo internamente al enviar el webhook — no verificado.

**Routine y webhook quedan configurados tal cual** (`trig_0142zKmhVNHWazPjBgrVPpfi`, enabled, con el webhook `a4a7861b-a6ab-47ab-9aad-920ea6814968` enganchado) por si el problema se resuelve solo del lado de la plataforma en el futuro — no hace daño dejarlos así.

**Opciones para retomar, discutidas con Andres y no descartadas:**
1. Reemplazar el enfoque por una routine con **cron cada 1 hora** (el mínimo permitido) que busque PRs abiertos sin comentario de review todavía — no es instantáneo, pero usa el mecanismo de routines que SÍ se probó confiable (la nocturna de CI).
2. Dejarlo como está y reintentar otro día (quizás la plataforma lo arregle sola, o aparezca más documentación de `create_webhook_trigger`).
3. Abandonar esta pieza — de las 3 de la semana 11, la más valiosa (routine nocturna de CI + Slack) ya quedó funcionando sólido.

**Nota para quien retome:** el repo `qa-automation-portfolio` ahora tiene la GitHub App "Claude" instalada con acceso a todos sus repos — ver nota cruzada en el propio `CONTEXT.md`/`CLAUDE.md` de ese repo.

*(Histórico: las 3 opciones de arriba se resolvieron en la entrada siguiente.)*

---

**2026-09-30 — Semana 11: review de PRs resuelto y deploy automático diseñado (sesión nueva).**

**Review de PRs.** Andres eligió reintentar el webhook. Antes de probar se revisó el log real de la routine nocturna y se corrigió un supuesto: `curl` a `api.github.com` **sí** funciona para leer desde el sandbox. El problema real era comentar, que requiere autenticación. Se reescribió el prompt: comenta con la herramienta MCP de GitHub (`gh` solo como respaldo), deja una línea `DIAG:` con lo que recibió del evento y no duplica comentarios del mismo head sha.

La prueba separó los dos problemas con un PR real (#2, rama `test/pr-review-routine-2`, archivo de prueba con un `time.sleep()` y un XPath plantados):
1. **Webhook: no disparó** (5 minutos de espera, cuarto evento real sin runs). Queda confirmado que falla del lado de la plataforma.
2. **Corrida manual con el PR abierto: funcionó completa en 19s.** Reportó "sin payload de evento", encontró el PR, publicó el comentario con `mcp__github__add_issue_comment` y detectó las 2 violaciones plantadas más una tercera real (locator inline fuera de un Page Object), sin inventar problemas.

Decisión de Andres: agregar un **cron horario** como mecanismo real y dejar el webhook enganchado por si la plataforma lo arregla. La plataforma asignó el minuto 33 (`33 * * * *`). La rama de prueba se borró y el PR #2 quedó cerrado.

**Deploy automático.** Andres eligió GitHub Actions + clave dedicada en vez de una Routine con acceso SSH, para que una credencial de producción no pase por un agente de IA. Se verificó en la Security List que el puerto 22 ya acepta `0.0.0.0/0`, así que los runners de GitHub pueden entrar sin tocar el firewall. Archivos nuevos, **sin commitear**:
- `.github/workflows/deploy.yml`: push a `main` (ignora `.md`) o manual; SSH con huella fijada; smoke test HTTPS a `/` y `/api/projects` con reintentos; `concurrency` para no solapar deploys.
- `deploy/deploy.sh`: `git pull --ff-only` → `docker compose up -d --build` → `restart nginx`.
- `.gitattributes`: fuerza LF en `*.sh`.
- `README.md`: sección "Deploy automático" con el diseño de seguridad.

Andres commiteó y pusheó esos archivos (`a793bd1`). La corrida por `push` falló como se esperaba (todavía no había secrets).

**Configuración guiada (misma sesión).** Andres ejecutó cada comando en su propia terminal:
1. `git pull --ff-only` en el servidor. Se verificó `deploy.sh`: `bash -n` sin errores y 0 caracteres `\r`, así que el `.gitattributes` funcionó.
2. Clave `ed25519` generada **en la PC de Andres** (`~/.ssh/qa_portfolio_deploy`, sin passphrase, comentario `github-actions-deploy`). Un primer intento se corrió por error en la sesión SSH del servidor y falló con "Permission denied" sin crear nada.
3. Clave pública agregada a `~/.ssh/authorized_keys` del servidor con `command="bash /home/ubuntu/qa-portfolio-server/deploy/deploy.sh",restrict`. Hay respaldo en `authorized_keys.bak-<fecha>`.
4. **Prueba de la restricción:** `ssh -i qa_portfolio_deploy ubuntu@<IP> whoami` no imprimió `ubuntu`, sino que ejecutó el deploy completo. Confirma que la clave entra y que el forced command ignora cualquier otro comando.
5. **Huella del host verificada por dos caminos:** `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` dentro del servidor y `ssh-keyscan` desde afuera dieron la misma huella (`SHA256:XrauocfD...`). Recién entonces se usó como `DEPLOY_KNOWN_HOSTS`.
6. Andres cargó los 4 secrets. La clave privada se copió con `Get-Content -Raw | Set-Clipboard`, sin mostrarse en pantalla ni pasar por el chat.
7. **Corrida manual (`workflow_dispatch`): verde.** Configure SSH, deploy y smoke test pasaron en 6s, y el sitio respondió `200` en `/` y `/api/projects` verificado desde afuera.

Detalle menor observado: `docker compose` avisa "requires buildx plugin". Usa el builder clásico y funciona igual que en los deploys manuales. Instalar buildx es opcional.

**Con esto, la semana 11 queda cerrada:** routine nocturna de CI, review de PRs (cron) y deploy automático (GitHub Actions). Lo único pendiente es opcional: ver el disparo por `push` real con el próximo cambio de código.

**Siguiente paso recomendado:** semana 12 del plan (Cowork/MCP), o antes, si Andres quiere, los opcionales (reinicio real del servidor para validar systemd, Flask-Migrate, buildx).
