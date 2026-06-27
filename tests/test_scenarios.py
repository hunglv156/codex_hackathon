import time

from src.generators.base import ServiceConfig
from src.generators.logs_gen import LogsGenerator
from src.generators.metrics_gen import MetricsGenerator
from src.generators.traces_gen import TracesGenerator
from src.scenarios.spike import SpikeScenario


def test_spike_scenario_auto_reverts():
    services = [ServiceConfig("order-service", "host-01")]
    metrics = MetricsGenerator(services)
    logs = LogsGenerator(services)
    traces = TracesGenerator(services)
    scenario = SpikeScenario()
    scenario.DURATION_SECONDS = 0.01
    scenario.apply(metrics, logs, traces)
    assert metrics.spike_mode is True
    time.sleep(0.05)
    assert metrics.spike_mode is False
