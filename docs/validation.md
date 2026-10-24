# Validation evidence — 24 October 2026

This is a working first-release implementation in the existing `PalidaY/papradit_app` checkout, not a production deployment or historical cutover. GitHub workflow definitions are included. See repository history for source publication; hosted workflow results require independent verification. No AWS infrastructure or paid service was provisioned.

## Runtime

- Linux x86_64; Docker Engine 28.4.0; Compose v2.40.3.
- **Python 3.13.17** in the application image, Django 5.2.18, Psycopg/Psycopg binary 3.3.6, Gunicorn 26.2.0, WhiteNoise 6.12.0.
- PostgreSQL **17.11** (`17.11-1.pgdg12+2`) in a separate Compose service with persistent volume.
- Python base: `python:3.13.17-slim-trixie@sha256:fe14fd57a4c0361110eaa0c284112b189750bcb43fb04bb5d1ee7b7744027ccf`.
- PostgreSQL base: `postgres:17.11-bookworm@sha256:858bb5e98eed02eb8cafbcdc007f9a65d1b613972028944a8ec2133ccaf80d27`.
- The original Bookworm Python image was available but had 67 HIGH/CRITICAL findings (65 high / 2 critical). Trixie retains the **same approved Python patch** and initially reduced this to 48 high / 0 critical. Separating installer-free production from development subsequently reduced production to **44 high / 0 critical**; the four installer-library findings remain only in the development target. This distribution choice changes no selected runtime dependency pins.
- Runtime/transitive and separate development locks were generated using uv 0.9.7 under exact Python 3.13.17. All runtime wheels were installed with hashes; the cp313 x86_64 Psycopg binary wheel was resolved and executed. Other architectures are unverified.

## Passed

| Check | Current-instance evidence |
|---|---|
| Exact app image build | Successful, non-root Gunicorn execution; source permissions normalized for non-root runtime |
| `python -m pip check` | No broken requirements |
| Django system/migration checks | `check`, `makemigrations --check --dry-run`: no issues/drift |
| Fresh PostgreSQL migrations | All auth/catalog/core/work/session migrations applied to isolated new databases |
| Domain/permission tests | **29 passed inside the installer-free production image**, exact Python 3.13.17 + PostgreSQL 17.11, clean test-database teardown |
| Release-gate tests | **11 passed** under Python 3.13.17: exact SHA, trusted repository/push/workflow, latest-success requirement; failed/pending/fork/old success cannot authorize deployment |
| Installer removal | Production has neither pip nor ensurepip/bootstrap wheel; app package metadata retained. Development `pip check` still passes |
| OS updates | Signed Debian repository refresh completed in a disposable pinned-base container; no package upgrades available. No verification bypass or forced package removal |
| Concurrency | Concurrent assignments/receipts reject over-allocation; duplicate-key race posts once |
| Permission coverage | Anonymous API 401; viewer write forbidden; financial fields omitted from HTML/JSON/CSV; account disablement and grant/session revocation; CSRF; no first-visitor admin; last-admin guard |
| Operational coverage | Multiple product/size lines, explicit string source IDs/crosswalk, actual PR create/edit forms, partial QC/rework, independent steps, rate snapshots, safe reversals, partial delivery, close guards, price overlap/missing rate rejection |
| Browser integration | **1 full journey passed**, real Chromium + Playwright 1.56.0: login → multi-line PR → post → invalid/valid assignment → partial QC/rework → search/HTMX; loaded CSS/JS, no HTTP/JS errors; desktop and tablet overflow/layout assertions |
| Browser environment distinction | Browser suite ran from host Python 3.12.14 against isolated PostgreSQL 17.11. Domain and Gunicorn runtime checks ran under selected Python 3.13.17. GitHub workflow is configured to run both under 3.13.17, but that CI run is unverified |
| Static assets | `collectstatic`; vendored SHA256 checks; actual Gunicorn/WhiteNoise requests returned hashed Bootstrap/app CSS with correct content types |
| Application requests | Initial Gunicorn authenticated persisted PR check; final installer-free production Gunicorn health/login page and all six hashed assets passed. DB health `{"status":"ok"}` |
| Deployment configuration check | `check --deploy --fail-level WARNING` with DEBUG=0, explicit host/HTTPS CSRF origin: no issues (not proof of actual ALB/HTTPS behavior) |
| Persistence across replacement | Existing authenticated database session and PR records survived replacing the Gunicorn container; repeated with final Trixie app image |
| Backup/restore | PostgreSQL custom dump of synthetic runtime database restored to a separate DB: exact full-row reconciliation across **26 tables, 153 rows**, including sessions, source mappings, audit and PR lines |
| Python dependency audit | pip-audit 2.9.0: no known vulnerabilities in the seven locked runtime packages at scan time |
| Source secret scan | Trivy secret scanner: **0 findings** in source; ignored local `.env`, caches, test artefacts and vendored assets excluded. This is not a full remote Git-history scan |
| Reusable setup | `sh infra/setup_cloud.sh` executed successfully on existing `.env`/database; migrations no-op on repeat; app/DB started healthy with Compose `--wait` |

