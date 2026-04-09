#!/bin/bash
set -euo pipefail

APP_ROOT="/home/site/wwwroot"
VENV_GUNICORN="${APP_ROOT}/antenv/bin/gunicorn"

# Azure App Service sets PORT. Keep safe defaults for local/manual starts.
PORT="${PORT:-8000}"
WORKERS="${GUNICORN_WORKERS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "--- Running startup.sh ---"
echo "APP_ROOT=${APP_ROOT}"
echo "PORT=${PORT}"

if [ -x "${VENV_GUNICORN}" ]; then
  GUNICORN_CMD="${VENV_GUNICORN}"
  echo "Using gunicorn from antenv."
elif command -v gunicorn >/dev/null 2>&1; then
  GUNICORN_CMD="$(command -v gunicorn)"
  echo "Using gunicorn from PATH: ${GUNICORN_CMD}"
else
  echo "ERROR: gunicorn not found in ${VENV_GUNICORN} or PATH."
  echo "Set SCM_DO_BUILD_DURING_DEPLOYMENT=true and redeploy so Oryx installs dependencies."
  exit 1
fi

exec "${GUNICORN_CMD}" \
  -w "${WORKERS}" \
  -k uvicorn.workers.UvicornWorker \
  --chdir "${APP_ROOT}" \
  app.main:app \
  --bind "0.0.0.0:${PORT}" \
  --timeout "${TIMEOUT}"