from __future__ import annotations

import argparse
import logging
import os
import re
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv

from src.generators.base import ServiceConfig
from src.generators.logs_gen import LogsGenerator
from src.generators.metrics_gen import MetricsGenerator
from src.generators.traces_gen import TracesGenerator
from src.scenarios.error_burst import ErrorBurstScenario
from src.scenarios.normal import NormalScenario
from src.scenarios.slow_trace import SlowTraceScenario
from src.scenarios.spike import SpikeScenario
from src.sink.clickhouse_sink import ClickHouseSink


logging.basicConfig(level=logging.INFO, format="%(message)s")
LOGGER = logging.getLogger(__name__)
SCENARIOS = {
    "normal": NormalScenario,
    "spike": SpikeScenario,
    "error_burst": ErrorBurstScenario,
    "slow_trace": SlowTraceScenario,
}


def main() -> int:
    load_dotenv()
    args = parse_args()
    config = load_config(args.config)
    services = [
        ServiceConfig(name=item["name"], host=item["host"], env=item.get("env", "prod"))
        for item in config["generator"]["services"]
    ]
    metrics_gen = MetricsGenerator(services, args.scenario)
    logs_gen = LogsGenerator(services, args.scenario)
    traces_gen = TracesGenerator(services, args.scenario)
    SCENARIOS[args.scenario]().apply(metrics_gen, logs_gen, traces_gen)

    sink = build_sink(config)
    stop = {"requested": False}

    def handle_shutdown(signum, frame):
        stop["requested"] = True

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    if args.inject:
        inject(args.inject, metrics_gen, logs_gen, traces_gen)

    started = time.monotonic()
    next_inject_at = time.monotonic() + args.inject_interval
    auto_sequence = ["spike", "error_burst", "slow_trace"]
    auto_index = 0

    while not stop["requested"]:
        loop_started = time.perf_counter()
        if args.duration and time.monotonic() - started >= args.duration:
            break
        if args.auto_inject and time.monotonic() >= next_inject_at:
            scenario_name = auto_sequence[auto_index % len(auto_sequence)]
            inject(scenario_name, metrics_gen, logs_gen, traces_gen)
            auto_index += 1
            next_inject_at = time.monotonic() + args.inject_interval

        batch_size = int(config["generator"]["batch_size"])
        metrics = metrics_gen.generate_batch(batch_size)
        traces = traces_gen.generate_batch(max(1, batch_size // 6))
        logs = correlated_logs(logs_gen, traces, max(1, batch_size // 3))
        insert_with_reconnect(sink, "metrics", metrics)
        insert_with_reconnect(sink, "logs", logs)
        insert_with_reconnect(sink, "traces", traces)
        elapsed_ms = int((time.perf_counter() - loop_started) * 1000)
        print_status(active_label(metrics_gen, logs_gen, traces_gen), len(metrics), len(logs), len(traces), elapsed_ms)
        time.sleep(float(config["generator"]["interval_seconds"]))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate real-time AIOps metrics, logs, and traces into ClickHouse.")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "config" / "settings.yaml"))
    parser.add_argument("--scenario", choices=SCENARIOS.keys(), default="normal")
    parser.add_argument("--inject", choices=[name for name in SCENARIOS if name != "normal"])
    parser.add_argument("--auto-inject", action="store_true")
    parser.add_argument("--inject-interval", type=int, default=60)
    parser.add_argument("--duration", type=int)
    return parser.parse_args()


def load_config(path: str) -> Dict[str, Any]:
    content = Path(path).read_text(encoding="utf-8")
    content = re.sub(r"\$\{([^}:]+):-([^}]*)\}", lambda match: os.getenv(match.group(1), match.group(2)), content)
    return yaml.safe_load(content)


def build_sink(config: Dict[str, Any]) -> ClickHouseSink:
    ch = config["clickhouse"]
    while True:
        try:
            sink = ClickHouseSink(ch["host"], ch["port"], ch["database"], ch["user"], ch["password"])
            if sink.health_check():
                return sink
            LOGGER.error("[SINK] ClickHouse health check failed, retrying in 5s")
        except Exception as exc:
            LOGGER.error("[SINK] ClickHouse unavailable, retrying in 5s: %s", exc)
        time.sleep(5)


def insert_with_reconnect(sink: ClickHouseSink, table: str, rows: List[Dict[str, Any]]) -> None:
    sink.insert_batch(table, rows)


def correlated_logs(logs_gen: LogsGenerator, traces: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
    logs = []
    roots = [span for span in traces if span["parent_span_id"] == ""]
    for span in roots[: max(1, min(len(roots), count // 2))]:
        logs.append(logs_gen.generate_log(trace_id=span["trace_id"], span_id=span["span_id"]))
    while len(logs) < count:
        logs.append(logs_gen.generate_log())
    return logs


def inject(name: str, metrics_gen, logs_gen, traces_gen) -> None:
    padded = name.upper().replace("_", " ").ljust(6)
    duration = SCENARIOS[name].DURATION_SECONDS
    print(f"[{timestamp()}] [{padded}] Injecting {name} scenario ({duration}s window)")
    SCENARIOS[name]().apply(metrics_gen, logs_gen, traces_gen)


def active_label(metrics_gen, logs_gen, traces_gen) -> str:
    if metrics_gen.spike_mode:
        return "SPIKE "
    if logs_gen.error_burst_mode:
        return "ERROR "
    if traces_gen.slow_trace_mode:
        return "SLOW  "
    return "NORMAL"


def print_status(label: str, metrics_count: int, logs_count: int, traces_count: int, elapsed_ms: int) -> None:
    print(
        f"[{timestamp()}] [{label}] Inserted {metrics_count} metrics | "
        f"{logs_count} logs | {traces_count} traces in {elapsed_ms}ms",
        flush=True,
    )


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    sys.exit(main())
