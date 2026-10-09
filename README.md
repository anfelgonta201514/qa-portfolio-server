# qa-portfolio-server

Servidor y portafolio web personal de Andres Gonzalez — semanas 8-14 de un plan de estudio de 14 semanas más amplio (Claude IA + QE Automation). Continúa a [`qa-automation-portfolio`](../qa-automation-portfolio) (semanas 4-7): ese repo demuestra el stack de testing, este aloja el sitio que lo presenta.

Corre sobre una instancia Oracle Cloud Always Free (Ubuntu 20.04 LTS, ARM/aarch64). Público en **https://andresqe.duckdns.org**.

## Arquitectura

Todo dockerizado — ver `CLAUDE.md` para el porqué de esta decisión.

```
Nginx (contenedor, proxy inverso, resolución dinámica de upstream, HTTPS)
  → Gunicorn (contenedor, WSGI)
    → Flask (app Python — frontend público + API REST + panel admin)
      → PostgreSQL (contenedor, volumen persistente)

Certbot (contenedor) → certificado Let's Encrypt para andresqe.duckdns.org,
                        renovación automática cada 12h (solo renueva si
                        falta <30 días para el vencimiento)

systemd (qa-portfolio.service) → docker compose up -d al boot del servidor
```

## Estructura

```
qa-portfolio-server/
├── app/
│   ├── app.py           → app factory Flask: registra blueprints, Flask-Login, CSRF, config
│   ├── api.py           → blueprint /api/* — lectura pública, escritura con @login_required
│   ├── admin.py         → blueprint /admin/* — login/logout, dashboard, alta/edición/borrado
│   ├── models.py        → modelos SQLAlchemy: Project, User (password hasheado)
│   ├── create_admin.py  → script interactivo para crear/actualizar el usuario admin (getpass, nunca en texto plano)
│   ├── seed.py           → carga las 4 entradas reales de qa-automation-portfolio (idempotente)
│   ├── public.py        → blueprint del sitio público: overview, experiencia y casos de estudio, en ES y EN
│   ├── content.py       → todos los textos del sitio público en español e inglés (+ traducción EN de los proyectos)
│   ├── templates/        → Jinja2: site/ (sitio público), base.html + admin/ (login, dashboard, form)
│   ├── static/           → site.css (sitio público), style.css (admin), img/ (foto), cv/ (PDF del CV, opcional)
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/
│   └── nginx.conf       → reverse proxy hacia `app`, resolver dinámico, HTTP→HTTPS, TLS con el cert de Certbot
├── docker-compose.yml   → orquesta app + nginx + postgres + certbot
├── .env.example          → plantilla de variables (copiar a .env, nunca commitear el real)
├── deploy/
│   └── qa-portfolio.service → systemd unit, instalado en /etc/systemd/system/ del servidor
└── SERVER_INFO.local.md → datos de conexión reales, gitignorado, NUNCA se commitea
```

## Estado

✅ **Portafolio completo funcionando end-to-end, con HTTPS real**: frontend público en `https://andresqe.duckdns.org` consumiendo `GET /api/projects` (4 entradas reales de `qa-automation-portfolio`, una por semana 4-7), panel admin (`/admin`) con login real (Flask-Login + contraseña hasheada), CRUD completo de proyectos protegido por sesión, CSRF en los formularios. Certificado de Let's Encrypt con renovación automática verificada. Las dos capas de firewall abiertas y verificadas. systemd levanta todo el stack al boot. Deploy automático con GitHub Actions en cada push a `main` (SSH con clave restringida + smoke test post-deploy).

Sección "Demos" en la home: **placeholder a propósito** ("Próximamente") — los demos de IA aplicada a QA (generador de test cases, analizador de bugs, generador de suites de API) son contenido de la semana 13, no de la 10. Desde el 2026-10-07 el enfoque es **multi-proveedor**: el portafolio muestra el uso de IA en general, no de una sola marca, y cada demo indica qué modelo lo genera (ver "Enfoque de IA del portafolio" en `CLAUDE.md`).

