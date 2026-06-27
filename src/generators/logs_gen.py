from __future__ import annotations

import random
import uuid
from typing import Dict, List, Optional

from faker import Faker

from src.generators.base import BaseGenerator


class LogsGenerator(BaseGenerator):
    LEVELS = ("INFO", "WARN", "ERROR", "DEBUG")
    NORMAL_WEIGHTS = (85, 10, 4, 1)
    ERROR_BURST_WEIGHTS = (15, 4, 80, 1)

    def __init__(self, services, scenario: str = "normal"):
        super().__init__(services, scenario)
        self.fake = Faker()
        self.error_burst_mode = scenario == "error_burst"

    def set_error_burst_mode(self, enabled: bool) -> None:
        self.error_burst_mode = enabled
        self.scenario = "error_burst" if enabled else "normal"

    def generate_batch(self, batch_size: int) -> List[Dict]:
        return [self.generate_log() for _ in range(batch_size)]

    def generate_log(self, trace_id: Optional[str] = None, span_id: str = "") -> Dict:
        service = random.choice(self.services)
        level = random.choices(
            self.LEVELS,
            weights=self.ERROR_BURST_WEIGHTS if self.error_burst_mode else self.NORMAL_WEIGHTS,
            k=1,
        )[0]
        return {
            "trace_id": trace_id or str(uuid.uuid4()),
            "span_id": span_id,
            "service_name": service.name,
            "host": service.host,
            "timestamp": self._now_ms(),
            "level": level,
            "message": self._message(level),
            "logger": f"{service.name}.app",
        }

    def _message(self, level: str) -> str:
        if self.error_burst_mode and level == "ERROR":
            used = random.randint(90, 100)
            maximum = 100
            return f"FATAL: database connection pool exhausted ({used}/{maximum} connections used)"
        duration = random.randint(10, 600)
        messages = {
            "INFO": [
                f"Request processed successfully in {duration}ms",
                f"Cache hit for key={self.fake.slug()}, ttl={random.randint(30, 600)}s",
            ],
            "WARN": [
                f"Response time {duration}ms exceeded SLA threshold 200ms",
                f"Retry attempt {random.randint(1, 3)}/3 for downstream service",
            ],
            "ERROR": [
                f"Connection refused: {self.fake.hostname()}:{random.choice([5432, 6379, 9000])}",
                f"Null pointer exception in {self.fake.word().title()}Service.{self.fake.word()}()",
            ],
            "DEBUG": [
                f"Debug payload size={random.randint(128, 8192)} bytes",
                f"Feature flag {self.fake.word()} evaluated to {random.choice(['true', 'false'])}",
            ],
        }
        return random.choice(messages[level])
