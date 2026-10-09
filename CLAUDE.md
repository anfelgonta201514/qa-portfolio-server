# CLAUDE.md — qa-portfolio-server

Instrucciones permanentes para trabajar en este repo. Arquitectura estable, convenciones y reglas duras — lo que no cambia de sesión a sesión.

> **Para estado actual, pendientes y "qué estábamos haciendo antes de esto"** → ver [`CONTEXT.md`](CONTEXT.md).
> **Datos de conexión al servidor (IP, usuario, ruta de la clave SSH)** → ver `SERVER_INFO.local.md`, gitignorado, nunca se commitea.

---

## Descripción del proyecto

Servidor y portafolio web personal de Andres Gonzalez (QE en FLYR), semanas 8-14 de un plan de estudio de 14 semanas más amplio (Claude IA + QE Automation). Continúa a [`qa-automation-portfolio`](../qa-automation-portfolio) (semanas 4-7, repo separado): ese repo demuestra el stack de testing (UI+API+CI+Docker+BDD); este proyecto aloja el sitio web que presenta todo eso, con backend propio, panel admin y demos de IA aplicada a QA (multi-proveedor — ver "Enfoque de IA del portafolio" más abajo).

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
6. **`docker-compose.yml` y cualquier archivo de config versionado nunca lleva secretos en texto plano** (contraseñas de Postgres, claves de API de los proveedores de IA, `SECRET_KEY` de Flask, credenciales de admin) — van en variables de entorno cargadas desde un `.env` gitignorado en el servidor, nunca committeadas. El repo es público: el código puede verse, los secretos nunca.
7. **Los commits de este repo NO llevan trailer `Co-Authored-By: Claude`** — mismo motivo y mismo criterio que `qa-automation-portfolio` (repo hermano del mismo portafolio público): el autor real es Andres, la línea solo generaba confusión en el listado de Contributors de GitHub.
8. **Las claves de API (de prueba o del servidor) nunca se piden ni se pegan en el chat.** Andres las lee con `Read-Host` en su propia sesión. La clave de pruebas locales y la del servidor son **distintas**, y la de pruebas se borra de la consola al terminar.

---

## Enfoque de IA del portafolio (decisión de Andres, 2026-10-07)

El portafolio se enfoca en el **uso de IA aplicada a QA, no en una sola marca de IA**: Andres usa Claude para unas tareas y otras herramientas para otras, y eso es lo que el sitio debe mostrar. El nombre del plan de estudio ("Claude IA + QE Automation") se conserva tal cual, pero el producto público no se "casa" con un proveedor.

Reglas que se derivan de eso (no negociables sin hablarlo con Andres):
1. **Cada demo declara con verdad qué modelo/proveedor lo genera.** Nunca se muestra uno como si fuera otro.
2. **Un ejemplo pregenerado nunca se presenta como "en vivo".** Si la respuesta no se generó en ese momento para la entrada del visitante, el sitio lo dice ("ejemplo real generado con ...").
3. **Proveedor intercambiable:** el backend llama a la IA a través de una capa mínima (interfaz común), de modo que cambiar de proveedor o de modelo sea configuración (variables del `.env`), no reescribir demos.
4. **Los planes gratuitos tienen límites y condiciones que cambian** (cuotas por minuto/día, y algunos usan los datos de entrada para mejorar sus modelos). Antes de elegir un proveedor se verifican **sus páginas oficiales**, no blogs comparativos. Cada demo con un proveedor externo lleva aviso de "no pegues datos reales ni confidenciales".
5. **Los demos nunca dependen de que el proveedor responda:** si falla o se agota la cuota, se muestra el ejemplo pregenerado (etiquetado), no un error. Aun siendo gratis, hay límite por visitante para que una sola persona no agote la cuota diaria.
6. **Todo texto del sitio, README y documentación evita decir "Claude API" como si fuera el único motor** del portafolio. (Lo que sí es de Claude se dice explícito: p. ej. las routines de Claude Code o los ejemplos generados con Claude.)

---

## Medición de la calidad de los demos de IA (QAP-17)

Reglas para cualquier cambio de prompts, modelo, esfuerzo de razonamiento o limpieza de la salida:
1. **Se mide con la rúbrica** (`docs/rubrica-medicion-ia.md`): primero se puntúa la línea base, después se cambia, y se publica la tabla completa **incluido lo que no mejore o empeore**. Los criterios **no se modifican** tras ver resultados nuevos.
2. **Se declara cuántos cambios se hicieron a la vez** (la mejora no se atribuye a uno solo si fueron varios). Con 6 respuestas y un muestreo, una diferencia de 1 o 2 puntos no es concluyente; lo sólido es lo ejecutado (API real) y lo automático.
3. **La salida del modelo se limpia en código** (`clean_output` en `app/ai_service.py`); pedirlo en el prompt no basta (el modelo usó markdown y guiones raros aunque se le pidió que no).
4. **Una respuesta de IA nunca se presenta como verificada.** El código de tests de API generado no se ejecutó salvo que se haya ejecutado de verdad contra la API real.
5. **`scripts/score_measure.py` ejecuta código generado por un modelo (no confiable):** solo con las 6 entradas propias, solo tras su filtro estático, nunca con entradas de visitantes. El filtro es defensa en profundidad, **no un sandbox**.
6. **Las mediciones con clave real las corre Andres** en su PowerShell, con la clave leída con `Read-Host` (nunca pegada en el chat ni en archivos). Los resultados quedan en `.groq-measure/` (ignorado por git) y Claude los lee desde disco, sin que Andres tenga que copiar nada.

