#!/bin/bash
set -euo pipefail

APP_ROOT="/home/site/wwwroot"
VENV_DIR="${APP_ROOT}/antenv"
PY_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"
GUNICORN_BIN="${VENV_DIR}/bin/gunicorn"

# Azure App Service sets PORT. Keep a safe fallback for local/manual starts.
PORT="${PORT:-8000}"
WORKERS="${GUNICORN_WORKERS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "--- Running startup.sh ---"
echo "APP_ROOT=${APP_ROOT}"
echo "PORT=${PORT}"

if [ ! -f "${APP_ROOT}/requirements.txt" ]; then
  echo "ERROR: requirements.txt not found under ${APP_ROOT}"
  exit 1
fi

# Rebuild virtualenv if missing, or force manually with FORCE_REBUILD_VENV=1.
if [ "${FORCE_REBUILD_VENV:-0}" = "1" ] || [ ! -x "${PY_BIN}" ]; then
  echo "Creating virtual environment at ${VENV_DIR}..."
  rm -rf "${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"
fi

echo "Installing runtime dependencies..."
"${PIP_BIN}" install --upgrade pip
"${PIP_BIN}" install -r "${APP_ROOT}/requirements.txt"

if [ ! -x "${GUNICORN_BIN}" ]; then
  echo "ERROR: gunicorn not installed in ${VENV_DIR}"
  exit 1
fi

echo "Starting gunicorn..."
exec "${GUNICORN_BIN}" \
  -w "${WORKERS}" \
  -k uvicorn.workers.UvicornWorker \
  --chdir "${APP_ROOT}" \
  app.main:app \
  --bind "0.0.0.0:${PORT}" \
  --timeout "${TIMEOUT}"