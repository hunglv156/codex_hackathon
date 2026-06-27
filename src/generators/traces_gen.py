from __future__ import annotations

import json
import random
import uuid
from datetime import timedelta
from typing import Dict, List

from src.generators.base import BaseGenerator


class TracesGenerator(BaseGenerator):
    RESOURCES = ("orders", "payments", "inventory", "users")
    CHILD_OPERATIONS = ("db.query", "cache.get", "rpc.call")

    def __init__(self, services, scenario: str = "normal"):
        super().__init__(services, scenario)
        self.slow_trace_mode = scenario == "slow_trace"

    def set_slow_trace_mode(self, enabled: bool) -> None:
        self.slow_trace_mode = enabled
        self.scenario = "slow_trace" if enabled else "normal"

    def generate_batch(self, batch_size: int) -> List[Dict]:
        rows: List[Dict] = []
        while len(rows) < batch_size:
            rows.extend(self.generate_trace()[: max(0, batch_size - len(rows))])
        return rows

    def generate_trace(self) -> List[Dict]:
        service = random.choice(self.services)
        trace_id = str(uuid.uuid4())
        root_span_id = self._span_id()
        start_time = self._now_ms()
        resource = random.choice(self.RESOURCES)
        root_duration = random.uniform(2000.0, 8000.0) if self.slow_trace_mode else random.uniform(50.0, 200.0)
        spans = [
            {
                "trace_id": trace_id,
                "span_id": root_span_id,
                "parent_span_id": "",
                "service_name": service.name,
                "operation": f"HTTP GET /api/v1/{resource}",
                "start_time": start_time,
                "duration_ms": root_duration,
                "status_code": self._status_code(),
                "attributes": json.dumps(
                    {
                        "http.method": "GET",
                        "http.url": f"/api/v1/{resource}",
                        "http.status_code": 200,
                    }
                ),
            }
        ]
        child_count = random.randint(2, 4)
        operations = random.sample(self.CHILD_OPERATIONS, min(child_count, len(self.CHILD_OPERATIONS)))
        if child_count > len(operations):
            operations.append(random.choice(self.CHILD_OPERATIONS))
        for index, operation in enumerate(operations):
            if self.slow_trace_mode and operation == "db.query":
                duration = root_duration * random.uniform(0.7, 0.8)
                attributes = {"db.query": "SELECT * FROM orders WHERE ...", "db.rows_examined": 500000}
            else:
                duration = random.uniform(10.0, 50.0)
                attributes = {"component": operation}
            spans.append(
                {
                    "trace_id": trace_id,
                    "span_id": self._span_id(),
                    "parent_span_id": root_span_id,
                    "service_name": service.name,
                    "operation": operation,
                    "start_time": start_time + timedelta(milliseconds=random.randint(1, 20) * (index + 1)),
                    "duration_ms": duration,
                    "status_code": self._status_code(),
                    "attributes": json.dumps(attributes),
                }
            )
        return spans

    @staticmethod
    def _span_id() -> str:
        return uuid.uuid4().hex[:16]

    @staticmethod
    def _status_code() -> int:
        return random.choices([0, 1, 2], weights=[95, 4, 1], k=1)[0]
