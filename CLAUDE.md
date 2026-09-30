# CLAUDE.md — qa-portfolio-server

Instrucciones permanentes para trabajar en este repo. Arquitectura estable, convenciones y reglas duras — lo que no cambia de sesión a sesión.

> **Para estado actual, pendientes y "qué estábamos haciendo antes de esto"** → ver [`CONTEXT.md`](CONTEXT.md).
> **Datos de conexión al servidor (IP, usuario, ruta de la clave SSH)** → ver `SERVER_INFO.local.md`, gitignorado, nunca se commitea.

---

## Descripción del proyecto

Servidor y portafolio web personal de Andres Gonzalez (QE en FLYR), semanas 8-14 de un plan de estudio de 14 semanas más amplio (Claude IA + QE Automation). Continúa a [`qa-automation-portfolio`](../qa-automation-portfolio) (semanas 4-7, repo separado): ese repo demuestra el stack de testing (UI+API+CI+Docker+BDD); este proyecto aloja el sitio web que presenta todo eso, con backend propio, panel admin y demos de IA en vivo.

Corre sobre una instancia **Oracle Cloud Always Free** (Ubuntu 20.04 LTS, ARM/aarch64, 4 cores, 24GB RAM, 200GB — de los cuales ~191GB libres) que Andres ya tenía provisionada (usada antes para un servidor de Palworld, completamente dado de baja y libre para este proyecto).

---

## Decisión de arquitectura: todo dockerizado

Nginx, la app Flask/Gunicorn y PostgreSQL corren como **contenedores Docker** (`docker-compose`), con un systemd unit simple que levanta el compose al boot del servidor — no una instalación nativa de Nginx/Python/Gunicorn en el SO.

