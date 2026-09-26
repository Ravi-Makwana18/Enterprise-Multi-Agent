#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-staging}"
IMAGE_TAG="${2:-latest}"
APP_NAME="enterprise-multi-agent"
APP_DIR="/opt/${APP_NAME}"
TARGET_DIR="${APP_DIR}/${ENVIRONMENT}"

mkdir -p "${TARGET_DIR}"
cp -R . "${TARGET_DIR}/source"

cd "${TARGET_DIR}/source"
python -m venv .venv
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

nohup ./.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 > /tmp/${APP_NAME}-${ENVIRONMENT}.log 2>&1 &

curl --fail --silent http://127.0.0.1:8001/health >/dev/null

echo "Deployment successful for ${ENVIRONMENT} (${IMAGE_TAG})"
