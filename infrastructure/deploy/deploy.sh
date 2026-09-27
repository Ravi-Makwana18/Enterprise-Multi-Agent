#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-staging}"
IMAGE_TAG="${2:-latest}"
APP_NAME="enterprise-multi-agent"

# Fallback if /opt is not writable by current user
if [ -w /opt ] || [ "${EUID:-$(id -u)}" -eq 0 ]; then
  APP_DIR="/opt/${APP_NAME}"
else
  APP_DIR="${DEPLOY_APP_DIR:-/tmp/${APP_NAME}}"
fi
TARGET_DIR="${APP_DIR}/${ENVIRONMENT}"

mkdir -p "${TARGET_DIR}"
cp -R . "${TARGET_DIR}/source"

cd "${TARGET_DIR}/source"
PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null; then
  PYTHON_CMD="python"
fi

${PYTHON_CMD} -m venv .venv
./.venv/bin/pip install --upgrade pip >/dev/null
./.venv/bin/pip install -r requirements.txt >/dev/null

cat > .env <<EOF
APP_NAME=${APP_NAME}
ENVIRONMENT=${ENVIRONMENT}
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8001
DATABASE_URL=sqlite:///./enterprise_multi_agent.db
EOF

# Free up port 8001 if previously occupied
pkill -f "uvicorn backend.main:app" || true
if command -v docker &>/dev/null; then
  docker stop enterprise-multi-agent 2>/dev/null || true
fi

nohup ./.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 > /tmp/${APP_NAME}-${ENVIRONMENT}.log 2>&1 &

sleep 3
curl --fail --silent http://127.0.0.1:8001/health >/dev/null

echo "Deployment successful for ${ENVIRONMENT} (${IMAGE_TAG})"

