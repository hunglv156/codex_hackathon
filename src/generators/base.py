from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List


@dataclass(frozen=True)
class ServiceConfig:
    name: str
    host: str
    env: str = "prod"


class BaseGenerator(ABC):
    def __init__(self, services: List[ServiceConfig], scenario: str = "normal"):
        if not services:
            raise ValueError("At least one service is required")
        self.services = services
        self.scenario = scenario

    @abstractmethod
    def generate_batch(self, batch_size: int) -> List[Dict]:
        """Generate rows matching the ClickHouse table schema."""

    def set_scenario(self, scenario: str) -> None:
        self.scenario = scenario

    def _now_ms(self) -> datetime:
        now = datetime.now(timezone.utc)
        return now.replace(microsecond=(now.microsecond // 1000) * 1000)
