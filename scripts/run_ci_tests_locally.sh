#!/usr/bin/env bash
#
# Run CI tests locally (matches GitHub PR workflow).
# Requires Docker for PostgreSQL and Redis.
#
# Usage: ./scripts/run_ci_tests_locally.sh
#
set -e

CONTAINER_POSTGRES="test-postgres"
CONTAINER_REDIS="test-redis"

# Cleanup function
cleanup() {
  echo "Cleaning up containers..."
  docker stop "$CONTAINER_POSTGRES" "$CONTAINER_REDIS" 2>/dev/null || true
  docker rm "$CONTAINER_POSTGRES" "$CONTAINER_REDIS" 2>/dev/null || true
}

# Ensure we're in project root
cd "$(dirname "$0")/.."

# Check Docker is running
if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker daemon is not running. Please start Docker and try again."
  exit 1
fi

# Remove existing containers if they exist
docker rm -f "$CONTAINER_POSTGRES" "$CONTAINER_REDIS" 2>/dev/null || true

echo "Starting PostgreSQL 13..."
docker run -d --name "$CONTAINER_POSTGRES" \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=test_confida \
  -p 5432:5432 \
  postgres:13

echo "Starting Redis 6..."
docker run -d --name "$CONTAINER_REDIS" \
  -p 6379:6379 \
  redis:6

# Register cleanup on exit
trap cleanup EXIT

echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
  if docker exec "$CONTAINER_POSTGRES" pg_isready -U postgres -d test_confida >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "PostgreSQL failed to become ready"
    exit 1
  fi
  sleep 1
done

echo "Waiting for Redis to be ready..."
for i in {1..10}; do
  if docker exec "$CONTAINER_REDIS" redis-cli ping 2>/dev/null | grep -q PONG; then
    break
  fi
  if [ "$i" -eq 10 ]; then
    echo "Redis failed to become ready"
    exit 1
  fi
  sleep 1
done

echo "Setting environment variables..."
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_confida
export REDIS_URL=redis://localhost:6379
export SECRET_KEY=test-secret-key-for-github-actions
export ENVIRONMENT=test
export RATE_LIMIT_ENABLED=false

echo "Installing dependencies..."
pip install -q -r requirements.txt
pip install -q -r requirements-test.txt

echo "Running migrations..."
python app/database/migrate.py upgrade head

echo "Running CI test command..."
python -m pytest tests/ -v --cov=app --cov-report=xml --junitxml=test-results.xml --timeout=60
