"""Docker orchestrator for parallel test execution."""

import os
import time
import threading
import uuid
from dataclasses import dataclass
from typing import Optional

import docker
from docker.models.containers import Container


@dataclass(kw_only=True)
class TestScenario:
    """Represents a single test scenario."""
    id: int
    duration: int = 60  # seconds


@dataclass(kw_only=True)
class TestResult:
    """Result of a test scenario execution."""
    scenario_id: int
    status: str
    duration: int
    container_id: str
    artifacts_copied: bool = False


class WorkerPool:
    """Manages a pool of worker containers for parallel test execution."""

    def __init__(
        self,
        num_workers: int = 4,
        image: str = "doit-orchestrator:latest",
        docker_socket: str = "unix:///var/run/docker.sock",
        work_dir: Optional[str] = None,
        artifacts_dir: Optional[str] = None
    ):
        self.num_workers = num_workers
        self.image = image
        self.docker_client = docker.DockerClient(base_url=docker_socket)
        self.active_containers: list[Container] = []
        self.results: list[TestResult] = []
        self._lock = threading.Lock()
        self.work_dir = work_dir
        self.artifacts_dir = artifacts_dir

    def _run_scenario(self, scenario: TestScenario) -> TestResult:
        """Run a single test scenario in a container."""
        start_time = time.time()
        artifacts_copied = False
        container = None

        print(f"    [Container] Starting scenario {scenario.id}")

        try:
            # Build container run arguments
            # Worker writes artifacts to mounted artifacts directory
            run_kwargs = {
                "detach": True,
                "remove": False,  # Keep container to extract artifacts, then remove manually
                "environment": {
                    "ROLE": "worker",
                    "SCENARIO_ID": str(scenario.id),
                    "SCENARIO_DURATION": str(scenario.duration),
                },
                "name": f"doit-worker-{scenario.id}"
            }

            # Mount worker directory from host if specified (read-only)
            if self.work_dir:
                run_kwargs["volumes"] = {
                    self.work_dir: {"bind": "/work", "mode": "ro"}
                }
                run_kwargs["working_dir"] = "/work"

            # Mount artifacts directory - same path in container as host path
            # Worker writes to /app/tests/artifacts/test_scenario_X which appears on host
            if self.artifacts_dir:
                run_kwargs["volumes"] = run_kwargs.get("volumes", {})
                run_kwargs["volumes"][self.artifacts_dir] = {"bind": self.artifacts_dir, "mode": "rw"}
                # Also set environment so worker knows where to write
                run_kwargs["environment"] = run_kwargs.get("environment", {})
                run_kwargs["environment"]["WORKER_ARTIFACTS_DIR"] = self.artifacts_dir

            print(f"    [Container] Starting worker container...")

            # Run container
            container = self.docker_client.containers.run(
                self.image,
                **run_kwargs
            )

            print(f"    [Container] Container started: {container.id}")

            with self._lock:
                self.active_containers.append(container)

            # Wait for container to finish
            result = container.wait()
            exit_code = result.get('StatusCode', 0)
            print(f"    [Container] Worker {scenario.id} exited with code {exit_code}")

            # Get logs (works on stopped/exited containers)
            logs = container.logs().decode('utf-8')
            print(f"    [Container] Logs: {logs[:500] if logs else '(empty)'}")

            # Artifacts are written directly to mounted artifacts directory
            # Check if artifacts were created
            if self.artifacts_dir:
                scenario_artifacts_dst = os.path.join(self.artifacts_dir, f"test_scenario_{scenario.id}")
                if os.path.exists(scenario_artifacts_dst):
                    artifacts_copied = True
                    print(f"    [Artifact] Copied to: {scenario_artifacts_dst}")
            
            # Remove container after artifacts extracted
            if container:
                try:
                    container.remove(force=True)
                    print(f"    [Container] Removed container")
                except Exception as e:
                    print(f"    [Container] Remove error: {e}")
            
            # Remove from active list
            with self._lock:
                if container in self.active_containers:
                    self.active_containers.remove(container)

            duration = int(time.time() - start_time)
            return TestResult(
                scenario_id=scenario.id,
                status="passed",
                duration=duration,
                container_id=container.id if container else "",
                artifacts_copied=artifacts_copied
            )

        except Exception as e:
            duration = int(time.time() - start_time)
            # Clean up container on error
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            return TestResult(
                scenario_id=scenario.id,
                status=f"failed: {str(e)}",
                duration=duration,
                container_id=container.id if container else "",
                artifacts_copied=False
            )

    def run_parallel(self, scenarios: list[TestScenario]) -> list[TestResult]:
        """Run scenarios in parallel using a worker pool."""
        total_scenarios = len(scenarios)
        completed = 0
        results: list[TestResult] = []

        # Start initial batch of workers
        threads: list[threading.Thread] = []

        def worker_thread(scenario: TestScenario):
            result = self._run_scenario(scenario)
            with self._lock:
                results.append(result)

        # Start up to num_workers threads
        for i in range(min(self.num_workers, total_scenarios)):
            t = threading.Thread(target=worker_thread, args=(scenarios[i],))
            t.start()
            threads.append(t)

        # Wait for a thread to complete, then start next scenario
        next_idx = self.num_workers

        while completed < total_scenarios:
            # Wait for any thread to complete
            for i, t in enumerate(threads):
                t.join(timeout=1)
                if not t.is_alive():
                    # This thread completed
                    completed += 1

                    # Start next scenario if any remaining
                    if next_idx < total_scenarios:
                        new_t = threading.Thread(
                            target=worker_thread,
                            args=(scenarios[next_idx],)
                        )
                        new_t.start()
                        threads[i] = new_t
                        next_idx += 1

                    break

        # Wait for all remaining threads
        for t in threads:
            t.join()

        return results

    def close(self):
        """Clean up resources."""
        # Kill any remaining containers
        for container in self.active_containers:
            try:
                container.kill()
                container.remove(force=True)
            except Exception:
                pass

        self.docker_client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def create_scenarios(count: int = 5, duration: int = 60) -> list[TestScenario]:
    """Create test scenarios."""
    return [TestScenario(id=i+1, duration=duration) for i in range(count)]