from __future__ import annotations
import time
from typing import Any
from prometheus_client import Counter, Histogram

facet_switch_total = Counter(
    "iskra_facet_switch_total", "Facet switches", labelnames=["facet"]
)
phase_switch_total = Counter(
    "iskra_phase_switch_total", "Phase switches", labelnames=["phase"]
)
activation_latency = Histogram(
    "iskra_activation_latency_seconds", "Latency of activation flow"
)

def log_facet_switch(facet: str) -> None:
    facet_switch_total.labels(facet=facet).inc()

def log_phase_switch(phase: str) -> None:
    phase_switch_total.labels(phase=phase).inc()

def timed() -> Any:
    def wrap(fn):
        def inner(*a, **kw):
            start = time.time()
            try:
                return fn(*a, **kw)
            finally:
                activation_latency.observe(time.time() - start)
        return inner
    return wrap
