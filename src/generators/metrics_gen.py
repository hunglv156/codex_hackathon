from __future__ import annotations

import random
from typing import Dict, List, Tuple

from src.generators.base import BaseGenerator


MetricSpec = Tuple[str, str, float, float, float, float]


class MetricsGenerator(BaseGenerator):
    METRICS: Dict[str, MetricSpec] = {
        "cpu_usage": ("percent", 40.0, 10.0, 5.0, 0.0, 100.0),
        "mem_bytes": ("bytes", 3 * 1024**3, 1024**3, 200 * 1024**2, 0.0, 16 * 1024**3),
        "latency_p99": ("ms", 100.0, 50.0, 20.0, 1.0, 10000.0),
        "error_rate": ("percent", 1.0, 1.0, 0.5, 0.0, 100.0),
        "request_count": ("count", 300.0, 200.0, 50.0, 0.0, 5000.0),
        "gc_pause_ms": ("ms", 17.5, 12.5, 5.0, 0.0, 1000.0),
    }

    def __init__(self, services, scenario: str = "normal"):
        super().__init__(services, scenario)
        self.spike_mode = scenario == "spike"

    def set_spike_mode(self, enabled: bool) -> None:
        self.spike_mode = enabled
        self.scenario = "spike" if enabled else "normal"

    def generate_batch(self, batch_size: int) -> List[Dict]:
        rows: List[Dict] = []
        while len(rows) < batch_size:
            service = random.choice(self.services)
            metric_names = random.sample(list(self.METRICS), random.randint(3, 5))
            if self.spike_mode and "cpu_usage" not in metric_names:
                metric_names[0] = "cpu_usage"
            for metric_name in metric_names:
                if len(rows) >= batch_size:
                    break
                unit, value = self._metric_value(metric_name)
                rows.append(
                    {
                        "service_name": service.name,
                        "host": service.host,
                        "env": service.env,
                        "timestamp": self._now_ms(),
                        "metric_name": metric_name,
                        "value": value,
                        "unit": unit,
                    }
                )
        return rows

    def _metric_value(self, metric_name: str) -> Tuple[str, float]:
        unit, base, spread, noise, min_value, max_value = self.METRICS[metric_name]
        if self.spike_mode and metric_name == "cpu_usage":
            return unit, random.uniform(85.0, 95.0)
        if self.spike_mode and metric_name == "latency_p99":
            normal = self._normal_value(base, spread, noise, min_value, max_value)
            return unit, min(max_value, normal * random.uniform(5.0, 10.0))
        if metric_name == "request_count":
            value = random.gauss(base, noise)
        else:
            value = self._normal_value(base, spread, noise, min_value, max_value)
        return unit, min(max_value, max(min_value, value))

    @staticmethod
    def _normal_value(base: float, spread: float, noise: float, min_value: float, max_value: float) -> float:
        center = random.uniform(base - spread, base + spread)
        return min(max_value, max(min_value, random.gauss(center, noise)))
