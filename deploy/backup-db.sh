#!/usr/bin/env bash
# Backup de la base PostgreSQL del portafolio (semana 14).
#
# Lo ejecuta el timer de systemd deploy/qa-portfolio-backup.timer una vez al día, pero también se puede correr a
# mano desde el servidor:   bash ~/qa-portfolio-server/deploy/backup-db.sh
#
# Qué hace:
#   1. pg_dump dentro del contenedor `postgres` (las credenciales ya están en el entorno del contenedor: este script
#      no lee ni contiene ningún secreto), comprimido con gzip.
#   2. Escribe a un archivo temporal y solo lo renombra si pasa las comprobaciones (gzip íntegro, tamaño mínimo y el
#      pie que pg_dump escribe al terminar). Un backup a medias nunca ocupa el lugar de uno bueno.
#   3. Rotación: 7 copias diarias; los domingos además se guarda una semanal (se conservan 4).
#
# Variables opcionales: BACKUP_DIR (por defecto /home/ubuntu/backups), KEEP_DAILY (7), KEEP_WEEKLY (4).
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/ubuntu/qa-portfolio-server}"
BACKUP_DIR="${BACKUP_DIR:-/home/ubuntu/backups}"
KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"
MIN_BYTES=200

umask 077
cd "$REPO_DIR"
mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly"

stamp="$(date -u +%Y%m%d-%H%M%SZ)"
final="$BACKUP_DIR/daily/db-$stamp.sql.gz"
partial="$final.partial"
trap 'rm -f "$partial"' EXIT

echo "==> pg_dump -> $final"
# -T: sin TTY (necesario fuera de una terminal). Las variables $POSTGRES_* las expande el shell DEL CONTENEDOR.
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip -9 > "$partial"

echo "==> comprobando el backup"
gzip -t "$partial"
size="$(stat -c %s "$partial")"
(( size >= MIN_BYTES )) || { echo "backup-db.sh: el archivo pesa $size bytes, demasiado poco" >&2; exit 1; }
# El pie de pg_dump va seguido de unas pocas líneas (hoy "--", una vacía, "\unrestrict <token>" y otra vacía) y las
# versiones nuevas de pg_dump pueden añadir más: se miran las últimas 20 para no dar por "cortado" un dump bueno.
zcat "$partial" | tail -n 20 | grep -q "PostgreSQL database dump complete" \
  || { echo "backup-db.sh: el dump no termina con su pie esperado (cortado)" >&2; exit 1; }

mv "$partial" "$final"
trap - EXIT

# Domingo (date +%u == 7): copia semanal.
if [ "$(date -u +%u)" = "7" ]; then
  cp "$final" "$BACKUP_DIR/weekly/"
fi

# Rotación: se borra lo que sobra pasadas las N más recientes de cada carpeta.
rotate() {
  local dir="$1" keep="$2"
  # `|| true`: con la carpeta vacía (p. ej. weekly/ de lunes a sábado) `ls` devuelve 2 y, con pipefail, abortaría el
  # script ya terminado el backup. shellcheck disable=SC2012: nombres controlados por este script (db-<fecha>.sql.gz).
  { ls -1t "$dir"/db-*.sql.gz 2>/dev/null || true; } | tail -n +"$((keep + 1))" | while read -r old; do
    echo "==> borrando copia antigua: $old"
    rm -f -- "$old"
  done
}
rotate "$BACKUP_DIR/daily" "$KEEP_DAILY"
rotate "$BACKUP_DIR/weekly" "$KEEP_WEEKLY"

echo "==> backup OK: $final ($size bytes)"