Pendiente: migraciones con Flask-Migrate/Alembic (hoy usa `db.create_all()`, suficiente mientras el schema sea trivial), demos de IA (semana 13).

## Dominio y HTTPS

- **DNS:** `andresqe.duckdns.org` → `158.247.123.101`, configurado a mano en DuckDNS (IP fija de Oracle Cloud Always Free — no hace falta el cliente de actualización dinámica de DuckDNS, la IP no cambia sola).
- **Certificado:** Let's Encrypt vía Certbot, modo `webroot` (usa el propio Nginx para responder el desafío HTTP, sin tener que parar nada). Emitido una sola vez a mano:
  ```bash
  docker compose run --rm --entrypoint certbot certbot certonly \
    --webroot -w /var/www/certbot \
    -d andresqe.duckdns.org \
    --email andresfelgonta@gmail.com \
    --agree-tos --no-eff-email
  ```
- **Renovación:** el servicio `certbot` del compose corre un loop (`certbot renew` cada 12h) — no hace nada mientras el certificado no esté por vencer. Probar que funciona sin gastar cuota real ni esperar 90 días:
  ```bash
  docker compose run --rm --entrypoint certbot certbot renew --dry-run
  ```

## Sitio público (multipágina, ES/EN)

Diseño tipo dashboard (menú lateral + header) con páginas separadas en vez de una sola página larga: el Overview concentra lo que un reclutador ve sin hacer clic (rol, años, métricas de impacto, experiencia resumida, proyectos, contacto) y las demás páginas dan profundidad para un entrevistador técnico.

| Página | Español | Inglés |
|---|---|---|
| Overview | `/` | `/en/` |
| Experiencia | `/experiencia` | `/en/experience` |
| Caso de estudio UI | `/proyectos/ui-playwright` | `/en/projects/ui-playwright` |

- **Idioma por URL**, no por cookie ni JS: el selector ES/EN del header enlaza a la misma página en el otro idioma, y cada página declara su par con `<link rel="alternate" hreflang>` para que los buscadores indexen las dos versiones.
- **Textos en `app/content.py`**, nunca sueltos en los templates — una frase se cambia en los dos idiomas en el mismo lugar.
- **Los proyectos siguen saliendo de la base** (se editan desde `/admin`). La base guarda un solo idioma: `PROJECT_EN` en `content.py` traduce los 4 proyectos cargados por título; uno nuevo se muestra con su texto original en `/en/` hasta agregarle traducción ahí. `CASE_STUDIES` define qué proyecto enlaza a su página de caso de estudio (el resto enlaza a su código en GitHub).
- **CV descargable**: `app/static/cv/CV_Andres_Gonzalez.pdf` (versión pública, **sin teléfono** — el repo y el sitio son públicos), el mismo archivo para ES y EN. El botón se oculta solo si el archivo no existe.
- **Logo / favicon**: monograma AG con check (variante "Minimalista"), en `app/static/img/` — `favicon.ico` (16–64px, también servido en `/favicon.ico`), `favicon-32.png`, `apple-touch-icon.png`, `icon-192/512.png` y `logo-mark.png` (header). Paleta: fondo `#0B0F14`, logo `#F1F5F9`, check/éxito `#14B8A6` (mismo verde que usa el sitio para estados OK).
- **Contacto por correo**: los botones "Escríbeme" / "Hablemos" son `mailto:` normales (funcionan sin JS); con JS abren un `<dialog>` para elegir Gmail, Outlook web, la app de correo del sistema o copiar la dirección.
- "Este sitio" y "Demos IA" están en el menú como **"pronto"**: hoy son secciones del Overview, sus páginas propias vienen después (los demos son semana 13).

## Panel admin

`/admin/login` — protegido con Flask-Login (contraseña hasheada con Werkzeug, nunca en texto plano) y CSRF en los formularios. Los endpoints de escritura del API (`POST`/`PUT`/`DELETE /api/projects`) requieren la misma sesión.

