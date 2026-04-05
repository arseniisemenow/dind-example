# DIND Parallel Test Demo

Docker-in-Docker demo with parallel test scenario execution.

## Architecture

```
Host Machine (Docker Daemon)
    │
    └── Orchestrator (Python via Poetry)
           ├── Connects to host Docker via socket
           └── Spawns Worker Containers in parallel
                  ├── Worker 1 → runs scenario 1
                  ├── Worker 2 → runs scenario 2
                  ├── Worker 3 → runs scenario 3
                  ├── Worker 4 → runs scenario 4
                  └── (after worker finishes) → Worker runs scenario 5
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

2. Build the worker Docker image:
```bash
poetry run doit build
```

## Usage

Run test scenarios in parallel:
```bash
poetry run doit test --parallel --workers 4
```

Options:
- `--parallel` - Enable parallel execution (required)
- `--workers N` - Number of parallel workers (default: 4)
- `--scenarios N` - Number of test scenarios (default: 5)
- `--duration N` - Duration of each scenario in seconds (default: 60)
- `--image NAME` - Worker Docker image (default: doit-worker:latest)

### Examples

Run 4 parallel workers with 5 scenarios (60s each):
```bash
poetry run doit test --parallel --workers 4
```
Expected: ~120s (first 4 run in parallel, then 5th)

Run 4 workers with 4 scenarios (60s each):
```bash
poetry run doit test --parallel --workers 4 --scenarios 4
```
Expected: ~60s (all 4 run in parallel)

Run with shorter duration for testing:
```bash
poetry run doit test --parallel --workers 4 --duration 10
```

## Development

Run tests:
```bash
poetry run pytest tests/ -v
```

### Test Verification

The key test `test_4_workers_4_scenarios_should_take_approx_60s` verifies:
- With 4 workers and 4 scenarios of equal duration
- Total time ≈ longest single scenario (not sum of all)
- This proves parallel execution works correctly

## File Structure

```
.
├── pyproject.toml          # Poetry project config
├── src/doit/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point
│   └── orchestrator.py     # Worker pool manager
├── worker/
│   ├── Dockerfile          # Worker image (Alpine-based)
│   └── run_test.sh        # Test imitation script
└── tests/
    └── test_orchestrator.py  # Unit tests with parallel verification
```

## How It Works

1. CLI parses `--parallel --workers N` flags
2. WorkerPool spawns up to N containers simultaneously
3. Each container runs `run_test.sh` which sleeps for configured duration
4. When a worker finishes, the pool starts the next scenario
5. Results are collected and reported

The worker container reads `SCENARIO_ID` and `SCENARIO_DURATION` from environment variables set by the orchestrator.