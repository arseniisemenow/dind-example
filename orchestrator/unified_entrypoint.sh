#!/bin/bash
# Unified entrypoint for both orchestrator and worker roles
# Role is determined by the ROLE environment variable
# If /work/run.sh exists (mounted from host), run that instead

set -e

ROLE="${ROLE:-orchestrator}"

if [ "$ROLE" = "worker" ]; then
    # Worker role: check if work dir is mounted with custom script
    if [ -f "/work/run.sh" ]; then
        echo "[Worker] Running custom script from /work/run.sh"
        cd /work
        chmod +x run.sh
        exec /work/run.sh
    else
        # Fallback: internal test scenario
        SCENARIO_ID="${SCENARIO_ID:-1}"
        DURATION="${SCENARIO_DURATION:-60}"
        
        echo "[Worker] Starting scenario $SCENARIO_ID (duration: ${DURATION}s)"
        sleep "$DURATION"
        echo "[Worker] Scenario $SCENARIO_ID completed in ${DURATION}s"
        echo "RESULT:scenario=$SCENARIO_ID:status=passed:duration=${DURATION}s"
        exit 0
    fi
    
elif [ "$ROLE" = "orchestrator" ]; then
    # Orchestrator role: run the test orchestration
    PARALLEL="${PARALLEL:-true}"
    WORKERS="${WORKERS:-4}"
    SCENARIOS="${SCENARIOS:-5}"
    DURATION="${DURATION:-60}"
    WORKER_IMAGE="${WORKER_IMAGE:-doit-orchestrator:latest}"
    
    export IN_ORCHESTRATOR=true
    
    CMD="poetry run doit test --parallel"
    
    if [ "$PARALLEL" = "true" ] || [ "$PARALLEL" = "True" ] || [ "$PARALLEL" = "1" ]; then
        CMD="$CMD --parallel"
    fi
    
    CMD="$CMD --workers $WORKERS"
    CMD="$CMD --scenarios $SCENARIOS"
    CMD="$CMD --duration $DURATION"
    CMD="$CMD --image $WORKER_IMAGE"
    
    echo "Running: $CMD"
    exec $CMD
    
else
    echo "Unknown role: $ROLE"
    exit 1
fi