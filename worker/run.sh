#!/bin/bash
# Test scenario script - runs test scenario
# This file is shared from host to worker container

set -e

SCENARIO_ID="${SCENARIO_ID:-1}"
DURATION="${SCENARIO_DURATION:-60}"

echo "[Worker] Starting scenario $SCENARIO_ID (duration: ${DURATION}s)"

# Simulate test work - can run actual tests here
sleep "$DURATION"

echo "[Worker] Scenario $SCENARIO_ID completed in ${DURATION}s"
echo "RESULT:scenario=$SCENARIO_ID:status=passed:duration=${DURATION}s"

exit 0