"""Query orchestration and conversation session management.

One turn is: plan (model) -> validate -> apply delta -> filter -> compute ->
assemble the four output channels. The model touches only the first step.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from threading import Lock
import re
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core import aggregates
from app.core.state import DeltaError, QueryState, apply_delta, apply_filters, validate_delta
from app.data.repository import alias_index, load_projects, vocabulary

log = logging.getLogger("zai.engine")


# Words that follow a locative preposition but are not places.
_NON_PLACE = {
    "the", "our", "all", "any", "this", "that", "which", "what", "total",
    "progress", "planning", "place", "detail", "details", "risk", "attention",
    "projects", "project", "portfolio", "general", "terms", "years", "year",
    "من", "في", "كل", "هذا", "التي",
}


def detect_unknown_place(question: str, alias_idx: Dict[str, Any]) -> List[str]:
    """Find place-like terms the portfolio does not contain.

    Generic by construction: a term is 'unknown' only because it is absent from
    the vocabulary built out of the dataset. No hardcoded list of countries.

    Two cues, both narrow enough to avoid false positives:
      - a word following a locative preposition ("projects in Ruritania")
      - a short all-capitals acronym ("UAE")
    """
    known = {k.lower() for k in alias_idx}
    found: List[str] = []

    for match in re.finditer(
        r"\b(?:in|from|at|across|within|في|من)\s+([A-Za-z\u0600-\u06FF][\w\u0600-\u06FF'-]{1,24})",
        question, flags=re.IGNORECASE,
    ):
        term = match.group(1).strip(" ?.,!")
        if term.lower() in _NON_PLACE or term.isdigit():
            continue
        if term.lower() not in known:
            found.append(term)

    for match in re.finditer(r"\b([A-Z]{2,5})\b", question):
        acronym = match.group(1)
        if acronym.lower() not in known and acronym.lower() not in _NON_PLACE:
            found.append(acronym)

    # Preserve order, drop duplicates and case-variant repeats.
    seen, unique = set(), []
    for term in found:
        if term.lower() not in seen:
            seen.add(term.lower())
            unique.append(term)
    return unique


def detect_language(text: str) -> str:
    """Code-side detection. Deliberately not delegated to the model."""
    arabic = sum(1 for ch in text if "\u0600" <= ch <= "\u06FF")
    return "ar" if arabic >= 2 else "en"


@dataclass
class Session:
    id: str
    state: QueryState = field(default_factory=QueryState)
    history: List[Dict[str, str]] = field(default_factory=list)
    documents: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    touched_at: float = field(default_factory=time.time)


class SessionStore:
    """In-process store. Swap for Redis when horizontally scaling."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}
        self._lock = Lock()

    def get_or_create(self, session_id: Optional[str]) -> Session:
        with self._lock:
            self._evict_expired()
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                session.touched_at = time.time()
                return session
            new_id = session_id or uuid.uuid4().hex
            session = Session(id=new_id)
            self._sessions[new_id] = session
            return session

    def _evict_expired(self) -> None:
        cutoff = time.time() - settings.session_ttl_seconds
        for key in [k for k, v in self._sessions.items() if v.touched_at < cutoff]:
            self._sessions.pop(key, None)

    def count(self) -> int:
        return len(self._sessions)


sessions = SessionStore()


def _contextual_follow_ups(state: QueryState, rows: List[Dict[str, Any]],
                           language: str) -> List[str]:
    """Follow-up chips that reflect the current view rather than a fixed list."""
    ar = language == "ar"
    chips: List[str] = []
    countries = state.filters.get("country") or []
    sectors = state.filters.get("sector") or []

    if countries:
        chips.append(f"قارن {countries[0]} مع مصر" if ar
                     else f"Compare {countries[0]} with Egypt")
        chips.append(f"أظهر جميع مشاريع {sectors[0] if sectors else 'التعليم'}" if ar
                     else f"Show {sectors[0] if sectors else 'education'} projects everywhere")
    else:
        chips.append("أظهر مشاريع الأردن" if ar else "Show projects in Jordan")

    if not state.attention_only and any(r["attention_required"] for r in rows):
        chips.append("أظهر المشاريع التي تحتاج إلى انتباه" if ar
                     else "Show projects requiring attention")
    if "risk_level" not in state.filters:
        chips.append("أظهر المشاريع عالية المخاطر" if ar else "Show high risk projects")
    if not state.is_empty():
        chips.append("أظهر المحفظة بالكامل" if ar else "Show the entire portfolio")

    return chips[:4]


