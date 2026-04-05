"""CLI for DIND parallel test orchestrator."""

import sys
import time

import click
from doit.orchestrator import WorkerPool, create_scenarios


@click.group()
def cli():
    """DIND parallel test orchestrator."""
    pass


def _run_tests(parallel: bool, workers: int, scenarios: int, duration: int, image: str):
    """Shared test execution logic."""
    click.echo(f"Starting test execution:")
    click.echo(f"  Parallel: {parallel}")
    click.echo(f"  Workers: {workers}")
    click.echo(f"  Scenarios: {scenarios}")
    click.echo(f"  Duration per scenario: {duration}s")
    click.echo(f"  Worker image: {image}")
    click.echo()

    if not parallel:
        click.echo("Sequential mode not implemented (use --parallel)")
        sys.exit(1)

    scenario_list = create_scenarios(count=scenarios, duration=duration)

    start_time = time.time()

    try:
        with WorkerPool(num_workers=workers, image=image) as pool:
            results = pool.run_parallel(scenario_list)

        total_time = int(time.time() - start_time)

        click.echo()
        click.echo(f"Results ({total_time}s total):")
        for result in results:
            status_icon = "✓" if result.status == "passed" else "✗"
            click.echo(f"  {status_icon} Scenario {result.scenario_id}: {result.status} ({result.duration}s)")

        passed = sum(1 for r in results if r.status == "passed")
        click.echo()
        click.echo(f"Passed: {passed}/{len(results)}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)



@cli.command()
@click.option('--parallel', is_flag=True, default=True, help='Enable parallel execution (default: True)')
@click.option('--workers', type=int, default=4, help='Number of parallel workers')
@click.option('--scenarios', type=int, default=5, help='Number of test scenarios')
@click.option('--duration', type=int, default=60, help='Duration of each scenario in seconds')
@click.option('--image', 'image', default='doit-worker:latest', help='Worker Docker image')
def test(parallel: bool, workers: int, scenarios: int, duration: int, image: str):
    """Run test scenarios in DIND mode (inside container).
    
    Spawns an orchestrator container with Docker socket mounted,
    which runs the test scenarios and spawns worker containers.
    """
    import os
    import subprocess

    # Check if we're already inside the orchestrator container
    if os.environ.get('IN_ORCHESTRATOR'):
        # Run tests directly (don't spawn another container)
        _run_tests(parallel, workers, scenarios, duration, image)
        return

    click.echo("Running in DIND mode (inside container)")
    click.echo(f"  Mounting Docker socket from host")
    click.echo()

    # Build orchestrator image if needed
    click.echo("Ensuring orchestrator image is built...")
    build_result = subprocess.run(
        ["docker", "build", "-t", "doit-orchestrator:latest", "-f", "orchestrator/Dockerfile", "."],
        capture_output=True,
        text=True
    )
    if build_result.returncode != 0:
        click.echo(f"Build failed: {build_result.stderr}", err=True)
        sys.exit(1)

    # Run orchestrator container with Docker socket mounted
    docker_args = [
        "docker", "run", "--rm",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        "-e", f"IN_ORCHESTRATOR=true",
        "-e", f"WORKERS={workers}",
        "-e", f"SCENARIOS={scenarios}",
        "-e", f"DURATION={duration}",
        "-e", f"WORKER_IMAGE={image}",
    ]

    # Pass through parallel flag
    if parallel:
        docker_args.append("-e")
        docker_args.append("PARALLEL=true")

    docker_args.append("doit-orchestrator:latest")

    click.echo(f"Starting orchestrator container...")
    result = subprocess.run(docker_args, capture_output=False)
    sys.exit(result)


@cli.command()
def build():
    """Build the worker Docker image."""
    import subprocess

    click.echo("Building worker image...")
    result = subprocess.run(
        ["docker", "build", "-t", "doit-worker:latest", "-f", "worker/Dockerfile", "worker/"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        click.echo("Build successful!")
    else:
        click.echo(f"Build failed: {result.stderr}", err=True)
        sys.exit(1)


@cli.command()
def build_all():
    """Build both worker and orchestrator images."""
    import subprocess

    click.echo("Building worker image...")
    result = subprocess.run(
        ["docker", "build", "-t", "doit-worker:latest", "-f", "worker/Dockerfile", "worker/"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        click.echo(f"Worker build failed: {result.stderr}", err=True)
        sys.exit(1)
    click.echo("Worker image built!")

    click.echo("Building orchestrator image...")
    result = subprocess.run(
        ["docker", "build", "-t", "doit-orchestrator:latest", "-f", "orchestrator/Dockerfile", "."],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        click.echo(f"Orchestrator build failed: {result.stderr}", err=True)
        sys.exit(1)
    click.echo("Orchestrator image built!")

    click.echo("All images built successfully!")


if __name__ == '__main__':
    cli()