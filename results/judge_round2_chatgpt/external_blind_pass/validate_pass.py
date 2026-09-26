"""Validate this pass using only its permitted inputs and newly produced outputs."""
import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent
SESSION = ["S.1_consistency_over_time", "S.2_degradation_resistance",
           "S.3_narrative_momentum", "S.4_adaptive_responsiveness",
           "S.5_agency_respect_session", "S.6_temporal_reasoning"]
STANDARD = ["2.1_anti_purple_prose", "2.2_anti_repetition",
            "2.5_show_dont_tell", "2.6_subtext", "2.7_pacing"]
TOP = {"session_id", "session_dimensions", "standard_dimensions",
       "quality_trajectory", "overall", "overall_notes"}
TRAJECTORY = {"early_quality", "mid_quality", "late_quality", "degradation_detected"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fingerprint():
    names = ["TASK.md", "RUBRIC.md"] + [f"sessions_part{i:02}.json" for i in range(1, 13)]
    return {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in names}


def number(value):
    assert type(value) in (int, float) and math.isfinite(value) and 1 <= value <= 5, value


def inputs():
    parts = {i: read(SOURCE / f"sessions_part{i:02}.json") for i in range(1, 13)}
    ids = []
    for part in parts.values():
        assert isinstance(part, list) and len(part) == 10
        for item in part:
            assert set(item) == {"session_id", "character_name", "user_name", "num_turns", "transcript"}
            assert re.fullmatch(r"s\d+", item["session_id"]), "Nonopaque ID"
            assert isinstance(item["transcript"], str)
            ids.append(item["session_id"])
    assert len(ids) == len(set(ids)) == 120
    return parts


def validate(part, source):
    rows = read(OUT / f"external_part{part:02}.json")
    assert isinstance(rows, list) and len(rows) == 10
    assert [r["session_id"] for r in rows] == [r["session_id"] for r in source]
    for row in rows:
        assert set(row) == TOP, row["session_id"]
        for group, keys in (("session_dimensions", SESSION), ("standard_dimensions", STANDARD)):
            assert set(row[group]) == set(keys)
            for key in keys:
                item = row[group][key]
                extras = {"violation_count"} if key == SESSION[4] else {"contradictions"} if key == SESSION[5] else set()
                assert set(item) == {"score", "rationale"} | extras
                number(item["score"])
                assert isinstance(item["rationale"], str) and item["rationale"].strip()
                assert "\n" not in item["rationale"], (row["session_id"], key)
        count = row["session_dimensions"][SESSION[4]]["violation_count"]
        assert type(count) is int and count >= 0
        contradictions = row["session_dimensions"][SESSION[5]]["contradictions"]
        assert isinstance(contradictions, list) and all(isinstance(c, str) and c.strip() for c in contradictions)
        trajectory = row["quality_trajectory"]
        assert set(trajectory) == TRAJECTORY
        assert type(trajectory["degradation_detected"]) is bool
        for field in TRAJECTORY - {"degradation_detected"}:
            number(trajectory[field])
        number(row["overall"])
        assert isinstance(row["overall_notes"], str) and row["overall_notes"].strip()
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--parts", type=int, nargs="+")
    args = parser.parse_args()
    source = inputs()
    fingerprints = fingerprint()
    if args.snapshot:
        with (OUT / "input_sha256.json").open("x", encoding="utf-8") as f:
            json.dump(fingerprints, f, indent=2)
            f.write("\n")
        print("Input snapshot: 12 parts, 120 unique opaque IDs; hashes saved.")
    else:
        assert read(OUT / "input_sha256.json") == fingerprints, "INPUTS CHANGED DURING PASS"
        parts = args.parts or list(range(1, 13))
        all_rows = []
        for part in parts:
            rows = validate(part, source[part])
            all_rows.extend(rows)
            print(f"part {part:02}: PASS")
        values = [r["overall"] for r in all_rows]
        summary = {"parts": parts, "sessions": len(values), "min": min(values),
                   "median": statistics.median(values), "max": max(values), "input_hashes_unchanged": True}
        print(json.dumps(summary))
        if not args.parts:
            with (OUT / "validation.json").open("w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
                f.write("\n")