Browser screenshots use synthetic data and live in ignored `.test-artifacts/dashboard-desktop.png` and `dashboard-tablet.png`. No historical data was used. Disposable runtime/browser services and databases were removed after checks; main app/DB contain no seeded staff or business records.

## Failed / production blockers

- **Image vulnerability gate fails:** Trivy 0.67.2 reports **44 HIGH, 0 CRITICAL** findings on the production Trixie image (48 high in the development target). The detailed package/advisory summary and local scanned image ID are in `image-scan-summary.json`. All 44 remaining production findings affect OS packages and have no fixed version reported. The four pip-vendored packaging findings (msgpack, setuptools, urllib3) were removed from production by removing unused installer/bootstrap tooling, not by suppressing scan results. The separate application runtime lock audit is clean. These findings have not been waived or assumed non-exploitable. CI deliberately fails the HIGH/CRITICAL image gate, and deployment now checks that CI result before obtaining AWS credentials. It remains blocked until a patched image/toolchain or reviewed mitigation is validated. Never call this image production-ready.
- AWS RDS CA bundle download from the official `truststore.pki.rds.amazonaws.com` endpoint returned HTTP 403 in this cloud environment. The ECS template requires an actual verified bundle at `/run/certs/rds-ca.pem`; the app image intentionally does not invent one. Allow that hostname in environment network settings, download/verify the official bundle, package it, and test RDS certificate verification before deployment. Local PostgreSQL validation is unaffected.
- No real AWS Region/account, RDS orderability, ALB/HTTPS/cookie/proxy behavior, production database role, current regional quote, production SMTP or RDS PITR restoration has been validated. See deployment gates.
- The owner has not confirmed company isolation or payable-wage/QC policy. PPD/GPT are context labels in one shared workspace, **not enforced legal-entity separation**. Settlement is disabled; accepted-work reference values are not liabilities. Do not do financial cutover until these decisions are resolved.
- No actual staff invitations/roles were configured. Create the first administrator with the controlled interactive command, then configure catalogues and grants. Invitation delivery was tested with Django's in-memory mail backend; real SMTP still needs validation.
- Later modules, payment accounting, separate PO approvals, historical staging/import/reconciliation, private uploads and PDF layouts remain outside this first release. Stock/payment acceptance cases were not run and are not reported as passing.

## Saved cloud configuration

`install_script` and `start_skill` were saved successfully as a configuration **draft**. They use the existing isolated checkout, preserve an existing `.env`, install/build/migrate/check, and start/verify app + database processes. Saving did not publish a snapshot or validate restoration in a new task. Review/save the draft in environment settings, then publish when appropriate for development use; production security gates remain separate.

The production image has passed application tests and installer-removal checks. The current GitHub workflow/API integration is prepared but unexecuted on GitHub; the 11 release-gate tests use synthetic workflow responses, not a claimed live GitHub authorization check.
