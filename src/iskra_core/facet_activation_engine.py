from __future__ import annotations
from typing import List, Dict
from .facets import Metrics, Context, FacetName

THRESHOLDS: Dict[FacetName, Dict[str, tuple[float, float]]] = {
    'Kain': {'pain': (0.7, 1.01)},
    'Pino': {'pain': (0.5, 0.7)},
    'Sam': {'clarity': (0.0, 0.7)},
    'Anhantra': {'trust': (0.0, 0.75)},
    'Huyndun': {'chaos': (0.6, 1.01)},
    'Iskriv': {'drift': (0.3, 1.01)},
    'Iskra': {},
    'Maki': {},
}

class FacetActivationEngine:
    def __init__(self) -> None:
        self.last_active: List[FacetName] = []

    def select_facets(self, metrics: Metrics, ctx: Context) -> List[FacetName]:
        order = {'Anhantra': 0, 'Kain': 1, 'Sam': 2, 'Iskra': 3, 'Iskriv': 4, 'Pino': 5, 'Huyndun': 6, 'Maki': 7}
        active: List[FacetName] = []
        for facet, cond in THRESHOLDS.items():
            if not cond:
                continue
            for m, (mn, mx) in cond.items():
                val = float(metrics.get(m, 0.0))
                if mn <= val < mx:
                    active.append(facet)
                    break
        active.sort(key=lambda x: order.get(x, 99))
        self.last_active = active
        return active
