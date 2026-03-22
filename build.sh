#!/usr/bin/env bash
# build.sh — rebuild and re-deploy all ARCRA containers
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Stopping running containers..."
docker compose -f "${PROJECT_ROOT}/docker-compose.yaml" down --remove-orphans --volumes

echo "==> Building images (no cache)..."
docker compose -f "${PROJECT_ROOT}/docker-compose.yaml" build --no-cache

echo "==> Starting containers..."
docker compose -f "${PROJECT_ROOT}/docker-compose.yaml" up -d

echo "==> Waiting for services to be ready..."
sleep 5

echo "==> Health check..."
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/transactions/active || echo "000")
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "000")

echo "    Backend  (http://localhost:8000): HTTP ${BACKEND_STATUS}"
echo "    Frontend (http://localhost:3000): HTTP ${FRONTEND_STATUS}"

if [[ "${BACKEND_STATUS}" == "200" && ("${FRONTEND_STATUS}" == "200" || "${FRONTEND_STATUS}" == "307") ]]; then
  echo ""
  echo "==> Deploy complete. Open http://localhost:3000 to access the dashboard."
else
  echo ""
  echo "WARNING: One or more services may not be healthy. Check logs with:"
  echo "  docker compose logs -f"
  exit 1
fi
