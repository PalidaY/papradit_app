# Papradit & GPT Operations

Thai internal operations app. First release: Admin/auth, product/job/wage catalogues, workers and **รับจ่ายงาน**. Django templates + HTMX + Bootstrap, one PostgreSQL database. Later modules are explicitly unavailable. See [design and scope](docs/design.md), [original requirements](docs/requirements.md), [validation evidence](docs/validation.md), [AWS deployment](docs/deployment.md) and [backup/restore](docs/backup.md).

## Local start

Tested: Docker Engine 28.4.0, Compose **v2.40.3**, Linux x86_64. Container runtime Python **3.13.17** (Debian Trixie), Django **5.2.18**, PostgreSQL **17.11**, Psycopg binary **3.3.6**, Gunicorn **26.2.0**, WhiteNoise **6.12.0**. Python/Postgres base image digests are pinned in Dockerfile/compose.yaml. No npm build needed; Bootstrap **5.3.8** and HTMX **2.0.11** are vendored with licences.

1. Copy `.env.example` to `.env` and keep it private. Set a random `DJANGO_SECRET_KEY` (at least 32 characters) and random `POSTGRES_PASSWORD`. Set `POSTGRES_DB=papradit`, `POSTGRES_USER=papradit`, `DJANGO_DEBUG=1`, `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`, `PUBLIC_BASE_URL=http://localhost:8000`. For local invitation testing, `EMAIL_BACKEND=django.core.mail.backends.filebased.EmailBackend` writes email to `/tmp/papradit-mail` **inside the app container**. Treat these invitation files as sensitive; do not publish them. Production requires SMTP configuration.
2. Build and migrate:

```sh
docker compose build
docker compose up -d db
docker compose run --rm app python manage.py migrate --noinput
docker compose run --rm app python manage.py bootstrap_admin
docker compose up -d app
```

Create the first administrator through the interactive controlled CLI; no shared/default account or password exists. Open the app on local port 8000. Sign in, add products → jobs → steps (optional patterns) → workers → effective wage rates, then receive a PR, open/post it, assign work, record partial QC and deliver completed pieces. Invite colleagues and assign explicit role/module grants through Admin. Rates should cover the assignment business date. All live lists start empty; tests use synthetic records in disposable databases.

Compose builds the `development` image target, which retains pip for dependency checks. The default Docker build target is `production`; it verifies the dependency lock during build, then removes pip and its `ensurepip` bootstrap wheel. App dependencies and their scan metadata remain installed. No packages are installed at application startup.

The app image contains code/static assets. Rebuild after code changes and recreate only the app: `docker compose up -d --build app`. PostgreSQL data remains in `pgdata`. Do not use `down -v` against a database you want to retain. Migrations are an explicit command, not automatic Gunicorn startup behavior.

## Checks

```sh
docker compose run --rm app python -m pip check
docker compose run --rm app python manage.py check
docker compose run --rm app python manage.py makemigrations --check --dry-run
docker compose run --rm app python manage.py test --noinput
docker compose run --rm app python manage.py collectstatic --noinput
curl --fail http://127.0.0.1:8000/health/
```

The tests require PostgreSQL and a user allowed to create disposable test databases. Never point tests at production. Browser suite is opt-in (not installed in the runtime image): install `requirements.lock` + `requirements-dev.lock` into a Python 3.13 virtual environment, install Playwright Chromium (`python -m playwright install --with-deps chromium`), export the `.env` variable names/values securely with POSTGRES_HOST/PORT for an isolated PostgreSQL instance, run `python manage.py test work.browser_journeys --noinput`. `CHROMIUM_PATH` can select an existing Chromium. Screenshots go to ignored `.test-artifacts/`.

Regenerate runtime and separate dev locks using uv 0.9.7 **inside the pinned Python image**: `uv pip compile requirements.in --generate-hashes --python /usr/local/bin/python --output-file requirements.lock` (and similarly dev input). Install with `pip install --require-hashes`. Psycopg's cp313 x86_64 wheel was downloaded and run. Revalidate other architectures before deployment. Vendor asset hashes are in `static/vendor/SHA256SUMS`.

## Cloud workspace notes

This task already has an isolated checkout; use `/workspace/papradit_app` directly, with no worktree. The cloud proxy CA must be trusted in download/build containers. If BuildKit cannot resolve the proxy, pass its resolved address with `--add-host proxy:<resolved-IP>`, and forward existing proxy build args without printing their values:

```sh
DOCKER_CONFIG=/workspace/.docker docker build \
  --add-host "proxy:$(getent ahostsv4 proxy | awk 'NR==1{print $1}')" \
  --secret id=ca,src=/etc/ssl/certs/ca-certificates.crt \
  --build-arg HTTPS_PROXY --build-arg HTTP_PROXY --build-arg NO_PROXY \
  --target development -t papradit-app:local .
```

This uses TLS verification and a BuildKit secret mount (CA is not committed to the image). Ordinary local machines use `docker compose build`. Cloud host Python is 3.12.14; app/domain validation uses the exact Python 3.13.17 container, not the host interpreter.

## Release limitations

The container scan reports **44 HIGH findings** (zero critical) in the production target; the development target retains four additional installer-library findings; production release is blocked pending remediation/review. See `docs/image-scan-summary.json`.

This is the first implementation, not a production cutover. No AWS resources are provisioned or deployment claimed. SMTP/real user identities, company visibility and payable-wage rules require configuration/decisions. Historical spreadsheets were not imported. Fabric/material stock, cutting, fixed costs, payment accounting and PO approval are later releases. The `.env` created during development is ignored and contains generated local-only configuration, not production credentials.

Production image checks: `docker build --target production -t papradit-app:production .`; run the PostgreSQL application suite inside that image as in `.github/workflows/checks.yml`. Release-gate tests: `python -m unittest infra.test_release_gate -v`. Deployment refuses revisions without a successful latest trusted push Checks run for the exact full commit SHA, before requesting AWS credentials. GitHub-hosted workflows still require a real run after source review/push.
