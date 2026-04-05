# DIND Parallel Test Demo

Docker-in-Docker demo with parallel test scenario execution.

## Architecture

```
Host Machine (Docker Daemon)
    │
    └── `poetry run doit test` spawns:
           └── Orchestrator Container
                  └── Mounts /var/run/docker.sock
                  └── Spawns Worker Containers (parallel)
                         ├── Worker 1 → scenario 1
                         ├── Worker 2 → scenario 2
                         ├── Worker 3 → scenario 3
                         ├── Worker 4 → scenario 4
                         └── (after worker finishes) → scenario 5
```

## Requirements

- Docker daemon running on host
- Python 3.11+
- Poetry

## Setup

1. Install dependencies:
```bash
poetry install
```

2. Build Docker images:
```bash
poetry run doit build        # Worker image
# Orchestrator image is built automatically on first `doit test` run
```

Or build both at once:
```bash
docker build -t doit-worker:latest -f worker/Dockerfile worker/
docker build -t doit-orchestrator:latest -f orchestrator/Dockerfile .
```

## Usage

**DIND mode (default):**
```bash
poetry run doit test --workers 4
```

This command:
1. Spawns an orchestrator container with Docker socket mounted
2. Container runs the test orchestration
3. Worker containers are spawned in parallel via the mounted socket

Options:
- `--workers N` - Number of parallel workers (default: 4)
- `--scenarios N` - Number of test scenarios (default: 5)
- `--duration N` - Duration of each scenario in seconds (default: 60)
- `--image NAME` - Worker Docker image (default: doit-worker:latest)

### Examples

```bash
# 4 workers, 5 scenarios, 60s each → ~120s total
poetry run doit test --workers 4

# Quick test
poetry run doit test --workers 4 --scenarios 4 --duration 5
```

## Development

Run tests:
```bash
poetry run pytest tests/ -v
```

### Test Verification

The key test `test_4_workers_4_scenarios_should_take_approx_60s` verifies parallel execution works correctly - total time ≈ longest single scenario, not sum of all.

## File Structure

```
.
├── pyproject.toml              # Poetry project config
├── src/doit/
│   ├── __init__.py
│   ├── cli.py                  # CLI (doit test spawns container)
│   └── orchestrator.py         # Worker pool manager
├── orchestrator/
│   ├── Dockerfile              # Orchestrator image (Python + Poetry + Docker)
│   └── test_entrypoint.sh      # Container entrypoint
├── worker/
│   ├── Dockerfile              # Worker image (Alpine-based)
│   └── run_test.sh            # Test imitation script
└── tests/
    └── test_orchestrator.py   # Unit tests
```

## How It Works

1. `poetry run doit test` is called
2. CLI spawns orchestrator container with Docker socket mounted
3. Orchestrator container sets `IN_ORCHESTRATOR=true` env var
4. Inside container, CLI detects this env var and runs tests directly
5. WorkerPool spawns worker containers via Docker SDK (talking to host daemon)
6. Each worker container runs `run_test.sh` which sleeps for configured duration