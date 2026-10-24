# syntax=docker/dockerfile:1
FROM python:3.13.17-slim-trixie@sha256:fe14fd57a4c0361110eaa0c284112b189750bcb43fb04bb5d1ee7b7744027ccf AS application
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock ./
RUN --mount=type=secret,id=ca \
    if [ -f /run/secrets/ca ]; then export PIP_CERT=/run/secrets/ca; fi; \
    pip install --no-cache-dir --require-hashes -r requirements.lock && pip check
COPY --chown=10001:10001 . .
RUN chmod -R a+rX /app && DJANGO_SECRET_KEY=build-only-placeholder-key-no-runtime-access python manage.py collectstatic --noinput && useradd --uid 10001 --create-home app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/')"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "--timeout", "60"]

# Local development retains the installer and `pip check` command.
FROM application AS development

# The deployed application installs nothing at runtime. Preserve application and
# OS metadata for vulnerability scanning; remove only the unused installer and
# its stdlib bootstrap wheel, both of which vendor vulnerable tooling libraries.
FROM application AS production
USER root
RUN python -m pip check \
    && python -m pip uninstall --yes pip \
    && python -c "import pathlib, shutil, sysconfig; shutil.rmtree(pathlib.Path(sysconfig.get_path('stdlib')) / 'ensurepip')"
USER app
