"""Conversational query state and the delta engine.

This module is the spine of ZAI. The language model never emits SQL and never
emits figures; it emits a *delta* against a small, closed set of dimensions.
Applying a delta is pure, total and cheap, which is why there is no repair loop
anywhere in this system.

Refinement semantics fall out of the data structure rather than being coded:
  - a delta on an unoccupied dimension accumulates  ("Jordan" + "education")
  - a delta on an occupied dimension replaces       ("Jordan" -> "Egypt")
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

DIMENSIONS = ("country", "region", "sector", "status", "partner", "risk_level")
OPERATIONS = ("set", "add", "remove", "clear")


class DeltaOp(BaseModel):
    op: str
    values: List[str] = Field(default_factory=list)


class QueryState(BaseModel):
    """Everything that defines the current view of the portfolio."""

    filters: Dict[str, List[str]] = Field(default_factory=dict)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    attention_only: bool = False
    text: Optional[str] = None

    def is_empty(self) -> bool:
        return not (self.filters or self.year_from or self.year_to
                    or self.attention_only or self.text)

    def describe(self) -> str:
        """Human-readable state, used in the model prompt for follow-up turns."""
        if self.is_empty():
            return "entire portfolio, no filters applied"
        parts = []
        for dim, vals in sorted(self.filters.items()):
            if not vals:
                continue
            # Long value lists make the chip unreadable and hide the filters
            # that actually matter.
            shown = ", ".join(vals[:2])
            extra = f" +{len(vals) - 2} more" if len(vals) > 2 else ""
            parts.append(f"{dim}={shown}{extra}")
        if self.year_from or self.year_to:
            parts.append(f"years={self.year_from or 'any'}-{self.year_to or 'any'}")
        if self.attention_only:
            parts.append("requiring executive attention")
        if self.text:
            parts.append(f'text~"{self.text}"')
        return "; ".join(parts)


class DeltaError(ValueError):
    """Raised when a model-produced delta references unknown fields or values."""

    def __init__(self, message: str, *, dimension: str | None = None,
                 value: str | None = None) -> None:
        super().__init__(message)
        self.dimension = dimension
        self.value = value


def validate_delta(delta: Dict[str, Any], vocabulary: Dict[str, List[str]]) -> None:
    """Reject a malformed delta *before* it touches state.

    This is the entire error surface of the query path. Contrast with generated
    SQL, whose failure modes are unbounded and only discoverable at execution.
    """
    if not isinstance(delta, dict):
        raise DeltaError("delta must be an object")

    for key, spec in delta.items():
        if key in ("year_from", "year_to"):
            if spec is not None and not isinstance(spec, int):
                raise DeltaError(f"{key} must be an integer or null")
            continue
        if key == "attention_only":
            if not isinstance(spec, bool):
                raise DeltaError("attention_only must be a boolean")
            continue
        if key == "text":
            if spec is not None and not isinstance(spec, str):
                raise DeltaError("text must be a string or null")
            continue
        if key not in DIMENSIONS:
            raise DeltaError(f"unknown dimension '{key}'", dimension=key)
        if not isinstance(spec, dict) or "op" not in spec:
            raise DeltaError(f"dimension '{key}' requires an object with 'op'")
        if spec["op"] not in OPERATIONS:
            raise DeltaError(f"unknown operation '{spec['op']}' on '{key}'")
        allowed = set(vocabulary.get(key, []))
        for value in spec.get("values", []) or []:
            if value not in allowed:
                raise DeltaError(
                    f"value '{value}' is not valid for dimension '{key}'",
                    dimension=key, value=value)


def apply_delta(state: QueryState, delta: Dict[str, Any]) -> QueryState:
    """Return a new state with the delta applied. Never mutates the input."""
    new = QueryState(**copy.deepcopy(state.model_dump()))

    for key, spec in delta.items():
        if key in ("year_from", "year_to"):
            setattr(new, key, spec)
            continue
        if key == "attention_only":
            new.attention_only = spec
            continue
        if key == "text":
            new.text = spec
            continue

        op = spec["op"]
        values = spec.get("values", []) or []
        current = new.filters.get(key, [])

        if op == "clear":
            new.filters.pop(key, None)
        elif op == "set":
            # Same dimension referenced again -> replace, not accumulate.
            new.filters[key] = list(dict.fromkeys(values))
        elif op == "add":
            new.filters[key] = list(dict.fromkeys(current + values))
        elif op == "remove":
            remaining = [v for v in current if v not in values]
            if remaining:
                new.filters[key] = remaining
            else:
                new.filters.pop(key, None)

    new.filters = {k: v for k, v in new.filters.items() if v}
    return new


def apply_filters(projects: List[Dict[str, Any]], state: QueryState) -> List[Dict[str, Any]]:
    """Evaluate the state against the dataset. Pure, in-memory, sub-millisecond."""
    rows = projects

    for dim, values in state.filters.items():
        allowed = set(values)
        rows = [r for r in rows if r.get(dim) in allowed]

    if state.year_from is not None:
        rows = [r for r in rows if r["end_year"] >= state.year_from]
    if state.year_to is not None:
        rows = [r for r in rows if r["start_year"] <= state.year_to]
    if state.attention_only:
        rows = [r for r in rows if r["attention_required"]]
    if state.text:
        needle = state.text.lower()
        rows = [r for r in rows
                if needle in r["name"].lower() or needle in r["description"].lower()]

    return rows