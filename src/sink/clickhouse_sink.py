from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

try:
    import clickhouse_connect
except ModuleNotFoundError:
    class _MissingClickHouseConnect:
        @staticmethod
        def get_client(*args, **kwargs):
            raise RuntimeError("clickhouse-connect is required. Install dependencies with pip install -r requirements.txt")

    clickhouse_connect = _MissingClickHouseConnect()


LOGGER = logging.getLogger(__name__)


class ClickHouseSink:
    ALLOWED_TABLES = {"metrics", "logs", "traces", "aiops.metrics", "aiops.logs", "aiops.traces"}

    def __init__(self, host, port, database, user, password):
        self.client = clickhouse_connect.get_client(
            host=host,
            port=int(port),
            database=database,
            username=user,
            password=password,
        )

    def insert_batch(self, table: str, rows: List[Dict[str, Any]]) -> bool:
        if not rows:
            return True
        if table not in self.ALLOWED_TABLES:
            raise ValueError(f"Refusing to write to unsupported table: {table}")

        columns = list(rows[0].keys())
        data = [[row[column] for column in columns] for row in rows]
        for attempt in range(3):
            started = time.perf_counter()
            try:
                self.client.insert(table, data, column_names=columns)
                latency_ms = int((time.perf_counter() - started) * 1000)
                LOGGER.info("[SINK] Inserted %s rows into %s in %sms", len(rows), table, latency_ms)
                return True
            except Exception as exc:
                if attempt == 2:
                    LOGGER.error("[SINK] Failed to insert %s rows into %s after 3 attempts: %s", len(rows), table, exc)
                    return False
                LOGGER.warning("[SINK] Insert failed for %s, retrying: %s", table, exc)
                time.sleep(2**attempt)
        return False

    def health_check(self) -> bool:
        try:
            result = self.client.query("SELECT 1")
            return bool(result.result_rows and result.result_rows[0][0] == 1)
        except Exception as exc:
            LOGGER.error("[SINK] Health check failed: %s", exc)
            return False
