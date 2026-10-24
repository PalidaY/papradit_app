#!/bin/sh
set -eu
# Existing isolated checkout; no worktree and no reset/clean of user work.
cd /workspace/papradit_app
export DOCKER_CONFIG=/workspace/.docker
mkdir -p "$DOCKER_CONFIG"
if [ ! -f .env ]; then
  python - <<'PY'
from pathlib import Path
import secrets
p=Path('.env')
with p.open('x') as f:
    f.write('DJANGO_SECRET_KEY='+secrets.token_urlsafe(48)+'\n')
    f.write('POSTGRES_PASSWORD='+secrets.token_urlsafe(32)+'\n')
    f.write('POSTGRES_DB=papradit\nPOSTGRES_USER=papradit\nDJANGO_DEBUG=1\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\nPUBLIC_BASE_URL=http://localhost:8000\nEMAIL_BACKEND=django.core.mail.backends.filebased.EmailBackend\n')
p.chmod(0o600)
PY
fi
if [ -n "${HTTPS_PROXY:-}" ] && getent ahostsv4 proxy >/dev/null 2>&1; then
  papradit_proxy_ip=$(getent ahostsv4 proxy | awk 'NR==1{print $1}')
  docker build --target development --add-host "proxy:$papradit_proxy_ip" \
    --secret id=ca,src=/etc/ssl/certs/ca-certificates.crt \
    --build-arg HTTPS_PROXY --build-arg HTTP_PROXY --build-arg NO_PROXY \
    -t papradit-app:local .
else
  docker compose build
fi
docker compose up -d --wait db
docker compose run --rm app python manage.py migrate --noinput
docker compose run --rm app python -m pip check
docker compose run --rm app python manage.py check
docker compose run --rm app python manage.py makemigrations --check --dry-run
