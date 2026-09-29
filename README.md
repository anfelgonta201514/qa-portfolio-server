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
│   ├── templates/        → Jinja2: base.html, index.html (público), admin/ (login, dashboard, form)
│   ├── static/style.css
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

✅ **Portafolio completo funcionando end-to-end, con HTTPS real**: frontend público en `https://andresqe.duckdns.org` consumiendo `GET /api/projects` (4 entradas reales de `qa-automation-portfolio`, una por semana 4-7), panel admin (`/admin`) con login real (Flask-Login + contraseña hasheada), CRUD completo de proyectos protegido por sesión, CSRF en los formularios. Certificado de Let's Encrypt con renovación automática verificada. Las dos capas de firewall abiertas y verificadas. systemd levanta todo el stack al boot. Deploy vía `git pull`.

Sección "Demos" en la home: **placeholder a propósito** ("Próximamente") — los demos interactivos reales con la API de Anthropic (generador de test cases, analizador de bugs, generador de suites de API) son contenido de la semana 13, no de la 10; acá solo se dejó el lugar reservado en el frontend.

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

## Panel admin

`/admin/login` — protegido con Flask-Login (contraseña hasheada con Werkzeug, nunca en texto plano) y CSRF en los formularios. Los endpoints de escritura del API (`POST`/`PUT`/`DELETE /api/projects`) requieren la misma sesión.

**Crear o resetear el usuario admin** — interactivo, la contraseña nunca pasa por el chat, un archivo ni un log (usa `getpass`):
```bash
docker compose exec -it app python create_admin.py
```
Correrlo de nuevo con el mismo usuario actualiza su contraseña.

## Cómo desplegar (hoy, manual vía git)

El servidor tiene un `git clone` de este mismo repo en `~/qa-portfolio-server` (público, no necesita credenciales). Para desplegar un cambio:

```bash
ssh -i <clave> ubuntu@<IP> "cd ~/qa-portfolio-server && git pull && docker compose up -d --build && docker compose restart nginx"
```

**El `docker compose restart nginx` del final no es opcional** — ver la nota de "resolución de DNS" en troubleshooting más abajo. Si `app` no se recreó en este deploy (por ejemplo, un cambio que no toca `app/`), se puede omitir; si hay dudas, incluirlo siempre es seguro (nginx tarda menos de un segundo en reiniciar).

(Automatizar este paso vía Routine de Claude Code queda para la semana 11 del plan.)

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
