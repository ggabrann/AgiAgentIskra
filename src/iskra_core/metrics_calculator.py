from __future__ import annotations
from .facets import Metrics

class MetricsCalculator:
    def from_text(self, text: str) -> Metrics:
        t = text.lower()
        m: Metrics = {'trust': 0.9, 'clarity': 0.6, 'pain': 0.0, 'drift': 0.0, 'chaos': 0.3, 'silence_mass': 0.0}
        if 'больно' in t or '∆' in t: m['pain'] = min(1.0, m['pain'] + 0.7)
        if 'не понимаю' in t or '???' in t: m['clarity'] = max(0.0, m['clarity'] - 0.3)
        if 'потом' in t: m['drift'] = min(1.0, m['drift'] + 0.4)
        return m