def build_insight(rows: List[Dict[str, Any]], state: QueryState,
                  language: str) -> Dict[str, Any]:
    """Executive Insight card. Figures from code; advice from the current view.

    The recommendation branches on the actual shape of the result set. A single
    fixed sentence makes the card look static even when the numbers change,
    which is the fastest way to lose an executive's trust in it.
    """
    summary = aggregates.summarise(rows)

    if not rows:
        return {
            "summary": summary,
            "recommendation": ("لا توجد مشاريع مطابقة. جرّب توسيع نطاق العرض."
                               if language == "ar" else
                               "No projects match this view. Try widening the filters."),
            "decision_note": None,
            "risk_level": "Low",
            "follow_ups": _contextual_follow_ups(state, rows, language),
        }

    # Operating context follows the country that dominates the current view,
    # not whichever record happens to sort first.
    top_country = Counter(r["country"] for r in rows).most_common(1)[0][0]
    note_row = next((r for r in rows
                     if r["country"] == top_country and r.get("decision_note")), None)
    decision_note = f"{top_country} — {note_row['decision_note']}" if note_row else None

    total = summary["projects"]
    attention = [r for r in rows if r["attention_required"]]
    high_share = summary["high_risk"] / total
    done_share = summary["completed"] / total
    best = max(rows, key=lambda r: r["completion"])

    if high_share >= 0.3:
        worst = min([r for r in rows if r["risk_level"] == "High"] or rows,
                    key=lambda r: r["completion"])
        recommendation = (
            f"{summary['high_risk']} of {total} projects in this view are high risk. "
            f"Start with {worst['name']} in {worst['country']}, "
            f"{worst['completion']}% complete."
        )
    elif attention:
        worst = min(attention, key=lambda r: r["completion"])
        reason = (worst["attention_reasons"][0].lower()
                  if worst["attention_reasons"] else "flagged for review")
        recommendation = (
            f"{len(attention)} of {total} projects need attention. "
            f"Begin with {worst['name']} in {worst['country']} — {reason}."
        )
    elif done_share >= 0.6:
        recommendation = (
            f"{summary['completed']} of {total} projects are complete. "
            f"{best['name']} in {best['country']} is the strongest reference case "
            f"for replication."
        )
    else:
        recommendation = (
            f"This view is tracking at {summary['avg_completion']}% average completion "
            f"across {summary['countries']} "
            f"{'country' if summary['countries'] == 1 else 'countries'}. "
            f"{best['name']} leads at {best['completion']}%."
        )

    return {
        "summary": summary,
        "recommendation": recommendation,
        "decision_note": decision_note,
        "risk_level": ("High" if high_share >= 0.3
                       else "Medium" if summary["high_risk"] else "Low"),
        "follow_ups": _contextual_follow_ups(state, rows, language),
    }


def run_turn(session: Session, question: str, llm) -> Dict[str, Any]:
    """Execute one conversational turn. Never raises to the caller."""
    started = time.perf_counter()
    language = detect_language(question)
    projects = load_projects(settings.dataset_size)
    vocab = vocabulary(settings.dataset_size)

    plan = llm.plan(question, session.state, session.history)
    warnings: List[str] = []
    rejected: List[str] = []

    if plan.get("reset"):
        session.state = QueryState()

    delta = plan.get("delta") or {}
    # Did THIS turn resolve a place? If not, any place named in the question is
    # one the portfolio does not contain. Checking the delta rather than the
    # accumulated state is what matters: a Jordan filter left over from three
    # questions ago must not mask "is there any project in India?".
    turn_resolved_place = bool(delta.get("country") or delta.get("region"))
    try:
        validate_delta(delta, vocab)
        session.state = apply_delta(session.state, delta)
    except DeltaError as exc:
        # The entire error surface of the query path.
        log.warning("rejected delta: %s", exc)
        if exc.value:
            # The executive named something the portfolio does not contain.
            # Say so plainly instead of silently showing everything, which
            # reads as a wrong answer.
            rejected.append(exc.value)
        else:
            warnings.append(f"Ignored an invalid filter instruction: {exc}")

    # If the executive named a place the portfolio does not cover, say so rather
    # than silently returning the previous view — which reads as a wrong answer.
    if not rejected and not turn_resolved_place:
        rejected.extend(detect_unknown_place(question, alias_index(settings.dataset_size)))

    rows = apply_filters(projects, session.state)

    comparison = None
    compare_spec = plan.get("compare")
    if compare_spec and compare_spec.get("values"):
        comparison = aggregates.compare(
            projects, compare_spec.get("dimension", "country"),
            compare_spec["values"])

    narrative = plan.get("narrative_ar" if language == "ar" else "narrative_en") \
        or plan.get("narrative_en") or ""
    summary = aggregates.summarise(rows)

    # The model describes; the application quantifies. The two are joined here.
    if rejected:
        subject = " or ".join(v if v.isupper() else v.title() for v in rejected)
        spoken = (f"لا توجد لدينا مشاريع في {subject}. لا يزال العرض الحالي كما هو."
                  if language == "ar" else
                  f"We have no projects in {subject}. The current view is unchanged.")
    elif summary["projects"] == 0:
        spoken = ("لا توجد مشاريع مطابقة للمرشحات الحالية."
                  if language == "ar" else
                  "No projects match the current filters.")
    elif language == "ar":
        spoken = f"{narrative} {summary['projects']} مشروع في {summary['countries']} دولة."
    else:
        noun = "project" if summary["projects"] == 1 else "projects"
        place = "country" if summary["countries"] == 1 else "countries"
        spoken = (f"{narrative} {summary['projects']} {noun} across "
                  f"{summary['countries']} {place}.")

    session.history.append({"role": "executive", "content": question})
    session.history.append({"role": "zai", "content": spoken})
    session.history[:] = session.history[-12:]

    return {
        "session_id": session.id,
        "language": language,
        "intent": plan.get("intent", "filter"),
        "question": question,
        "spoken_response": spoken.strip(),
        "state": session.state.model_dump(),
        "state_description": session.state.describe(),
        "summary": summary,
        "distributions": aggregates.distributions(rows),
        "map": aggregates.map_payload(rows),
        "insight": build_insight(rows, session.state, language),
        "comparison": comparison,
        "projects": [r for r in rows if r["featured"]][:12],
        "map_action": "none" if rejected else plan.get("map_action", "fit"),
        "warnings": warnings,
        "unknown_values": rejected,
        # Which planner actually answered this turn. A silent fallback to the
        # keyword planner is otherwise indistinguishable from a bad model.
        "planner": plan.get("_source", "unknown"),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }