#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${ATLAS_API_BASE_URL:-http://127.0.0.1:8080}"
API_KEY_HEADER=()
if [ -n "${ATLAS_API_KEY:-}" ]; then
  API_KEY_HEADER=(-H "X-ATLAS-API-Key: ${ATLAS_API_KEY}")
fi

curl --fail-with-body "${BASE_URL}/api/v1/health"
printf '\n'
curl --fail-with-body -X POST "${BASE_URL}/api/v1/migrations" "${API_KEY_HEADER[@]}" -H 'Content-Type: application/json' -d '{"migration_id":"smoke-script","source":"legacy","target":"modern"}'
printf '\n'
curl --fail-with-body "${BASE_URL}/api/v1/migrations/smoke-script" "${API_KEY_HEADER[@]}"
printf '\n'
curl --fail-with-body -X POST "${BASE_URL}/api/v1/migrations/smoke-script/jobs" "${API_KEY_HEADER[@]}" -H 'Content-Type: application/json' -d '{"table":"accounts","partition":"p1"}'
printf '\n'
curl --fail-with-body "${BASE_URL}/api/v1/workers" "${API_KEY_HEADER[@]}"
printf '\n'
curl --fail-with-body -X POST "${BASE_URL}/api/v1/policies/precheck" "${API_KEY_HEADER[@]}" -H 'Content-Type: application/json' -d '{"reconciliation_passed":true,"cdc_lag":0,"breaking_schema_change":false,"pii_logging":false,"risk_score":0.1}'
printf '\n'
curl --fail-with-body "${BASE_URL}/openapi.json"
printf '\nAPI SMOKE: PASS\n'
