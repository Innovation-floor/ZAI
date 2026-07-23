"""In-memory project repository.

Loads the authored seed records and optionally synthesises additional records so
the dashboard headline figures match the approved executive materials.
Everything is held in memory: the dataset is small by design.
"""
from __future__ import annotations

import random
from functools import lru_cache
from typing import Any, Dict, List

from app.data import seed


def _attention(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Derive executive-attention flags. Deterministic, no hand-authored flags."""
    reasons: List[str] = []
    if rec["risk_level"] == "High" and rec["completion"] < 45:
        reasons.append("High risk with low completion")
    if rec["status"] == "Active" and rec["end_year"] <= 2025 and rec["completion"] < 75:
        reasons.append("Behind schedule against end date")
    return {"attention_required": bool(reasons), "attention_reasons": reasons}


def _build_seed_records() -> List[Dict[str, Any]]:
    out = []
    for row in seed.SEED:
        (pid, name, country, region, sector, status, partner, investment,
         beneficiaries, completion, risk, start, end, sdgs, description) = row
        lat, lon, country_ar = seed.COUNTRY_META[country]
        ctx = seed.OPERATING_CONTEXT.get(country, seed.DEFAULT_CONTEXT)
        rec: Dict[str, Any] = {
            "id": f"P{pid:04d}",
            "name": name,
            "country": country,
            "country_ar": country_ar,
            "region": region,
            "sector": sector,
            "sector_ar": seed.SECTOR_AR[sector],
            "status": status,
            "status_ar": seed.STATUS_AR[status],
            "partner": partner,
            "investment_aed_m": investment,
            "beneficiaries": beneficiaries,
            "completion": completion,
            "risk_level": risk,
            "risk_level_ar": seed.RISK_AR[risk],
            "start_year": start,
            "end_year": end,
            "sdgs": sdgs,
            "description": description,
            "lat": lat,
            "lon": lon,
            "featured": True,
            "challenges": ctx["challenges"],
            "cooperating_entities": ctx["entities"],
            "friction_points": ctx["friction"],
            "decision_note": ctx["decision_note"],
        }
        rec.update(_attention(rec))
        out.append(rec)
    return out


def _synthesise(base: List[Dict[str, Any]], target_total: int) -> List[Dict[str, Any]]:
    """Generate additional records so headline totals match the executive deck.

    Synthetic records are marked featured=False and are never surfaced in
    project-detail views. They exist to make portfolio-level figures realistic.
    """
    if target_total <= len(base):
        return []
    rng = random.Random(20260101)  # fixed seed: identical dataset on every boot
    countries = list(seed.COUNTRY_META.keys())
    sectors = list(seed.SECTOR_AR.keys())
    region_of = {r["country"]: r["region"] for r in base}
    region_of.update(seed.EXTRA_REGION)
    # Expand the partner roster to match the executive deck's partner count.
    partners = sorted({r["partner"] for r in base})
    for pre in seed.PARTNER_POOL_PREFIX:
        for suf in seed.PARTNER_POOL_SUFFIX:
            if len(partners) >= 68:
                break
            partners.append(f"{pre} {suf}")
    partners = sorted(set(partners))
    extra: List[Dict[str, Any]] = []

    for i in range(len(base) + 1, target_total + 1):
        country = rng.choice(countries)
        sector = rng.choice(sectors)
        status = rng.choices(["Active", "Completed", "Planning"], weights=[88, 9, 3])[0]
        completion = 100 if status == "Completed" else (
            rng.randint(3, 15) if status == "Planning" else rng.randint(20, 95))
        risk = rng.choices(["Low", "Medium", "High"], weights=[36, 40, 24])[0]
        start = rng.randint(2022, 2025)
        lat, lon, country_ar = seed.COUNTRY_META[country]
        rec: Dict[str, Any] = {
            "id": f"P{i:04d}",
            "name": f"{country} {sector.split(' ')[0]} Programme {i}",
            "country": country,
            "country_ar": country_ar,
            "region": region_of.get(country, "Sub-Saharan Africa"),
            "sector": sector,
            "sector_ar": seed.SECTOR_AR[sector],
            "status": status,
            "status_ar": seed.STATUS_AR[status],
            "partner": rng.choice(partners),
            "investment_aed_m": round(rng.uniform(0.4, 2.6), 1),
            "beneficiaries": rng.randrange(500, 6500, 100),
            "completion": completion,
            "risk_level": risk,
            "risk_level_ar": seed.RISK_AR[risk],
            "start_year": start,
            "end_year": start + rng.randint(1, 3),
            "sdgs": sorted(rng.sample(range(1, 17), rng.randint(1, 2))),
            "description": f"Programme delivering {sector.lower()} outcomes in {country}.",
            # jitter so co-located markers remain individually clickable
            "lat": round(lat + rng.uniform(-1.4, 1.4), 4),
            "lon": round(lon + rng.uniform(-1.4, 1.4), 4),
            "featured": False,
            "challenges": seed.DEFAULT_CONTEXT["challenges"],
            "cooperating_entities": seed.DEFAULT_CONTEXT["entities"],
            "friction_points": seed.DEFAULT_CONTEXT["friction"],
            "decision_note": seed.DEFAULT_CONTEXT["decision_note"],
        }
        rec.update(_attention(rec))
        extra.append(rec)
    return extra


# The executive deck scripts specific questions with specific answers
# ("twelve education projects in Jordan"). Random synthesis will not reliably
# satisfy them, so coverage is asserted explicitly after generation.
DEMO_COVERAGE = [
    ("Jordan", "Education", 12),
    ("Egypt", "Education", 6),
    ("Kenya", "Water & Sanitation", 5),
]


def _guarantee_demo_coverage(base: List[Dict[str, Any]],
                             extra: List[Dict[str, Any]]) -> None:
    """Reassign synthetic records so scripted demonstrations always resolve."""
    pool = [r for r in extra if r["status"] == "Active"]
    cursor = 0
    for country, sector, target in DEMO_COVERAGE:
        have = sum(1 for r in base + extra
                   if r["country"] == country and r["sector"] == sector)
        while have < target and cursor < len(pool):
            rec = pool[cursor]
            cursor += 1
            if rec["country"] == country and rec["sector"] == sector:
                continue
            lat, lon, country_ar = seed.COUNTRY_META[country]
            rec["country"] = country
            rec["country_ar"] = country_ar
            rec["region"] = seed.EXTRA_REGION.get(
                country, next((b["region"] for b in base
                               if b["country"] == country), rec["region"]))
            rec["sector"] = sector
            rec["sector_ar"] = seed.SECTOR_AR[sector]
            rec["name"] = f"{country} {sector.split(' ')[0]} Programme {rec['id'][1:]}"
            rec["description"] = f"Programme delivering {sector.lower()} outcomes in {country}."
            rec["lat"] = round(lat + ((cursor % 7) - 3) * 0.28, 4)
            rec["lon"] = round(lon + ((cursor % 5) - 2) * 0.28, 4)
            have += 1


@lru_cache(maxsize=1)
def load_projects(target_total: int = 210) -> List[Dict[str, Any]]:
    base = _build_seed_records()
    extra = _synthesise(base, target_total)
    _guarantee_demo_coverage(base, extra)
    return base + extra


@lru_cache(maxsize=1)
def vocabulary(target_total: int = 210) -> Dict[str, List[str]]:
    """Closed vocabulary for every filterable dimension.

    This is what makes value resolution unnecessary: the complete candidate set
    is small enough to place directly in the model prompt.
    """
    rows = load_projects(target_total)
    return {
        "country": sorted({r["country"] for r in rows}),
        "region": sorted({r["region"] for r in rows}),
        "sector": sorted({r["sector"] for r in rows}),
        "status": sorted({r["status"] for r in rows}),
        "partner": sorted({r["partner"] for r in rows}),
        "risk_level": ["Low", "Medium", "High"],
    }


@lru_cache(maxsize=1)
def alias_index(target_total: int = 210) -> Dict[str, tuple]:
    """Maps lowercase English and Arabic surface forms to (dimension, canonical)."""
    idx: Dict[str, tuple] = {}
    for dim, values in vocabulary(target_total).items():
        for v in values:
            idx[v.lower()] = (dim, v)
    for en, ar in seed.SECTOR_AR.items():
        idx[ar] = ("sector", en)
    for en, (_, _, ar) in seed.COUNTRY_META.items():
        idx[ar] = ("country", en)
    for en, ar in seed.STATUS_AR.items():
        idx[ar] = ("status", en)
    for en, ar in seed.RISK_AR.items():
        idx[ar] = ("risk_level", en)
    # convenience surface forms an executive would actually say
    idx.update({
        "water": ("sector", "Water & Sanitation"),
        "sanitation": ("sector", "Water & Sanitation"),
        "health": ("sector", "Health & Nutrition"),
        "nutrition": ("sector", "Health & Nutrition"),
        "shelter": ("sector", "Shelter & Reconstruction"),
        "reconstruction": ("sector", "Shelter & Reconstruction"),
        "emergency": ("sector", "Emergency Relief"),
        "relief": ("sector", "Emergency Relief"),
        "food": ("sector", "Food Security"),
        "orphan": ("sector", "Orphan & Family Care"),
        "orphans": ("sector", "Orphan & Family Care"),
        "africa": ("region", "Sub-Saharan Africa"),
        "asia": ("region", "South & Southeast Asia"),
        "middle east": ("region", "Middle East & North Africa"),
        # Short Arabic forms: an executive says "المياه", not the full label.
        "المياه": ("sector", "Water & Sanitation"),
        "التعليم": ("sector", "Education"),
        "الصحة": ("sector", "Health & Nutrition"),
        "التغذية": ("sector", "Health & Nutrition"),
        "المأوى": ("sector", "Shelter & Reconstruction"),
        "الإغاثة": ("sector", "Emergency Relief"),
        "الطارئة": ("sector", "Emergency Relief"),
        "الأيتام": ("sector", "Orphan & Family Care"),
        "الغذائي": ("sector", "Food Security"),
        "سبل العيش": ("sector", "Livelihoods"),
        "أفريقيا": ("region", "Sub-Saharan Africa"),
        "افريقيا": ("region", "Sub-Saharan Africa"),
        "آسيا": ("region", "South & Southeast Asia"),
        "الشرق الأوسط": ("region", "Middle East & North Africa"),
    })
    return idx
