"""CLI for DIND parallel test orchestrator."""

import sys
import time

import click
from doit.orchestrator import WorkerPool, create_scenarios


@click.group()
def cli():
    """DIND parallel test orchestrator."""
    pass


@cli.command()
@click.option('--parallel', is_flag=True, help='Enable parallel execution')
@click.option('--workers', type=int, default=4, help='Number of parallel workers')
@click.option('--scenarios', type=int, default=5, help='Number of test scenarios')
@click.option('--duration', type=int, default=60, help='Duration of each scenario in seconds')
@click.option('--image', default='doit-worker:latest', help='Worker Docker image')
def test(parallel: bool, workers: int, scenarios: int, duration: int, image: str):
    """Run test scenarios in parallel."""
    click.echo(f"Starting test execution:")
    click.echo(f"  Parallel: {parallel}")
    click.echo(f"  Workers: {workers}")
    click.echo(f"  Scenarios: {scenarios}")
    click.echo(f"  Duration per scenario: {duration}s")
    click.echo(f"  Worker image: {image}")
    click.echo()

    if not parallel:
        # Sequential execution
        click.echo("Sequential mode not implemented (use --parallel)")
        sys.exit(1)

    # Create scenarios
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


if __name__ == '__main__':
    cli()