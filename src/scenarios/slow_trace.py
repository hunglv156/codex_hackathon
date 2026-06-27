from __future__ import annotations

import threading


class SlowTraceScenario:
    """Slow root traces and db.query dominance for 45 seconds, then normal."""

    name = "slow_trace"
    DURATION_SECONDS = 45

    def apply(self, metrics_gen, logs_gen, traces_gen):
        traces_gen.set_slow_trace_mode(True)
        timer = threading.Timer(self.DURATION_SECONDS, traces_gen.set_slow_trace_mode, args=(False,))
        timer.daemon = True
        timer.start()
        return timer
