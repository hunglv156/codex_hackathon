from src.generators.base import ServiceConfig
from src.generators.logs_gen import LogsGenerator
from src.generators.metrics_gen import MetricsGenerator
from src.generators.traces_gen import TracesGenerator


SERVICES = [ServiceConfig("order-service", "host-01")]


def test_metrics_generator_normal_schema():
    rows = MetricsGenerator(SERVICES).generate_batch(20)
    assert rows
    assert set(rows[0]) == {"service_name", "host", "env", "timestamp", "metric_name", "value", "unit"}


def test_metrics_generator_spike_values():
    generator = MetricsGenerator(SERVICES)
    generator.set_spike_mode(True)
    rows = generator.generate_batch(20)
    assert any(row["metric_name"] == "cpu_usage" and row["value"] > 80 for row in rows)


def test_logs_generator_level_distribution():
    rows = LogsGenerator(SERVICES).generate_batch(1000)
    error_rate = sum(1 for row in rows if row["level"] == "ERROR") / len(rows)
    assert error_rate < 0.10


def test_traces_generator_parent_child_relationship():
    rows = TracesGenerator(SERVICES).generate_trace()
    root = next(row for row in rows if row["parent_span_id"] == "")
    children = [row for row in rows if row["parent_span_id"]]
    assert children
    assert all(row["parent_span_id"] == root["span_id"] for row in children)
