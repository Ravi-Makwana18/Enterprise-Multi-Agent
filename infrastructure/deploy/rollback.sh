#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-staging}"
APP_NAME="enterprise-multi-agent"
APP_DIR="/opt/${APP_NAME}"
TARGET_DIR="${APP_DIR}/${ENVIRONMENT}"
PREVIOUS_RELEASE="${TARGET_DIR}/previous"
CURRENT_LINK="${TARGET_DIR}/current"

if [[ ! -d "${PREVIOUS_RELEASE}" ]]; then
  echo "No previous release available for rollback."
  exit 1
fi

rm -rf "${CURRENT_LINK}"
cp -R "${PREVIOUS_RELEASE}" "${CURRENT_LINK}"

if pgrep -f "uvicorn.*backend.main:app" >/dev/null; then
  pkill -f "uvicorn.*backend.main:app" || true
fi

cd "${CURRENT_LINK}"
./.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 > /tmp/${APP_NAME}-${ENVIRONMENT}.log 2>&1 &

curl --fail --silent http://127.0.0.1:8001/health >/dev/null

echo "Rollback completed for ${ENVIRONMENT}"
