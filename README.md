# qa-portfolio-server

Servidor y portafolio web personal de Andres Gonzalez — semanas 8-14 de un plan de estudio de 14 semanas más amplio (Claude IA + QE Automation). Continúa a [`qa-automation-portfolio`](../qa-automation-portfolio) (semanas 4-7): ese repo demuestra el stack de testing, este aloja el sitio que lo presenta.

Corre sobre una instancia Oracle Cloud Always Free (Ubuntu 20.04 LTS, ARM/aarch64).

## Arquitectura

Todo dockerizado — ver `CLAUDE.md` para el porqué de esta decisión.

```
Nginx (contenedor, proxy inverso, resolución dinámica de upstream)
  → Gunicorn (contenedor, WSGI)
    → Flask (app Python, API REST de solo lectura)
      → PostgreSQL (contenedor, volumen persistente)

systemd (qa-portfolio.service) → docker compose up -d al boot del servidor
```

## Estructura

```
qa-portfolio-server/
├── app/
│   ├── app.py           → app Flask: hello world + API REST (/api/projects, solo lectura)
│   ├── models.py        → modelo SQLAlchemy Project
│   ├── seed.py           → inserta un proyecto de ejemplo (idempotente)
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/
│   └── nginx.conf       → reverse proxy hacia `app`, con resolver dinámico (ver troubleshooting)
├── docker-compose.yml   → orquesta app + nginx + postgres
├── .env.example          → plantilla de variables (copiar a .env, nunca commitear el real)
├── deploy/
│   └── qa-portfolio.service → systemd unit, instalado en /etc/systemd/system/ del servidor
└── SERVER_INFO.local.md → datos de conexión reales, gitignorado, NUNCA se commitea
```

## Estado

✅ **Backend con Postgres funcionando end-to-end**: Nginx → Gunicorn → Flask → PostgreSQL, servido desde el servidor real (puerto 80), con las dos capas de firewall abiertas y verificadas, `GET /api/projects` devolviendo datos reales desde la base. systemd levanta todo el stack al boot. Deploy vía `git pull` (no copia manual).

Endpoints de escritura (POST/PUT/DELETE) **a propósito no están implementados todavía** — el server es público y no hay autenticación hasta el panel admin (Flask-Login, semana 10).

Pendiente: HTTPS (necesita un dominio — Let's Encrypt no funciona solo con IP), panel admin + auth (semana 10), migraciones con Flask-Migrate/Alembic (hoy usa `db.create_all()`, suficiente mientras el schema sea trivial).

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
