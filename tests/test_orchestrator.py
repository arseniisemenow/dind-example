"""Tests for orchestrator - verify parallel execution timing."""

import time
import threading
from unittest.mock import MagicMock, patch

import pytest

from doit.orchestrator import TestScenario, TestResult, WorkerPool


class MockContainer:
    """Mock Docker container for testing."""

    def __init__(self, container_id: str, duration: int = 1):
        self.id = container_id
        self._duration = duration

    def wait(self):
        time.sleep(self._duration)
        return {'StatusCode': 0}

    def logs(self):
        return f"RESULT:scenario=1:status=passed:duration={self._duration}s".encode()

    def remove(self, force=False):
        pass


class TestParallelExecution:
    """Tests to verify parallel execution behavior."""

    def test_4_workers_4_scenarios_should_take_approx_60s(self):
        """With 4 workers and 4 scenarios of 60s each, total time should be ~60s, not 240s."""
        # This is the key test: parallel execution should be ~60s, not 240s
        with patch('docker.DockerClient') as MockClient:
            # Setup mock to return containers that "run" for 2 seconds
            call_count = [0]

            def mock_containers_run(*args, **kwargs):
                call_count[0] += 1
                return MockContainer(f"container-{call_count[0]}", duration=2)

            mock_client = MagicMock()
            mock_client.containers.run = mock_containers_run
            MockClient.return_value = mock_client

            pool = WorkerPool(num_workers=4, image="test-image")

            scenarios = [TestScenario(id=i+1, duration=2) for i in range(4)]

            start = time.time()
            results = pool.run_parallel(scenarios)
            elapsed = time.time() - start

            # With 4 workers and 4 scenarios of 2s each:
            # Sequential: 4 * 2 = 8s
            # Parallel: should be ~2s (all run simultaneously)
            # Allow some overhead but should be well under 5s
            assert elapsed < 5, f"Expected ~2s but took {elapsed:.1f}s - not parallel!"
            assert elapsed >= 1.5, f"Too fast ({elapsed:.1f}s) - test may be broken"
            assert len(results) == 4
            assert all(r.status == "passed" for r in results)

    def test_4_workers_5_scenarios_correct_behavior(self):
        """With 4 workers and 5 scenarios, we expect first 4 to run in parallel, then 5th."""
        with patch('docker.DockerClient') as MockClient:
            # Track when each scenario "starts"
            start_times = []

            def mock_containers_run(*args, **kwargs):
                scenario_id = kwargs.get('environment', {}).get('SCENARIO_ID', '1')
                start_times.append((scenario_id, time.time()))
                # All scenarios take 2s
                return MockContainer(f"container-{scenario_id}", duration=2)

            mock_client = MagicMock()
            mock_client.containers.run = mock_containers_run
            MockClient.return_value = mock_client

            pool = WorkerPool(num_workers=4, image="test-image")

            scenarios = [TestScenario(id=i+1, duration=2) for i in range(5)]

            start = time.time()
            results = pool.run_parallel(scenarios)
            elapsed = time.time() - start

            # First 4 should start roughly at the same time (within 1s)
            # 5th should start after first one completes (~2s later)
            # Total should be ~4s (2s for first batch + 2s for last one)
            assert elapsed < 8, f"Expected ~4s but took {elapsed:.1f}s"
            assert elapsed >= 3, f"Too fast ({elapsed:.1f}s) - test may be broken"
            assert len(results) == 5
            assert all(r.status == "passed" for r in results)

    def test_single_worker_sequential(self):
        """With 1 worker, execution should be sequential."""
        with patch('docker.DockerClient') as MockClient:
            call_count = [0]

            def mock_containers_run(*args, **kwargs):
                call_count[0] += 1
                return MockContainer(f"container-{call_count[0]}", duration=1)

            mock_client = MagicMock()
            mock_client.containers.run = mock_containers_run
            MockClient.return_value = mock_client

            pool = WorkerPool(num_workers=1, image="test-image")

            scenarios = [TestScenario(id=i+1, duration=1) for i in range(3)]

            start = time.time()
            results = pool.run_parallel(scenarios)
            elapsed = time.time() - start

            # With 1 worker and 3 scenarios of 1s each: ~3s
            assert elapsed < 6, f"Expected ~3s but took {elapsed:.1f}s"
            assert elapsed >= 2, f"Too fast ({elapsed:.1f}s)"
            assert len(results) == 3


class TestScenarios:
    """Tests for scenario creation and handling."""

    def test_create_scenarios_default(self):
        """Test default scenario creation."""
        scenarios = [
            TestScenario(id=1, duration=60),
            TestScenario(id=2, duration=60),
            TestScenario(id=3, duration=60),
            TestScenario(id=4, duration=60),
            TestScenario(id=5, duration=60),
        ]

    def test_create_scenarios_custom_count(self):
        """Test custom scenario count."""
        from doit.orchestrator import create_scenarios

        scenarios = create_scenarios(count=10, duration=30)
        assert len(scenarios) == 10
        assert all(s.duration == 30 for s in scenarios)
        assert [s.id for s in scenarios] == list(range(1, 11))

    def test_scenario_dataclass(self):
        """Test scenario dataclass."""
        scenario = TestScenario(id=42, duration=120)
        assert scenario.id == 42
        assert scenario.duration == 120


class TestResults:
    """Tests for test result handling."""

    def test_result_dataclass(self):
        """Test result dataclass."""
        result = TestResult(
            scenario_id=1,
            status="passed",
            duration=60,
            container_id="abc123"
        )
        assert result.scenario_id == 1
        assert result.status == "passed"
        assert result.duration == 60
        assert result.container_id == "abc123"

    def test_result_failure(self):
        """Test failure result."""
        result = TestResult(
            scenario_id=1,
            status="failed: connection error",
            duration=5,
            container_id=""
        )
        assert result.status.startswith("failed")


class TestWorkerPool:
    """Tests for WorkerPool class."""

    def test_pool_initialization(self):
        """Test pool can be initialized."""
        with patch('docker.DockerClient') as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            pool = WorkerPool(num_workers=4, image="my-image")
            assert pool.num_workers == 4
            assert pool.image == "my-image"

    def test_pool_context_manager(self):
        """Test pool works as context manager."""
        with patch('docker.DockerClient') as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with WorkerPool(num_workers=2) as pool:
                assert pool.num_workers == 2

            # close() should be called automatically
            mock_client.close.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])