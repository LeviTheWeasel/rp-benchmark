"""Validate independently authored external-judge artifacts without loading prior scores."""

import argparse
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SESSION = (
    "S.1_consistency_over_time", "S.2_degradation_resistance",
    "S.3_narrative_momentum", "S.4_adaptive_responsiveness",
    "S.5_agency_respect_session", "S.6_temporal_reasoning",
)
STANDARD = (
    "2.1_anti_purple_prose", "2.2_anti_repetition", "2.5_show_dont_tell",
    "2.6_subtext", "2.7_pacing",
)
TOP = {"session_id", "session_dimensions", "standard_dimensions",
       "quality_trajectory", "overall", "overall_notes"}


def number(value):
    assert type(value) in (int, float) and math.isfinite(value) and 1 <= value <= 5, value


def validate(part):
    source = json.loads((ROOT / f"sessions_part{part:02}.json").read_text())
    rows = json.loads((ROOT / f"external_part{part:02}.json").read_text())
    assert isinstance(rows, list) and len(rows) == len(source) == 10
    assert [r["session_id"] for r in rows] == [r["session_id"] for r in source]
    assert len({r["session_id"] for r in rows}) == 10
    for row in rows:
        assert set(row) == TOP
        for group, keys in (("session_dimensions", SESSION), ("standard_dimensions", STANDARD)):
            assert set(row[group]) == set(keys)
            for key in keys:
                item = row[group][key]
                extra = {"violation_count"} if key == SESSION[4] else {"contradictions"} if key == SESSION[5] else set()
                assert set(item) == {"score", "rationale"} | extra
                number(item["score"])
                assert isinstance(item["rationale"], str) and item["rationale"].strip()
        agency = row["session_dimensions"][SESSION[4]]["violation_count"]
        assert type(agency) is int and agency >= 0
        contradictions = row["session_dimensions"][SESSION[5]]["contradictions"]
        assert isinstance(contradictions, list) and all(isinstance(c, str) and c.strip() for c in contradictions)
        trajectory = row["quality_trajectory"]
        assert set(trajectory) == {"early_quality", "mid_quality", "late_quality", "degradation_detected"}
        for field in ("early_quality", "mid_quality", "late_quality"):
            number(trajectory[field])
        assert type(trajectory["degradation_detected"]) is bool
        number(row["overall"])
        assert isinstance(row["overall_notes"], str) and row["overall_notes"].strip()
    return rows


def build_part01():
    source = json.loads((ROOT / "sessions_part01.json").read_text())
    judgments = json.loads((ROOT / "judge_work_part01.json").read_text())
    assert len(judgments) == 10 and [j["index"] for j in judgments] == list(range(10))
    rows = []
    for entry, judgment in zip(source, judgments):
        assert len(judgment["scores"]) == len(judgment["rationales"]) == 11
        dimensions = {key: {"score": score, "rationale": rationale}
                      for key, score, rationale in zip(SESSION + STANDARD, judgment["scores"], judgment["rationales"])}
        dimensions[SESSION[4]]["violation_count"] = judgment["violation_count"]
        dimensions[SESSION[5]]["contradictions"] = judgment["contradictions"]
        rows.append({
            "session_id": entry["session_id"],
            "session_dimensions": {key: dimensions[key] for key in SESSION},
            "standard_dimensions": {key: dimensions[key] for key in STANDARD},
            "quality_trajectory": dict(zip(("early_quality", "mid_quality", "late_quality", "degradation_detected"), judgment["trajectory"])),
            "overall": judgment["overall"], "overall_notes": judgment["notes"],
        })
    target = ROOT / "external_part01.json"
    assert not target.exists(), "Refusing to overwrite an existing result."
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-part01", action="store_true")
    parser.add_argument("--parts", nargs="+", type=int, default=list(range(1, 13)))
    args = parser.parse_args()
    if args.build_part01:
        build_part01()
    all_rows = []
    for part in args.parts:
        rows = validate(part)
        all_rows.extend(rows)
        print(f"part {part:02}: PASS, {len(rows)} rows")
    assert len({r['session_id'] for r in all_rows}) == len(all_rows)
    overall = [r["overall"] for r in all_rows]
    print(json.dumps({"parts": args.parts, "sessions": len(overall), "overall_min": min(overall),
                      "overall_median": statistics.median(overall), "overall_max": max(overall)}))
