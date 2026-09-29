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

### ❌ Todavía no empezado
- Validar el systemd unit con un reinicio real del servidor (opcional, decisión de Andres — es una acción con impacto real en un server que ya tiene datos reales en Postgres).
- Automatizar el `git pull` del deploy vía Routine de Claude Code — queda para la semana 11 del plan, no antes.
- Flask-Migrate/Alembic — hoy el schema se crea con `db.create_all()` (simplificación documentada a propósito, ver `app.py`); introducir migraciones de verdad antes de que el schema deje de ser trivial.
- Dominio (DuckDNS) + HTTPS (Let's Encrypt/Certbot) — Andres eligió dejarlo para después de la parte de datos.
- Panel admin + Flask-Login + endpoints de escritura del API — semana 10, junto con insertar en la BD todo lo documentado de `qa-automation-portfolio`.
- Semanas 11-14: fuera de alcance por ahora (Routines, Cowork/MCP, demos IA, lanzamiento) — ver el plan completo en `C:\Users\andre\Documents\proyecto_claude\plan-estudio-andres-qe-ia-contexto-v2.md`.

**✅ Hito: la semana 8 del plan queda funcionalmente completa** (SSH, puertos OCI + iptables, Nginx, Gunicorn/Python, systemd service — todo dockerizado en vez de nativo, decisión tomada con Andres).

**✅ Hito parcial: la semana 9 del plan (PostgreSQL + Flask-SQLAlchemy + API REST) también queda funcionalmente completa.** Falta la parte de dominio/SSL de esa misma semana, dejada para después a pedido de Andres.

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
- [ ] Endpoints de escritura del API (POST/PUT/DELETE) — deliberadamente pospuestos hasta que haya autenticación (semana 10).
- [ ] Flask-Migrate/Alembic — hoy usa `db.create_all()`, simplificación documentada a propósito mientras el schema sea trivial.

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

**Siguiente paso recomendado:** preguntarle a Andres si quiere seguir directo a la **semana 10** (frontend + panel admin + Flask-Login + insertar el resto del contenido real de `qa-automation-portfolio` en la BD) o pausar acá.
