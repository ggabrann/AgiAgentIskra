from __future__ import annotations
from typing import Protocol, TypedDict, Literal, Dict, Any, List

FacetName = Literal['Kain','Pino','Sam','Anhantra','Huyndun','Iskriv','Iskra','Maki']

class Metrics(TypedDict, total=False):
    trust: float
    clarity: float
    pain: float
    drift: float
    chaos: float
    echo: float
    silence_mass: float
    mirror_sync: float

class Context(TypedDict, total=False):
    phase: str
    state: str
    ritual: str
    history: List[str]

class Facet(Protocol):
    name: FacetName
    def should_activate(self, metrics: Metrics, ctx: Context) -> bool: ...
    def respond(self, text: str, metrics: Metrics, ctx: Context) -> str: ...