**Crear o resetear el usuario admin** — interactivo, la contraseña nunca pasa por el chat, un archivo ni un log (usa `getpass`):
```bash
docker compose exec -it app python create_admin.py
```
Correrlo de nuevo con el mismo usuario actualiza su contraseña.

## Cómo desplegar

El servidor tiene un `git clone` de este mismo repo en `~/qa-portfolio-server` (público, no necesita credenciales). Los pasos del deploy viven en [`deploy/deploy.sh`](deploy/deploy.sh): `git pull --ff-only` → `docker compose up -d --build` → `docker compose restart nginx`.

**El `docker compose restart nginx` del final no es opcional** — ver la nota de "resolución de DNS" en troubleshooting más abajo. Reiniciarlo siempre es seguro (tarda menos de un segundo).

### Deploy automático (GitHub Actions)

Cada push a `main` (salvo cambios solo en `.md`) dispara [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml), que entra por SSH al servidor, corre `deploy/deploy.sh` y después hace un **smoke test** contra el sitio real por HTTPS (`/` y `/api/projects`, con reintentos). Un deploy solo cuenta como exitoso si el sitio responde después. También se puede disparar a mano desde Actions → Deploy → Run workflow.

**Por qué GitHub Actions y no una Routine de Claude Code** (el plan original proponía una Routine): automatizar el deploy implica guardar una credencial de acceso a producción en algún lado. Un workflow de GitHub con una clave dedicada es el estándar de la industria, y la clave nunca pasa por un agente de IA.

**Diseño de seguridad:**
- **Clave SSH dedicada solo a deploy**, distinta de la clave personal. Se guarda como secret de GitHub (`DEPLOY_SSH_KEY`) y nunca entra al repo.
- **Forced command en el servidor:** en `~/.ssh/authorized_keys` la clave está registrada con `command="bash /home/ubuntu/qa-portfolio-server/deploy/deploy.sh",restrict`. Esa clave **solo** puede ejecutar el script de deploy: sin shell interactiva, sin port forwarding y sin ejecutar otros comandos. Si se filtrara, lo único que permite es redeployar lo que ya está en `main`.
- **Huella del host fijada** (`DEPLOY_KNOWN_HOSTS`) en vez de `StrictHostKeyChecking=no`, para no aceptar a ciegas un servidor impostor.
- **`concurrency`**: nunca corren dos deploys a la vez.
- **`git pull --ff-only`**: si alguien editó a mano archivos versionados en el servidor, el deploy falla en vez de pisarlos o mergearlos.

**Secrets del repo** (Settings → Secrets and variables → Actions): `DEPLOY_SSH_KEY` (clave privada de deploy), `DEPLOY_HOST` (IP del servidor), `DEPLOY_USER` (`ubuntu`), `DEPLOY_KNOWN_HOSTS` (salida de `ssh-keyscan -t ed25519 <IP>`, verificada contra la huella real del servidor).

**Deploy manual** (si Actions no está disponible), desde el servidor:
```bash
bash ~/qa-portfolio-server/deploy/deploy.sh
```

## Badges con el estado real del CI

Los badges de cada proyecto (y el "CI passing" del caso de estudio) **no son texto fijo**: [`app/ci_status.py`](app/ci_status.py) lee el último run completado de `tests.yml` en `master` de `qa-automation-portfolio` desde la API pública de GitHub. Si el CI se pone rojo, el sitio lo muestra.

| Badge | Sale de |
|---|---|
| API | job `API tests` |
| UI | los 3 jobs `UI tests (chromium / firefox / webkit)` |
| BDD | step bloqueante `Run UI tests (BDD - admin room)` de los jobs de UI |
| CI/CD | resultado del run completo |

Estados: `passing` (verde) · `failing` (rojo) · `sin datos` / `no data` (gris).

**Decisiones de diseño:**
- **Nunca miente por omisión.** Si GitHub no responde, si cambian los nombres de los jobs, o si el último dato tiene más de 6 h, el badge dice "sin datos", jamás "passing". Un run **cancelado** tampoco cuenta como fallo.
- **No frena la página.** La lectura corre en un hilo aparte, con caché de 5 min; las páginas responden siempre con lo que haya en memoria. Se calienta al arrancar para que el primer visitante tras un deploy no vea "sin datos".
- **Respeta el límite de la API** sin autenticar (60 peticiones/hora por IP): 2 peticiones por refresco = máximo 24/hora. Tras un error espera 60 s antes de reintentar. Si un error ocurre con un dato bueno en caché, se conserva ese último dato (hasta las 6 h).
- **Solo librería estándar** (`urllib`): no agrega dependencias a la imagen Docker.
- El badge no es un enlace: en la home vive dentro de una tarjeta que ya es un `<a>`, y un `<a>` dentro de otro es HTML inválido. El detalle (commit y fecha del run) va en el tooltip.

**Limitación conocida:** los steps con `continue-on-error: true` (booking flow y BDD booking, ver `CLAUDE.md` de `qa-automation-portfolio`) figuran como `success` en la API aunque fallen, así que su fallo **no** se refleja en los badges. Es coherente con la regla del repo de que ese fallo en CI es esperado, pero hay que saberlo: "passing" aquí significa "pasaron los steps bloqueantes".

**Pruebas** (sin red; GitHub se simula; base SQLite en memoria, ver `app/tests/conftest.py`):
```bash
python -m pytest app/tests -q
```
Cubren la lógica de estado (todo verde, un job rojo, un navegador rojo, run cancelado, jobs que faltan) y el comportamiento ante fallos (GitHub caído, dato viejo, error con dato bueno en caché). Se comprobó además con mutaciones que detectan el bug más grave, mostrar "passing" cuando no hay datos. Variable `CI_STATUS_DISABLED=1` apaga la lectura (los badges salen en "sin datos").

## Demos de IA aplicada a QA

Página `/demos` (`/en/demos`) con tres demos: **generador de casos de prueba** (desde una historia de usuario), **analizador de bugs** (desde una traza de error) y **generador de tests de API** (desde la especificación de un endpoint). Contenido en [`app/demo_content.py`](app/demo_content.py), plantilla en `app/templates/site/demos.html`.

**Son ejemplos reales pregenerados, no resultados en vivo, y la página lo dice.** Cada respuesta la generó de verdad el modelo indicado en `MODEL` (hoy Claude Sonnet 5.5, en una sesión de Claude Code, el 2026-10-07). No hay ningún cuadro de entrada libre, porque insinuaría que lo que se escribe se procesa en el momento. Es una decisión consciente del enfoque de IA del portafolio (ver `CLAUDE.md`): costo cero, cero riesgo de abuso, y un respaldo permanente para cuando exista un modo en vivo.

**Garantías verificadas:**
- **El código de los tests de API se ejecutó contra la API real antes de publicarlo**: `3 passed` y `4 passed, 1 xfailed`, el resultado que declara cada ejemplo (`run`). Los comportamientos raros salieron de probar la API de verdad: un payload sin `firstname` responde 500 (no 400), y un `totalprice` no numérico se acepta y se guarda como `null` (por eso ese test es `xfail(strict=True)`). Para repetir esa comprobación: `python -m pytest app/tests -q -m network` (necesita red; no corre por defecto).
- **Dos ejemplos de bugs son casos reales de este proyecto** (el test de login con contraseña incorrecta y el choque entre los plugins de Allure), marcados como tales en la página.
- **Se probó con mutaciones que las pruebas detectan los fallos de honestidad**: que la página diga "en vivo", que aparezca un cuadro de entrada, y que se desactive el escape de HTML.
- Verificado en el navegador, en español e inglés, y en móvil (375 px) sin desbordamiento horizontal.

**Limitaciones:** el visitante no puede probar su propia entrada. Los textos de los ejemplos de casos de prueba salen de los criterios de aceptación de la historia, no de comprobar la aplicación real (solo los de API se ejecutaron). La capa del modo en vivo (siguiente sección) ya existe y está probada, pero **no está conectada a ningún endpoint ni formulario**: sigue apagada.

## Capa de proveedor de IA (modo en vivo, apagado)

Tres módulos pequeños que preparan el modo en vivo sin atarlo a una marca (ver "Enfoque de IA del portafolio" en `CLAUDE.md`). **Groq está registrado como primer proveedor (QAP-14), pero no hay endpoint que lo use y `AI_PROVIDER` está vacío:** los demos siguen mostrando los ejemplos pregenerados. Esto es la base probada, no una función activa.

| Módulo | Qué hace |
|---|---|
| [`ai_provider.py`](app/ai_provider.py) | Interfaz `Provider` (`generate()`), registro `PROVIDERS` y `GroqProvider` (solo librería estándar), escrito con la documentación oficial de Groq. Elección y fuentes en [`docs/proveedores-ia.md`](docs/proveedores-ia.md). Cambiar de proveedor o modelo = variables del `.env`. Una configuración errónea deja el modo en vivo apagado con un aviso en el log, nunca tumba el sitio |
| [`ai_limits.py`](app/ai_limits.py) | Límite por visitante (ventana deslizante) y tope diario global. Decisión atómica con candado; una petición rechazada no consume cupo; la memoria queda acotada por el tope diario |
| [`ai_service.py`](app/ai_service.py) | Valida la entrada, aplica los límites, llama al proveedor y, si algo falla, devuelve el ejemplo pregenerado |

**Reglas que hace cumplir el servicio:**
- **El demo nunca depende del proveedor.** Cuota agotada (429), error, timeout, respuesta vacía o límite alcanzado → el resultado es el ejemplo pregenerado, con el motivo (`mode="fallback"`, `reason=...`). Solo `mode="live"` significa "lo generó el proveedor ahora".
- **Límites por defecto:** 5 peticiones por visitante cada 10 min, 100 al día entre todos, entrada máxima de 4000 caracteres (se **rechaza**, nunca se trunca en silencio), respuesta máxima de 1200 tokens, 15 s de espera. Todo configurable (`.env.example`); un valor inválido vuelve al por defecto.
- **Las llamadas fallidas también cuentan** contra el límite: el proveedor pudo haber gastado cuota igual.
- **La entrada del visitante nunca se registra en el log** (puede traer datos sensibles), ni su IP, ni la clave de API.
- **La entrada nunca se concatena al prompt del sistema**: viaja aparte como mensaje de usuario, y el prompt le indica al modelo que la trate como material a analizar e ignore instrucciones que traiga dentro.
- **IP del visitante:** se usará `X-Real-IP`, que Nginx fija con la IP real y que Flask solo recibe desde Nginx (el puerto 8000 no está publicado). **No** `X-Forwarded-For`: Nginx le agrega lo que mande el cliente y se puede falsificar.

**Verificado:** 127 pruebas de la capa (16 del limitador, 50 del servicio y la configuración, y 61 del proveedor de Groq) con un proveedor y respuestas HTTP simuladas (`app/tests/fakes.py`), sin gastar nada ni salir a la red, incluida concurrencia (100 hilos contra un mismo visitante y 200 visitantes contra el tope diario: nunca se supera el límite). Además, un análisis de mutaciones: se plantaron 12 bugs (quitar el candado, ignorar el tope diario, truncar la entrada, mezclar la entrada en el prompt del sistema, registrar la entrada en el log, subir los workers, registrar el proveedor simulado en producción...) y las pruebas detectan los 12. En una primera pasada no detectaban la falta del candado: la prueba de concurrencia no agrandaba la ventana de la carrera donde correspondía; ahora la detecta 5 de 5 veces y el código correcto pasó 25 de 25 corridas.

**Requisitos antes de activar el modo en vivo (no hechos aún):**
1. ~~Registrar el proveedor~~ — **hecho** (`GroqProvider`). Falta probarlo contra Groq de verdad: `GROQ_API_KEY=... python -m pytest app/tests -m groq_live -q -s` (la clave solo en el entorno de quien corre la prueba; consume una cantidad mínima de cuota).
2. **Pasar las variables `AI_*` al contenedor `app` en `docker-compose.yml`.** El compose solo entrega las variables que lista; sin esto la app no ve el `.env` aunque tenga las variables.
3. **Gunicorn con hilos.** Hoy corre con **un worker síncrono**: mientras espera al proveedor (hasta 15 s) **todo el sitio queda bloqueado**. Hace falta `--threads` (un solo proceso, para que los límites en memoria sigan valiendo).
4. **Endpoint y formulario**, con aviso de "no pegues datos reales ni confidenciales" y la etiqueta del modelo en cada respuesta viva.

**Limitaciones conocidas:**
- Los contadores viven **en memoria**: se ponen en cero con cada reinicio o deploy, y valen solo con **un único worker** (una prueba falla si alguien sube los workers en el `Dockerfile`; con varios habría que mover el estado a Postgres).
- Visitantes detrás de una misma red comparten IP y, por tanto, el mismo límite.
- **La primera llamada real a Groq (2026-10-09) falló con un 403 que las pruebas simuladas no podían ver**: Cloudflare bloquea el `User-Agent` por defecto de `urllib`. Ya está corregido (ver `docs/proveedores-ia.md`, "Hallazgo de la primera llamada real"), con una prueba de regresión, pero **todavía falta repetir la prueba real con la corrección**. Sus pruebas normales usan respuestas simuladas escritas según la documentación oficial. Siguen sin comprobarse la latencia real, el formato exacto de los errores, la cuota, y sobre todo **si el razonamiento de los modelos `gpt-oss` se come el tope de salida y devuelve respuestas vacías** (la documentación no dice si esos tokens cuentan; la capa ya responde con el ejemplo pregenerado en ese caso).

## Lectura de logs desde Claude (solo lectura)

Para que Claude pueda analizar el servidor (errores de la app, Nginx, renovación de certificados) sin darle acceso de escritura, hay una **segunda clave SSH, distinta de la de deploy**, atada a [`deploy/logs.sh`](deploy/logs.sh) con un forced command en `authorized_keys`:

```
command="bash /home/ubuntu/qa-portfolio-server/deploy/logs.sh",restrict ssh-ed25519 AAAA... claude-logs-readonly
```

Cómo funciona la restricción: con esa clave no se obtiene una shell. El servidor ignora el comando que pida el cliente y ejecuta siempre `logs.sh`, que recibe lo pedido como **texto** en `$SSH_ORIGINAL_COMMAND` y lo valida contra una lista cerrada:

| Comando | Qué ejecuta |
|---|---|
| `help` | lista los comandos |
| `status` | `docker compose ps`, `uptime`, `df -h /`, `free -h` |
| `app [N]` / `certbot [N]` | `docker compose logs --tail N <servicio>` |
| `nginx [N]` | igual, con el último octeto de cada IPv4 enmascarado (las IPs de visitantes son datos personales) |
| `unit [N]` | `journalctl -u qa-portfolio.service -n N` |

`N` es un entero de 1 a 500 (por defecto 200). Cualquier otra cosa se rechaza con exit 2: no hay rutas, opciones ni encadenado posible. Los logs de PostgreSQL **no se exponen a propósito**, porque pueden incluir datos de consultas.

Verificado antes de desplegar con 13 intentos hostiles (`app; id`, `app $(id)`, `cat /etc/passwd`, `app 9999`, `postgres`, etc.): todos rechazados.

```bash
# Ejemplos, desde la PC (clave de solo lectura, nunca la de deploy)
ssh -i ~/.ssh/qa_portfolio_logs ubuntu@<IP> status
ssh -i ~/.ssh/qa_portfolio_logs ubuntu@<IP> app 100
```

Limitación conocida: el usuario `ubuntu` pertenece al grupo `docker`, lo que equivale a privilegios de root en esa máquina. La seguridad de esta clave **depende por completo de que `logs.sh` no pueda ser manipulado** por quien la use (por eso es de solo lectura sobre el repositorio y no acepta argumentos libres) y de que nadie con acceso de escritura a `main` lo modifique sin revisión.

## Notas de troubleshooting

**El plugin `docker compose` puede no verse para `root`/`systemd` aunque funcione para tu usuario.** Si `docker compose version` funciona como `ubuntu` pero `sudo docker compose version` dice `'compose' is not a docker command`, es porque el plugin quedó instalado solo en `~/.docker/cli-plugins/docker-compose` (instalación por-usuario). Solución: copiarlo a una ruta de plugins a nivel de sistema, por ejemplo:

```bash
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo cp ~/.docker/cli-plugins/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
```

**Firewall en dos capas independientes.** Abrir un puerto nuevo requiere tocar la Security List de Oracle Cloud (consola web) **y** el iptables local del servidor (`sudo iptables -I INPUT <línea-antes-del-REJECT> ...` + `sudo netfilter-persistent save` para que sobreviva un reinicio) — agregar solo una de las dos no alcanza.

**Nginx cachea la IP del upstream — un `app` recreado sin reiniciar `nginx` da 502.** `proxy_pass http://app:8000` con una URL literal resuelve el hostname `app` **una sola vez**, cuando Nginx arranca, y cachea esa IP interna de Docker para siempre. Cuando `app` se recrea (`docker compose up -d --build` después de un cambio en `app/`), le toca una IP nueva — Nginx sigue mandando tráfico a la vieja y todo responde `502 Bad Gateway`, aunque `app` esté sano. Solución permanente aplicada en `nginx.conf`: `resolver 127.0.0.11 valid=10s;` (el DNS interno de Docker) + `proxy_pass` a una **variable** (`set $upstream_app app:8000; proxy_pass http://$upstream_app;`) en vez de una URL literal — así Nginx re-resuelve el hostname en cada request en vez de cachearlo para siempre. Aun así, conviene `docker compose restart nginx` después de cada deploy que recree `app`, por las dudas.

**SQLAlchemy se queda con conexiones muertas si Postgres se reinicia.** Si el contenedor `postgres` se recrea (por ejemplo, al agregarle el healthcheck) mientras `app` sigue corriendo sin reiniciarse, el pool de conexiones de SQLAlchemy queda con conexiones hacia un Postgres que ya no existe. El próximo query revienta con `OperationalError: server closed the connection unexpectedly` en vez de reconectar solo. Solución: `SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}` en `app.py` — antes de usar una conexión del pool, la prueba con un `SELECT 1` liviano y la descarta/reemplaza si está muerta.

**Al copiar un secreto a `.env`, no incluyas los `<` `>` de un placeholder tipo `VALOR=<pega-tu-valor-acá>`.** Esos símbolos son notación para decir "reemplazá esto", no parte del valor — si quedan en el archivo, terminan siendo parte literal del secreto (`SECRET_KEY=<64dc157...>` en vez de `SECRET_KEY=64dc157...`). No rompe nada (sigue siendo un string válido y suficientemente aleatorio), pero es prolijo evitarlo. Verificar siempre con `cat .env` después de editarlo.

**Cambiar un valor en `.env` no siempre alcanza con `docker compose up -d` — a veces hace falta `--force-recreate`.** Compose decide si recrea un contenedor comparando el hash de su configuración ya resuelta (con las variables de `.env` interpoladas); normalmente si el valor efectivo cambió, sí lo detecta y recrea solo. Si hay dudas de que un contenedor tomó un `.env` actualizado, confirmar con la fuente de verdad real — no el archivo, el proceso corriendo: `docker compose exec <servicio> printenv <VARIABLE>`.
