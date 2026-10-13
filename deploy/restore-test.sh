#!/usr/bin/env bash
# Prueba de restauración: demuestra que un backup SIRVE restaurándolo en una base TEMPORAL.
#
#   bash ~/qa-portfolio-server/deploy/restore-test.sh [archivo.sql.gz]
#
# Sin argumento usa el backup diario más reciente. NUNCA toca la base real: crea una base con otro nombre
# (restore_check_<fecha>), carga el dump allí, cuenta las tablas y las filas de `project`, y la borra al terminar
# (también si algo falla). Para restaurar de verdad en una emergencia ver el README, "Backup de PostgreSQL".
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/ubuntu/qa-portfolio-server}"
BACKUP_DIR="${BACKUP_DIR:-/home/ubuntu/backups}"
cd "$REPO_DIR"

file="${1:-}"
if [ -z "$file" ]; then
  # shellcheck disable=SC2012
  file="$(ls -1t "$BACKUP_DIR"/daily/db-*.sql.gz 2>/dev/null | head -n 1 || true)"
fi
[ -n "$file" ] && [ -f "$file" ] || { echo "restore-test.sh: no hay backup que probar" >&2; exit 1; }

tmpdb="restore_check_$(date -u +%Y%m%d%H%M%S)"
echo "==> backup: $file"
echo "==> base temporal: $tmpdb"

# Todo el trabajo ocurre dentro del contenedor, con las credenciales de su propio entorno.
psql_admin() { docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres "$@"' sh "$@"; }
psql_tmp()   { docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$0" "$@"' "$tmpdb" "$@"; }

cleanup() { psql_admin -c "DROP DATABASE IF EXISTS \"$tmpdb\"" >/dev/null 2>&1 || true; }
trap cleanup EXIT

# Nunca debería coincidir con la base real, pero se comprueba igual antes de crear nada.
real="$(docker compose exec -T postgres sh -c 'printf %s "$POSTGRES_DB"')"
[ "$tmpdb" != "$real" ] || { echo "restore-test.sh: el nombre temporal coincide con la base real" >&2; exit 1; }

psql_admin -c "CREATE DATABASE \"$tmpdb\"" >/dev/null
zcat "$file" | psql_tmp -q >/dev/null

tables="$(psql_tmp -t -A -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")"
echo "==> tablas restauradas: $tables"
(( tables >= 1 )) || { echo "restore-test.sh: la restauración no creó ninguna tabla" >&2; exit 1; }

for t in $(psql_tmp -t -A -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1"); do
  echo "    $t: $(psql_tmp -t -A -c "SELECT count(*) FROM \"$t\"") filas"
done

echo "==> restore-test OK (la base temporal se borra al salir)"
