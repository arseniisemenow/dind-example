#!/bin/bash
# Entrypoint for orchestrator container
# Reads environment variables and runs the test command

set -e

# Default values
PARALLEL="${PARALLEL:-true}"
WORKERS="${WORKERS:-4}"
SCENARIOS="${SCENARIOS:-5}"
DURATION="${DURATION:-60}"
WORKER_IMAGE="${WORKER_IMAGE:-doit-worker:latest}"

# Mark that we're inside the orchestrator to avoid infinite container spawning
export IN_ORCHESTRATOR=true

# Build command
CMD="poetry run doit test"

# Add parallel flag (default is already True in CLI, but explicitly set for clarity)
if [ "$PARALLEL" = "true" ] || [ "$PARALLEL" = "True" ] || [ "$PARALLEL" = "1" ]; then
    CMD="$CMD --parallel"
fi

CMD="$CMD --workers $WORKERS"
CMD="$CMD --scenarios $SCENARIOS"
CMD="$CMD --duration $DURATION"
CMD="$CMD --image $WORKER_IMAGE"

echo "Running: $CMD"
exec $CMD