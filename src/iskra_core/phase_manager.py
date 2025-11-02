from __future__ import annotations
from typing import Literal
from .facets import Metrics

Phase = Literal['Тьма','Переход','Ясность','Эхо','Молчание','Эксперимент','Растворение','Реализация']

class PhaseManager:
    def __init__(self, phase: Phase = 'Переход'):
        self.phase: Phase = phase
    def step(self, metrics: Metrics) -> Phase:
        if metrics.get('silence_mass', 0) > 0.6:
            self.phase = 'Молчание'
        elif metrics.get('chaos', 0) > 0.6:
            self.phase = 'Переход'
        elif metrics.get('clarity', 0) > 0.7:
            self.phase = 'Ясность'
        return self.phase
