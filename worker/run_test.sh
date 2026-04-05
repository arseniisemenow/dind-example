#!/bin/bash
# Test scenario imitation script
# Reads SCENARIO_ID and SCENARIO_DURATION from environment

set -e

SCENARIO_ID="${SCENARIO_ID:-1}"
DURATION="${SCENARIO_DURATION:-60}"

echo "[Worker] Starting scenario $SCENARIO_ID (duration: ${DURATION}s)"

# Simulate test work
START_TIME=$(date +%s)
sleep "$DURATION"
END_TIME=$(date +%s)

echo "[Worker] Scenario $SCENARIO_ID completed in $((END_TIME - START_TIME))s"

# Output result in machine-parseable format for orchestrator
echo "RESULT:scenario=$SCENARIO_ID:status=passed:duration=$((END_TIME - START_TIME))s"

exit 0