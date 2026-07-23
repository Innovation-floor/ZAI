"""Deterministic portfolio arithmetic.

Every number ZAI speaks, prints or charts originates in this module. The
language model is never asked to count, sum or average. This is a structural
guarantee, not a convention: if a figure cannot be traced to a function here,
it does not reach the executive.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


def summarise(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Headline figures for a result set."""
    if not rows:
        return {
            "projects": 0, "active": 0, "completed": 0, "planning": 0,
            "countries": 0, "partners": 0, "beneficiaries": 0,
            "investment_aed_m": 0.0, "avg_completion": 0,
            "attention_required": 0, "high_risk": 0,
        }

    return {
        "projects": len(rows),
        "active": sum(1 for r in rows if r["status"] == "Active"),
        "completed": sum(1 for r in rows if r["status"] == "Completed"),
        "planning": sum(1 for r in rows if r["status"] == "Planning"),
        "countries": len({r["country"] for r in rows}),
        "partners": len({r["partner"] for r in rows}),
        "beneficiaries": sum(r["beneficiaries"] for r in rows),
        "investment_aed_m": round(sum(r["investment_aed_m"] for r in rows), 1),
        "avg_completion": round(sum(r["completion"] for r in rows) / len(rows)),
        "attention_required": sum(1 for r in rows if r["attention_required"]),
        "high_risk": sum(1 for r in rows if r["risk_level"] == "High"),
    }


def _distribution(rows: List[Dict[str, Any]], key: str,
                  weight: str | None = None) -> List[Dict[str, Any]]:
    counter: Counter = Counter()
    for r in rows:
        counter[r[key]] += r[weight] if weight else 1
    total = sum(counter.values()) or 1
    return [
        {"label": label, "value": round(value, 1),
         "percent": round(value / total * 100, 1)}
        for label, value in counter.most_common()
    ]


def distributions(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Chart-ready breakdowns for the executive dashboard."""
    return {
        "budget_by_sector": _distribution(rows, "sector", "investment_aed_m"),
        "projects_by_status": _distribution(rows, "status"),
        "projects_by_risk": _distribution(rows, "risk_level"),
        "projects_by_region": _distribution(rows, "region"),
        "beneficiaries_by_country": _distribution(rows, "country", "beneficiaries")[:10],
    }


def map_payload(rows: List[Dict[str, Any]], limit: int = 400) -> Dict[str, Any]:
    """Marker set plus a bounding box for camera movement."""
    markers = [
        {
            "id": r["id"], "name": r["name"], "country": r["country"],
            "sector": r["sector"], "status": r["status"], "risk": r["risk_level"],
            "completion": r["completion"], "investment": r["investment_aed_m"],
            "beneficiaries": r["beneficiaries"], "lat": r["lat"], "lon": r["lon"],
            "featured": r["featured"],
        }
        for r in rows[:limit]
    ]
    bounds = None
    if markers:
        lats = [m["lat"] for m in markers]
        lons = [m["lon"] for m in markers]
        # pad so a single marker still yields a sane zoom level
        pad = 2.0 if len(markers) == 1 else 0.5
        bounds = {
            "south": min(lats) - pad, "west": min(lons) - pad,
            "north": max(lats) + pad, "east": max(lons) + pad,
        }
    return {"markers": markers, "bounds": bounds, "truncated": len(rows) > limit}


def compare(rows: List[Dict[str, Any]], dimension: str,
            values: List[str]) -> List[Dict[str, Any]]:
    """Side-by-side comparison, e.g. Jordan vs Egypt."""
    out = []
    for value in values:
        subset = [r for r in rows if r.get(dimension) == value]
        entry = {"label": value}
        entry.update(summarise(subset))
        out.append(entry)
    return out


def executive_brief(all_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Today's Executive Brief. Computed at session open, before any question."""
    active = [r for r in all_rows if r["status"] == "Active"]
    attention = [r for r in all_rows if r["attention_required"]]
    attention.sort(key=lambda r: (r["risk_level"] != "High", r["completion"]))
    recent = [r for r in all_rows if r["start_year"] >= 2025]

    return {
        "active_projects": len(active),
        "projects_requiring_attention": len(attention),
        "new_or_updated": len(recent),
        "countries_with_recent_activity": sorted({r["country"] for r in recent})[:5],
        "attention_list": [
            {"id": r["id"], "name": r["name"], "country": r["country"],
             "completion": r["completion"], "risk": r["risk_level"],
             "reasons": r["attention_reasons"]}
            for r in attention[:5]
        ],
        "portfolio": summarise(all_rows),
    }
