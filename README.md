# qa-portfolio-server

Servidor y portafolio web personal de Andres Gonzalez — semanas 8-14 de un plan de estudio de 14 semanas más amplio (Claude IA + QE Automation). Continúa a [`qa-automation-portfolio`](../qa-automation-portfolio) (semanas 4-7): ese repo demuestra el stack de testing, este aloja el sitio que lo presenta.

Corre sobre una instancia Oracle Cloud Always Free (Ubuntu 20.04 LTS, ARM/aarch64).

## Arquitectura

Todo dockerizado — ver `CLAUDE.md` para el porqué de esta decisión.

```
Nginx (contenedor, proxy inverso)
  → Gunicorn (contenedor, WSGI)
    → Flask (app Python)

systemd (qa-portfolio.service) → docker compose up -d al boot del servidor
```

## Estructura

```
qa-portfolio-server/
├── app/
│   ├── app.py           → app Flask (hoy: hello world; semana 9 en adelante: app real)
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/
│   └── nginx.conf       → reverse proxy hacia el servicio `app`
├── docker-compose.yml   → orquesta app + nginx
├── deploy/
│   └── qa-portfolio.service → systemd unit, instalado en /etc/systemd/system/ del servidor
└── SERVER_INFO.local.md → datos de conexión reales, gitignorado, NUNCA se commitea
```

## Estado

✅ **Hello world funcionando end-to-end**: Flask + Gunicorn detrás de Nginx, servido desde el servidor real vía HTTP (puerto 80), con las dos capas de firewall (Security List de Oracle Cloud + iptables local) abiertas y verificadas. systemd levanta el stack automáticamente al boot.

Pendiente: HTTPS (necesita un dominio — Let's Encrypt no funciona solo con IP), deploy vía `git pull` en vez de copia manual, backend real con PostgreSQL (semana 9).

## Cómo desplegar (hoy, manual vía git)

El servidor tiene un `git clone` de este mismo repo en `~/qa-portfolio-server` (público, no necesita credenciales). Para desplegar un cambio:

```bash
ssh -i <clave> ubuntu@<IP> "cd ~/qa-portfolio-server && git pull && docker compose up -d --build"
```

(Automatizar este paso vía Routine de Claude Code queda para la semana 11 del plan.)

## Notas de troubleshooting

**El plugin `docker compose` puede no verse para `root`/`systemd` aunque funcione para tu usuario.** Si `docker compose version` funciona como `ubuntu` pero `sudo docker compose version` dice `'compose' is not a docker command`, es porque el plugin quedó instalado solo en `~/.docker/cli-plugins/docker-compose` (instalación por-usuario). Solución: copiarlo a una ruta de plugins a nivel de sistema, por ejemplo:

```bash
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo cp ~/.docker/cli-plugins/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
```

**Firewall en dos capas independientes.** Abrir un puerto nuevo requiere tocar la Security List de Oracle Cloud (consola web) **y** el iptables local del servidor (`sudo iptables -I INPUT <línea-antes-del-REJECT> ...` + `sudo netfilter-persistent save` para que sobreviva un reinicio) — agregar solo una de las dos no alcanza.
