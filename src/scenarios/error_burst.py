from __future__ import annotations

import threading


class ErrorBurstScenario:
    """ERROR log flood for 20 seconds, then normal."""

    name = "error_burst"
    DURATION_SECONDS = 20

    def apply(self, metrics_gen, logs_gen, traces_gen):
        logs_gen.set_error_burst_mode(True)
        timer = threading.Timer(self.DURATION_SECONDS, logs_gen.set_error_burst_mode, args=(False,))
        timer.daemon = True
        timer.start()
        return timer
