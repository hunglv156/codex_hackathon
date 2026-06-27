from __future__ import annotations

import threading


class SpikeScenario:
    """CPU spike + latency spike for 30 seconds, then normal."""

    name = "spike"
    DURATION_SECONDS = 30

    def apply(self, metrics_gen, logs_gen, traces_gen):
        metrics_gen.set_spike_mode(True)
        timer = threading.Timer(self.DURATION_SECONDS, metrics_gen.set_spike_mode, args=(False,))
        timer.daemon = True
        timer.start()
        return timer
