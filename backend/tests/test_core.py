"""Tests for the parts that must never regress: state semantics and arithmetic."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from app.core.aggregates import summarise
from app.core.state import DeltaError, QueryState, apply_delta, apply_filters, validate_delta
from app.data.repository import load_projects, vocabulary


@pytest.fixture(scope="module")
def vocab():
    return vocabulary()


def test_new_dimension_accumulates(vocab):
    s = apply_delta(QueryState(), {"country": {"op": "set", "values": ["Jordan"]}})
    s = apply_delta(s, {"sector": {"op": "set", "values": ["Education"]}})
    assert s.filters == {"country": ["Jordan"], "sector": ["Education"]}


def test_same_dimension_replaces(vocab):
    """The GeoAI bug, prevented structurally rather than by a coded rule."""
    s = apply_delta(QueryState(), {"country": {"op": "set", "values": ["Jordan"]}})
    s = apply_delta(s, {"sector": {"op": "set", "values": ["Education"]}})
    s = apply_delta(s, {"country": {"op": "set", "values": ["Egypt"]}})
    assert s.filters["country"] == ["Egypt"]
    assert s.filters["sector"] == ["Education"]


def test_add_accumulates_within_dimension():
    s = apply_delta(QueryState(), {"country": {"op": "set", "values": ["Jordan"]}})
    s = apply_delta(s, {"country": {"op": "add", "values": ["Egypt"]}})
    assert s.filters["country"] == ["Jordan", "Egypt"]


def test_clear_removes_dimension():
    s = apply_delta(QueryState(), {"country": {"op": "set", "values": ["Jordan"]}})
    s = apply_delta(s, {"country": {"op": "clear"}})
    assert "country" not in s.filters


def test_apply_delta_is_pure():
    original = QueryState(filters={"country": ["Jordan"]})
    apply_delta(original, {"country": {"op": "set", "values": ["Egypt"]}})
    assert original.filters == {"country": ["Jordan"]}


@pytest.mark.parametrize("bad", [
    {"nonsense": {"op": "set", "values": []}},
    {"country": {"op": "explode", "values": []}},
    {"country": {"op": "set", "values": ["Atlantis"]}},
])
def test_invalid_deltas_rejected(bad, vocab):
    with pytest.raises(DeltaError):
        validate_delta(bad, vocab)


def test_dataset_reconciles_to_executive_deck():
    rows = load_projects()
    s = summarise(rows)
    assert s["projects"] == 210
    assert s["countries"] == 24
    assert 500 <= s["investment_aed_m"] <= 560       # deck states AED 540M
    assert 1_150_000 <= s["beneficiaries"] <= 1_250_000  # deck states 1.2M


def test_scripted_demo_question_resolves():
    """'Twelve education projects in Jordan' is scripted in every document."""
    rows = load_projects()
    state = QueryState(filters={"country": ["Jordan"], "sector": ["Education"]})
    assert len(apply_filters(rows, state)) == 12


def test_empty_result_summarises_safely():
    assert summarise([])["projects"] == 0


# ---------------------------------------------------------------------------
# Ollama planner
# ---------------------------------------------------------------------------
import json
from unittest.mock import patch

from app.core.state import apply_delta
from app.providers.llm import OllamaLLM, _plan_schema


class _Resp:
    def __init__(self, payload):
        self._payload = payload
    def raise_for_status(self):
        return None
    def json(self):
        return self._payload


def test_plan_schema_covers_every_dimension():
    """A drifting schema would silently drop a filter dimension."""
    from app.core.state import DIMENSIONS
    props = _plan_schema()["properties"]["delta"]["properties"]
    for dim in DIMENSIONS:
        assert dim in props


def test_ollama_plan_parses_schema_constrained_output(vocab):
    reply = {"message": {"content": json.dumps({
        "intent": "filter",
        "delta": {"country": {"op": "set", "values": ["Jordan"]},
                  "sector": {"op": "set", "values": ["Education"]}},
        "reset": False, "compare": None,
        "narrative_en": "Showing education projects in Jordan.",
        "narrative_ar": "عرض مشاريع التعليم في الأردن.",
        "map_action": "fit"})}}

    with patch("app.providers.llm.httpx.post", return_value=_Resp(reply)):
        plan = OllamaLLM().plan("show education projects in Jordan",
                                QueryState(), [])

    assert plan["intent"] == "filter"
    validate_delta(plan["delta"], vocab)
    state = apply_delta(QueryState(), plan["delta"])
    assert len(apply_filters(load_projects(), state)) == 12


def test_ollama_sends_schema_and_raised_context():
    """The two settings that break a local setup if wrong."""
    reply = {"message": {"content": '{"intent":"filter","delta":{},'
                                    '"narrative_en":"ok","map_action":"none"}'}}
    with patch("app.providers.llm.httpx.post", return_value=_Resp(reply)) as post:
        OllamaLLM().plan("hello", QueryState(), [])
    body = post.call_args.kwargs["json"]
    assert body["format"]["type"] == "object"      # constrained decoding on
    assert body["options"]["num_ctx"] >= 8192      # vocabulary block not truncated
    assert body["stream"] is False


def test_ollama_degrades_to_mock_when_daemon_is_down():
    """A local daemon going down mid-demonstration must not break the turn."""
    import httpx
    with patch("app.providers.llm.httpx.post",
               side_effect=httpx.ConnectError("connection refused")):
        plan = OllamaLLM().plan("show education projects", QueryState(), [])
    assert plan["delta"]["sector"]["values"] == ["Education"]
