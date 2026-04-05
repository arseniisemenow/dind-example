# DIND Parallel Test Demo

Docker-in-Docker demo with parallel test scenario execution.

## Architecture

```
Host Machine (Docker Daemon)
    │
    └── `poetry run doit test` spawns:
           └── Unified Container (same image for orchestrator + workers)
                  └── Mounts /var/run/docker.sock
                  └── Spawns Worker Containers (same image)
                         ├── Worker 1 → scenario 1
                         ├── Worker 2 → scenario 2
                         ├── Worker 3 → scenario 3
                         ├── Worker 4 → scenario 4
                         └── (after worker finishes) → scenario 5
```

## Key Feature: Unified Image

Both the **orchestrator** and **worker** containers use the **same Docker image**. The role is determined by the `ROLE` environment variable:
- `ROLE=orchestrator` → runs test orchestration logic
- `ROLE=worker` → runs test scenario

## Requirements

- Docker daemon running on host
- Python 3.11+
- Poetry

## Setup

1. Install dependencies:
```bash
poetry install
```

2. Build the unified Docker image:
```bash
poetry run doit build
```

## Usage

```bash
poetry run doit test --workers 4
```

Options:
- `--workers N` - Number of parallel workers (default: 4)
- `--scenarios N` - Number of test scenarios (default: 5)
- `--duration N` - Duration of each scenario in seconds (default: 60)
- `--image NAME` - Unified Docker image (default: doit-orchestrator:latest)

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
│   ├── Dockerfile              # Unified image (Python + Poetry + Docker)
│   └── unified_entrypoint.sh  # Handles both orchestrator & worker roles
└── tests/
    └── test_orchestrator.py   # Unit tests
```

## How It Works

1. `poetry run doit test` is called on host
2. CLI builds unified Docker image (if needed)
3. CLI spawns orchestrator container with:
   - Docker socket mounted (`-v /var/run/docker.sock:/var/run/docker.sock`)
   - `ROLE=orchestrator` environment variable
   - Test parameters (workers, scenarios, duration)
4. Inside orchestrator container:
   - Detects `IN_ORCHESTRATOR=true` environment variable
   - Runs test orchestration directly (not another container)
5. WorkerPool spawns worker containers via Docker SDK:
   - Uses same image as orchestrator
   - Sets `ROLE=worker` environment variable
   - Each worker runs its test scenario and exits

## Image Details

The unified image includes:
- Python 3.12 (slim)
- Poetry
- Docker CLI
- Project source code and dependencies

Worker containers just run the test scenario and exit. Orchestrator container handles the coordination and spawns workers as slots become available.