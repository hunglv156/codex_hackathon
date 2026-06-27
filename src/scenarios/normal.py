from __future__ import annotations


class NormalScenario:
    name = "normal"

    def apply(self, metrics_gen, logs_gen, traces_gen):
        metrics_gen.set_spike_mode(False)
        logs_gen.set_error_burst_mode(False)
        traces_gen.set_slow_trace_mode(False)
