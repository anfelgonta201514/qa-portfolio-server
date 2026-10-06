#!/usr/bin/env bash
# Lectura de logs del servidor, de SOLO LECTURA y con lista cerrada de comandos.
#
# Se usa con una clave SSH dedicada registrada en ~/.ssh/authorized_keys con
#   command="bash /home/ubuntu/qa-portfolio-server/deploy/logs.sh",restrict
# Con eso, quien se conecte con esa clave NO obtiene una shell ni puede correr
# nada distinto: el servidor ignora el comando pedido, ejecuta este script, y el
# comando que el cliente pidió llega en $SSH_ORIGINAL_COMMAND como simple texto
# que este script valida contra la lista de abajo. Todo lo que no esté en la lista
# se rechaza. No hay forma de pasar rutas, opciones ni encadenar comandos.
#
# Uso desde el cliente (ejemplos):
#   ssh -i <clave> ubuntu@<IP> help
#   ssh -i <clave> ubuntu@<IP> status
#   ssh -i <clave> ubuntu@<IP> app 200
set -euo pipefail

MAX_LINES=500
DEFAULT_LINES=200

refuse() {
  echo "logs.sh: $1" >&2
  echo "Comandos permitidos: help | status | app [N] | nginx [N] | certbot [N] | unit [N]  (N = 1-$MAX_LINES)" >&2
  exit 2
}

# El comando llega como texto; se separa por espacios sin interpretarlo nunca.
read -r cmd lines extra <<<"${SSH_ORIGINAL_COMMAND:-help}"

[ -z "${extra:-}" ] || refuse "demasiados argumentos"

lines="${lines:-$DEFAULT_LINES}"
[[ "$lines" =~ ^[0-9]{1,3}$ ]] || refuse "N debe ser un número entero"
(( lines >= 1 && lines <= MAX_LINES )) || refuse "N fuera de rango"

case "${cmd:-help}" in
  help|status|app|nginx|certbot|unit) ;;
  *) refuse "comando no permitido: ${cmd:-}" ;;
esac

cd /home/ubuntu/qa-portfolio-server

case "${cmd:-help}" in
  help)
    echo "Comandos permitidos (solo lectura):"
    echo "  status        estado de los contenedores, uptime, disco y memoria"
    echo "  app [N]       últimas N líneas de logs de la app Flask/Gunicorn"
    echo "  nginx [N]     últimas N líneas de logs de Nginx (IPs de visitantes enmascaradas)"
    echo "  certbot [N]   últimas N líneas de logs de renovación de certificados"
    echo "  unit [N]      últimas N líneas del unit de systemd qa-portfolio"
    echo "No se exponen los logs de PostgreSQL a propósito: pueden contener datos de consultas."
    ;;
  status)
    echo "== contenedores =="; docker compose ps
    echo "== uptime ==";       uptime
    echo "== disco ==";        df -h /
    echo "== memoria ==";      free -h
    ;;
  app|certbot)
    docker compose logs --no-color --timestamps --tail "$lines" "$cmd"
    ;;
  nginx)
    # Enmascara el último octeto de cada IPv4 (las IPs de visitantes son datos
    # personales y el análisis no las necesita).
    docker compose logs --no-color --timestamps --tail "$lines" nginx \
      | sed -E 's/([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})\.[0-9]{1,3}/\1.x/g'
    ;;
  unit)
    journalctl -u qa-portfolio.service --no-pager -n "$lines"
    ;;
esac
