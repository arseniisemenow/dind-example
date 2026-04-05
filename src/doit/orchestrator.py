"""Docker orchestrator for parallel test execution."""

import time
import threading
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


class WorkerPool:
    """Manages a pool of worker containers for parallel test execution."""

    def __init__(
        self,
        num_workers: int = 4,
        image: str = "doit-worker:latest",
        docker_socket: str = "unix:///var/run/docker.sock"
    ):
        self.num_workers = num_workers
        self.image = image
        self.docker_client = docker.DockerClient(base_url=docker_socket)
        self.active_containers: list[Container] = []
        self.results: list[TestResult] = []
        self._lock = threading.Lock()

    def _run_scenario(self, scenario: TestScenario) -> TestResult:
        """Run a single test scenario in a container."""
        start_time = time.time()

        try:
            # Run container with scenario ID and duration, and set role to worker
            container = self.docker_client.containers.run(
                self.image,
                detach=True,
                remove=False,
                environment={
                    "ROLE": "worker",
                    "SCENARIO_ID": str(scenario.id),
                    "SCENARIO_DURATION": str(scenario.duration)
                },
                name=f"doit-worker-{scenario.id}"
            )

            with self._lock:
                self.active_containers.append(container)

            # Wait for container to finish
            container.wait()

            # Get logs
            logs = container.logs().decode('utf-8')

            # Remove container after completion
            container.remove(force=True)

            with self._lock:
                self.active_containers.remove(container)

            duration = int(time.time() - start_time)
            return TestResult(
                scenario_id=scenario.id,
                status="passed",
                duration=duration,
                container_id=container.id
            )

        except Exception as e:
            duration = int(time.time() - start_time)
            return TestResult(
                scenario_id=scenario.id,
                status=f"failed: {str(e)}",
                duration=duration,
                container_id=""
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