---

## Cómo correr las pruebas

- **No hay venv en el repo.** Crear uno fuera de él: `python -m venv <ruta>` y `<ruta>\Scripts\python -m pip install -r app/requirements.txt pytest requests`.
- Desde la raíz del repo: `python -m pytest app/tests -q -p no:cacheprovider`. Si el intérprete es el venv de `qa-automation-portfolio` (trae los dos plugins de Allure, que chocan), añadir `-p no:allure_pytest -p no:allure_pytest_bdd`.
- **Pruebas opt-in** (se saltan solas; se activan con `-m`, definido en `app/tests/conftest.py`): `-m network` (API real de Restful-booker) y `-m groq_live` (clave real de Groq, **consume cuota**).
- Qué cubre cada archivo de `app/tests/`: `test_ci_status` (badges del CI), `test_demos` (página de demos y su honestidad), `test_ai_limits` (límites, incluida la concurrencia), `test_ai_service` (servicio, configuración, privacidad), `test_groq_provider` (proveedor con HTTP simulado y las dos pruebas reales), `test_output_and_prompts` (limpieza, truncado y reglas de los prompts), `test_score_measure` (el filtro de seguridad del puntuador).
- **Para fiarse de una prueba nueva:** plantar un bug a propósito, ver que falla, y restaurar. **Antes, comprobar el detector con un fallo conocido:** un resultado de "todas las mutaciones sobreviven" o "ninguna sobrevive" es motivo para sospechar del medidor, no de las pruebas.

---

## Jira (proyecto QA Portfolio)

- Sitio `https://andresfelgonta.atlassian.net`, proyecto **`QAP`** (Kanban, sin sprints; la clave antigua `KAN` es un alias). `cloudId` `37c78f1f-4153-45f2-b14f-7196997eed23`, vía el conector oficial de Atlassian.
- Tipos: Epic, Story, Task, Bug, Subtask. **Transiciones: 11 To Do · 21 In Progress · 31 In Review · 41 Done.**
- **Convención:** Claude mueve un ticket a In Progress al empezar y a In Review al terminar, con un comentario que dice qué se hizo, cómo se verificó y **qué NO se verificó**. **Andres decide cuándo pasa a Done.**
- **Leer el estado real antes de afirmarlo**, y las claves antes de citarlas: Jira las asigna en orden de creación y ya hubo dos errores por darlas por sabidas (se creyeron "En revisión" tickets que Andres ya había cerrado, y se intercambiaron QAP-17 y QAP-18).

---

## Lectura de logs del servidor (solo lectura)

Clave `C:\Users\andre\.ssh\qa_portfolio_logs`, atada a `deploy/logs.sh`: `ssh -i <clave> -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes ubuntu@<IP> status|app N|nginx N|certbot N|unit N` (la IP está en `SERVER_INFO.local.md`). No da shell; solo esos comandos. Los logs descargados se borran después de analizarlos. Detalle de diseño y límites en el `README.md`.

---

## Errores de proceso ya cometidos (no repetirlos)

1. **Afirmar de memoria** un estado, un conteo o una clave. Releer siempre con la herramienta (`pytest --collect-only`, JQL, `git status`).
2. **Dar por bueno un conjunto de pruebas simuladas.** 112 pruebas pasaban y el código no funcionaba contra Groq real (Cloudflare bloquea el `User-Agent` por defecto de `urllib`). Las pruebas reales opt-in se hacen pronto y no se omiten.
3. **No propagar nunca el cuerpo de un error externo ocultó la causa** ("HTTP 403" a secas). Se conservan solo identificadores cortos y seguros (`_error_detail`), nunca el texto libre, que podría repetir lo que escribió un visitante.
4. **Entorno Windows:** los scripts con `\u2011` o comillas mezcladas se corrompen si se pasan por heredoc (escribirlos como archivo); la consola cp1252 no imprime ciertos caracteres (`python -I -X utf8`; con `-I` la variable `PYTHONIOENCODING` se ignora); Git Bash convierte rutas como `/api/...` (usar PowerShell o URLs completas); en PowerShell `$home` es de solo lectura.
5. **Un medidor roto parece un resultado.** Un `-q` duplicado ocultó el resumen de pytest y parecía que sobrevivían las 12 mutaciones.

---

## Otras instrucciones permanentes

- Este proyecto es la implementación de las **semanas 8-14** de un plan de estudio de 14 semanas más amplio (Claude IA + QE Automation). El contexto de quién es Andres, su nivel y las reglas de evaluación semanal viven en la memoria de Claude Code y en `C:\Users\andre\Documents\proyecto_claude\plan-estudio-andres-qe-ia-contexto-v2.md` — si se retoma este proyecto sin esa memoria, no asumir el rol de "profesor de plan de estudio" solo a partir de este archivo. (Al 2026-10-09 la carpeta de memoria de este proyecto estaba **vacía**: lo esencial para retomar está en la sección 0 de `CONTEXT.md` y en las notas de memoria creadas ese día.)
- Nivel de Andres en administración Linux (declarado semana 8): conoce lo básico de SSH/terminal; nunca configuró Nginx/systemd/iptables "en serio" antes de este proyecto, pero sí administró un servidor de Palworld en esta misma instancia por 2+ meses (maneja el concepto de mantener un proceso vivo en un server remoto).
- Cada entregable nuevo debe quedar documentado en el `README.md` del proyecto — mismo hábito que `qa-automation-portfolio`.
