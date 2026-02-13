#!/bin/bash
#
# Quick monitoring check for confida-service.
# Curls /health and optionally /api/v1/health/metrics, reports status.
#
# Usage:
#   ./scripts/check_monitoring.sh [BASE_URL]
#   ./scripts/check_monitoring.sh http://localhost:8000
#   ./scripts/check_monitoring.sh https://staging.example.com
#

set -e

BASE_URL="${1:-http://localhost:8000}"
BASE_URL="${BASE_URL%/}"

echo "🔍 Monitoring check for $BASE_URL"
echo "================================"

# Health check
echo ""
echo "Health endpoint: GET $BASE_URL/health"
HTTP_CODE=$(curl -s -o /tmp/confida_health.json -w "%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    if command -v jq &>/dev/null; then
        STATUS=$(jq -r '.status // "unknown"' /tmp/confida_health.json 2>/dev/null || echo "unknown")
    else
        STATUS="ok"
    fi
    echo "  ✅ HTTP $HTTP_CODE - status: $STATUS"
else
    echo "  ❌ HTTP $HTTP_CODE (expected 200)"
    exit 1
fi

# Readiness check (optional)
echo ""
echo "Readiness endpoint: GET $BASE_URL/ready"
READY_CODE=$(curl -s -o /tmp/confida_ready.json -w "%{http_code}" "$BASE_URL/ready" 2>/dev/null || echo "000")
if [ "$READY_CODE" = "200" ]; then
    if command -v jq &>/dev/null; then
        READY=$(jq -r '.ready // "unknown"' /tmp/confida_ready.json 2>/dev/null || echo "unknown")
    else
        READY="ok"
    fi
    echo "  ✅ HTTP $READY_CODE - ready: $READY"
else
    echo "  ⚠️  HTTP $READY_CODE (optional)"
fi

# Metrics endpoint (when MONITORING_ENABLED=true)
echo ""
echo "Metrics endpoint: GET $BASE_URL/api/v1/health/metrics"
METRICS_CODE=$(curl -s -o /tmp/confida_metrics.txt -w "%{http_code}" "$BASE_URL/api/v1/health/metrics" 2>/dev/null || echo "000")
if [ "$METRICS_CODE" = "200" ]; then
    METRICS_LINES=$(wc -l < /tmp/confida_metrics.txt 2>/dev/null || echo "0")
    echo "  ✅ HTTP $METRICS_CODE - Prometheus metrics available ($METRICS_LINES lines)"
elif [ "$METRICS_CODE" = "404" ]; then
    echo "  ⚠️  HTTP 404 - Monitoring disabled (MONITORING_ENABLED=false)"
else
    echo "  ⚠️  HTTP $METRICS_CODE - Metrics endpoint may be disabled"
fi

# Cleanup
rm -f /tmp/confida_health.json /tmp/confida_ready.json /tmp/confida_metrics.txt

echo ""
echo "✅ Monitoring check complete"
