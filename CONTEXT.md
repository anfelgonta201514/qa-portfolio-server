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

### ❌ Todavía no empezado
- Limpiar o dejar la regla de firewall de `8211/udp` (Palworld) — sin uso, no bloqueante, decidir cuándo se toquen las reglas de firewall.
- El proyecto vive en el servidor como una copia manual (`scp`), no como un `git clone`/`git pull` — el flujo de deploy vía git (mencionado en `CLAUDE.md` y en el plan, semana 11) todavía no está armado. Por ahora, cualquier cambio futuro se vuelve a copiar a mano.
- Validar el systemd unit con un reinicio real del servidor (opcional, decisión de Andres — es una acción con impacto real en un server que ya tiene el hello world corriendo).
- Semanas 9-14: fuera de alcance por ahora (backend real con Postgres, frontend, Routines, Cowork/MCP, demos IA, lanzamiento) — ver el plan completo en `C:\Users\andre\Documents\proyecto_claude\plan-estudio-andres-qe-ia-contexto-v2.md`.

**✅ Hito: la semana 8 del plan (SSH, puertos OCI + iptables, Nginx, Gunicorn/Python, systemd service) queda funcionalmente completa** — la única diferencia con el plan original es que todo corre dockerizado en vez de nativo (decisión tomada con Andres, ver sección de arquitectura en `CLAUDE.md`).

---

## 3. PENDIENTES INMEDIATOS (semana 8)

- [x] Abrir `80/443 tcp` en iptables local — **hecho 2026-09-18**, persistido en `/etc/iptables/rules.v4`.
- [x] Abrir `80/443 tcp` en la **Security List de Oracle Cloud** — **hecho 2026-09-29**, verificado con `curl` externo ("Connection refused" en ambos puertos, confirma las dos capas de firewall abiertas).
- [x] Instalar/verificar Docker Compose en el servidor — **hecho 2026-09-29**, ya venía con la instalación de Docker.
- [x] Armar un `docker-compose.yml` inicial con un servicio "hello world" — **hecho 2026-09-29**, Flask + Gunicorn detrás de Nginx, verificado con `curl` externo (`200 OK`).
- [x] Escribir y activar el systemd unit — **hecho 2026-09-29**, `enabled` + `active (exited)`, con el fix del plugin de Compose instalado a nivel de sistema.
- [ ] (Opcional) Validar el systemd unit con un reinicio real del servidor.
- [ ] Evaluar si limpiar la regla de `8211/udp` (Palworld) ahora o dejarla (no genera riesgo real, solo ruido).
- [ ] Armar el deploy vía git (`git clone`/`git pull` en el server) en vez de `scp` manual — no bloqueante para cerrar la semana 8, pero hace falta antes de automatizar el deploy en semana 11.
- [ ] Cuando llegue el momento de HTTPS: registrar un dominio gratuito (DuckDNS, mencionado en el plan) — Let's Encrypt/Certbot no funciona solo con IP.

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

**Con esto, la semana 8 queda funcionalmente cerrada** (ver hito en sección 2). Pendientes menores no bloqueantes: validar con un reinicio real (opcional), decidir sobre la regla de Palworld, y armar deploy vía git en vez de `scp` manual.

**Siguiente paso recomendado:** preguntarle a Andres si quiere (a) seguir directo a la semana 9 (backend real: PostgreSQL + Flask-SQLAlchemy + dominio/SSL), (b) cerrar primero los pendientes menores de arriba, o (c) pausar acá. Mismo patrón de preguntar antes de asumir que se usó en toda la sesión.