**Por qué:** el objetivo de este proyecto es un portafolio de **QA Automation/SDET**, no una vacante de SysAdmin/DevOps. La propia tabla de prioridades de mercado del plan de estudio pone a Docker como prioridad explícita (#3, impacto "Medio-Alto"), mientras que administrar Nginx/systemd nativo no aparece como habilidad de mercado buscada para este rol — es infraestructura de soporte para alojar el sitio, no algo que un entrevistador QA vaya a auditar en detalle. Dockerizar todo además reutiliza directamente lo aprendido en la semana 7 de `qa-automation-portfolio` (misma habilidad, refuerza la narrativa de entrevista) y es más simple de mantener en un server ARM recién limpiado que compilar/instalar dependencias nativas de Python 3.13 + Nginx a mano.

**Lo que esto NO evita:** SSH, la Security List de Oracle Cloud y el iptables local del servidor se configuran igual, con o sin Docker — esa parte de "administración de servidor" sigue siendo real.

---

## Arquitectura del servidor

Dos capas de firewall **independientes**, hay que tocar ambas para exponer cualquier puerto nuevo:

1. **Oracle Cloud Security List** — firewall de nube, se edita desde la consola web de OCI (Networking → VCN → Security Lists).
2. **iptables local** — en el SO. `ufw` está `inactive`; las reglas viven directas en iptables (`INPUT` chain). Verificar con `sudo iptables -L -n -v`.

Estado inicial (antes de este proyecto): ambas capas solo permitían `22/tcp` (SSH) y `8211/udp` (Palworld, sin uso — candidato a limpiar).

```
Nginx (contenedor, proxy + SSL)
  → Gunicorn (contenedor, WSGI)
    → Flask (app Python, contenedor)
      → PostgreSQL (contenedor, con volumen para persistencia)

SSL: Let's Encrypt vía Certbot (requiere dominio, no IP — ver DuckDNS)
Deploy: deploy/deploy.sh (git pull --ff-only + docker compose up -d --build + restart nginx), disparado por
        GitHub Actions (.github/workflows/deploy.yml) en cada push a main, vía SSH con clave dedicada
        restringida por forced command — NO vía Routine de Claude (decisión de seguridad, ver README)
```

---

## Automatización externa: Routines de Claude Code (semana 11)

Dos "routines" (agentes de Claude Code programados en la nube, independientes de esta sesión) vigilan `qa-automation-portfolio` — no viven en ningún repo, se administran desde `claude.ai/code/routines` o la herramienta `RemoteTrigger`:

1. **`trig_018RKk64jV8zHmsMQtNvq1ZB`** — chequeo nocturno de CI, **funcionando**. Corre todas las noches a las 11pm hora Bogotá (`0 4 * * *` UTC), reporta el estado del run más reciente de `qa-automation-portfolio` a Slack (`#ci-alerts`), y solo profundiza en tests específicos (bajando logs de GitHub) si hubo actividad nueva en las últimas 24-48hs.
2. **`trig_0142zKmhVNHWazPjBgrVPpfi`** — review automático de PRs con checklist QA, **funcionando vía cron horario** (`33 * * * *`). Busca PRs abiertos, revisa el diff contra `CLAUDE.md` de `qa-automation-portfolio` y comenta con la herramienta MCP `mcp__github__add_issue_comment` (verificado con un PR real). No duplica: si ya comentó el mismo head sha, no vuelve a comentar. También tiene un `create_webhook_trigger` enganchado a `pull_request` (requirió la GitHub App "Claude"), pero **el webhook nunca disparó** (4 eventos reales probados) — se deja enganchado por si la plataforma lo arregla; el cron es el mecanismo real. Detalle en `CONTEXT.md`, sección 4 (semana 11).

**Notas técnicas sobre `RemoteTrigger` que no están en la documentación del skill `/schedule`:**
- El sandbox de las routines tiene un proxy de salida que bloquea conexiones directas a dominios externos (confirmado con `hooks.slack.com` y con el blob storage de logs de GitHub) — cualquier integración externa debe pasar por un conector MCP adjunto a la routine (`mcp_connections`), no por `curl` directo.
- El nombre de una herramienta MCP dentro de una routine usa el campo `name` del conector (ej. `mcp__Slack__slack_send_message`), no el `connector_uuid` como en una sesión normal de Claude Code — hay que buscarlo con `ToolSearch` dentro de la propia routine si no se sabe de antemano.
- Lectura por `curl` a `api.github.com` SÍ funciona desde el sandbox (lo bloqueado es `hooks.slack.com` y el blob storage de logs). Escribir en GitHub (comentarios) requiere la herramienta MCP de GitHub (`mcp__github__*`), que el sandbox trae disponible — no `curl` anónimo ni `gh` (no autenticado).
- `create_webhook_trigger` (acción de `RemoteTrigger`) no está documentada más allá de una línea en el skill — el schema real (`hook_type`, `source`, `scope_id`, `events`) se descubrió a prueba y error. `hook_type: "app"` requiere la GitHub App "Claude" instalada en el repo de destino.

---

## Reglas importantes que debemos respetar

1. **`SERVER_INFO.local.md` nunca se commitea.** Contiene IP pública, usuario SSH y ruta a la clave privada — está en `.gitignore` desde el commit inicial. El repo es **público en GitHub** (`github.com/anfelgonta201514/qa-portfolio-server`) desde el 2026-09-29 — esto es lo único que lo comprometería si se filtrara.
2. **Nunca pegar el contenido de la clave privada (`.key`/`.pem`) en ningún archivo de este repo**, ni siquiera temporalmente. Se referencia solo por ruta.
3. **Cualquier cambio de firewall (Security List de Oracle o iptables local) se avisa y confirma antes de aplicarse** — es un servidor real, un error de firewall puede cortar el propio acceso SSH. Antes de tocar reglas, siempre `sudo iptables -L -n -v` o revisar la Security List actual primero (no asumir el estado).
4. **Nunca mezclar nada del entorno de trabajo privado de Andres (SunExpress UAT / FLYR)** en este repo, igual que en `qa-automation-portfolio`.
5. **Claude no hace `git commit`/`git push` ni ejecuta comandos con efecto real en el servidor (cambios de firewall, instalar paquetes, levantar/bajar contenedores) sin que Andres lo confirme explícitamente para ese caso puntual.** Los comandos de solo lectura (verificar estado, `docker ps`, `iptables -L`, etc.) no necesitan confirmación previa.
6. **`docker-compose.yml` y cualquier archivo de config versionado nunca lleva secretos en texto plano** (contraseñas de Postgres, `ANTHROPIC_API_KEY`, `SECRET_KEY` de Flask, credenciales de admin) — van en variables de entorno cargadas desde un `.env` gitignorado en el servidor, nunca committeadas. El repo es público: el código puede verse, los secretos nunca.
7. **Los commits de este repo NO llevan trailer `Co-Authored-By: Claude`** — mismo motivo y mismo criterio que `qa-automation-portfolio` (repo hermano del mismo portafolio público): el autor real es Andres, la línea solo generaba confusión en el listado de Contributors de GitHub.

---

## Otras instrucciones permanentes

- Este proyecto es la implementación de las **semanas 8-14** de un plan de estudio de 14 semanas más amplio (Claude IA + QE Automation). El contexto de quién es Andres, su nivel y las reglas de evaluación semanal viven en la memoria de Claude Code — si se retoma este proyecto sin esa memoria, no asumir el rol de "profesor de plan de estudio" solo a partir de este archivo.
- Nivel de Andres en administración Linux (declarado semana 8): conoce lo básico de SSH/terminal; nunca configuró Nginx/systemd/iptables "en serio" antes de este proyecto, pero sí administró un servidor de Palworld en esta misma instancia por 2+ meses (maneja el concepto de mantener un proceso vivo en un server remoto).
- Cada entregable nuevo debe quedar documentado en el `README.md` del proyecto — mismo hábito que `qa-automation-portfolio`.
