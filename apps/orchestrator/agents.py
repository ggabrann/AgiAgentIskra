"""Utility LangGraph nodes for the Искра orchestrator.

These nodes provide lightweight behaviour so that the demo LangGraph
pipeline defined in :mod:`langgraph_main` can be executed without raising
runtime errors.  The implementation focuses on deterministic, inspectable
state transitions rather than LLM calls so that unit tests and local
experiments remain reproducible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, cast

if TYPE_CHECKING:  # pragma: no cover - used only for type checkers
    from .langgraph_main import AgentState


def _clone_state(state: "AgentState") -> "AgentState":
    """Return a shallow copy of *state* with duplicated list members."""

    cloned: Dict[str, Any] = dict(state)
    for key in ("claims", "evidence_ids", "action_log"):
        if key in cloned and isinstance(cloned[key], list):
            cloned[key] = list(cloned[key])
        else:
            cloned.setdefault(key, [])
    return cast("AgentState", cloned)


class AgentNode:
    """First step of the graph – collects initial claims."""

    def __init__(self, role: str = "Research") -> None:
        self.role = role

    def __call__(self, state: "AgentState") -> "AgentState":
        new_state = _clone_state(state)
        query = state.get("query", "").strip()
        claim = (
            f"Предварительное предположение по запросу: {query[:80]}"
            if query
            else "Пользовательский запрос не задан, добавлена заглушка для обсуждения."
        )
        if claim not in new_state["claims"]:
            new_state["claims"].append(claim)
        new_state["action_log"].append(f"{self.role} node processed query")
        new_state["next_action"] = "debate"
        return new_state


class DebateNode:
    """Evaluates collected claims and prepares evidence identifiers."""

    def __call__(self, state: "AgentState") -> "AgentState":
        new_state = _clone_state(state)
        assessments: List[str] = []
        for idx, claim in enumerate(new_state["claims"], start=1):
            label = "supported" if len(claim) <= 200 else "needs-review"
            assessments.append(label)
            new_state["action_log"].append(
                f"Debate review for claim {idx}: {label}"
            )
            # In lieu of real retrieval we attach a deterministic evidence id
            evidence_id = f"EVD-{idx:03d}"
            if evidence_id not in new_state["evidence_ids"]:
                new_state["evidence_ids"].append(evidence_id)
        new_state["next_action"] = "judge"
        new_state["debate_assessments"] = assessments
        return new_state


class JudgeNode:
    """Aggregates debate assessments into a final review score."""

    def __init__(self, acceptance_threshold: float = 0.6) -> None:
        self.acceptance_threshold = acceptance_threshold

    def __call__(self, state: "AgentState") -> "AgentState":
        new_state = _clone_state(state)
        assessments: List[str] = state.get("debate_assessments", [])
        if assessments:
            supported = sum(1 for item in assessments if item == "supported")
            score = supported / len(assessments)
        else:
            score = 0.0
        new_state["review_score"] = round(score, 2)
        verdict = "complete" if score >= self.acceptance_threshold else "refine"
        new_state["next_action"] = verdict
        new_state["action_log"].append(
            f"Judge verdict: {verdict} (score={score:.2f}, threshold={self.acceptance_threshold:.2f})"
        )
        new_state["verdict"] = verdict
        return new_state


__all__ = ["AgentNode", "DebateNode", "JudgeNode"]
