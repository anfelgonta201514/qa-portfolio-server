#!/usr/bin/env bash
# Deploy del stack en el servidor. Lo ejecuta el workflow de GitHub Actions
# (.github/workflows/deploy.yml) vía SSH, pero NO porque el workflow mande
# este comando: la clave de deploy está registrada en ~/.ssh/authorized_keys
# con command="bash /home/ubuntu/qa-portfolio-server/deploy/deploy.sh", así
# que esa clave SOLO puede correr este script — cualquier otro comando que
# se le pase por SSH se ignora. Si la clave se filtra, lo peor que se puede
# hacer con ella es redeployar lo que ya está en main.
#
# También sirve para deployar a mano desde el propio servidor:
#   bash ~/qa-portfolio-server/deploy/deploy.sh
set -euo pipefail

cd /home/ubuntu/qa-portfolio-server

echo "==> git pull (solo fast-forward: si alguien tocó archivos versionados a mano en el server, falla en vez de pisar nada)"
git pull --ff-only

echo "==> docker compose up -d --build"
docker compose up -d --build

# Ver README, troubleshooting: nginx puede quedarse con la IP vieja de "app"
# si este deploy la recreó. Reiniciarlo siempre es seguro y tarda < 1s.
echo "==> docker compose restart nginx"
docker compose restart nginx

echo "==> deploy OK: $(git log -1 --format='%h %s')"
