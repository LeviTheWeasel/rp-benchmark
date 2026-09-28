#!/usr/bin/env python3
"""Row schema for session-judge output, and a checker for one returned file.

This file does double duty. The importer imports `validate_row` from it, and
the package builder copies it verbatim into every chunk zip as
`validate_output.py`, so the judge checks its own file with exactly the code
that will accept or reject it here. Keep it standard-library only and free of
anything that names a model or a vendor: it travels inside a blind package.

As a script (inside an unzipped chunk):
    python validate_output.py chunk_01.out.json
It reads ITEMS.json next to itself for the expected ids and exits non-zero on
any problem.
"""
import json
import math
import sys
from pathlib import Path

SESSION_KEYS = (
    "S.1_consistency_over_time",
    "S.2_degradation_resistance",
    "S.3_narrative_momentum",
    "S.4_adaptive_responsiveness",
    "S.5_agency_respect_session",
    "S.6_temporal_reasoning",
)
STANDARD_KEYS = (
    "2.1_anti_purple_prose",
    "2.2_anti_repetition",
    "2.5_show_dont_tell",
    "2.6_subtext",
    "2.7_pacing",
)
TRAJECTORY_KEYS = ("early_quality", "mid_quality", "late_quality")
TOP_KEYS = ("session_id", "session_dimensions", "standard_dimensions",
            "quality_trajectory", "overall", "overall_notes")


def _score_ok(v):
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v) and 1.0 <= v <= 5.0)


def validate_row(row):
    """Return a list of problems with one row; empty means the row is usable."""
    errs = []
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    for k in TOP_KEYS:
        if k not in row:
            errs.append("missing top-level key %r" % k)
    if not isinstance(row.get("session_id"), str) or not row.get("session_id"):
        errs.append("session_id must be a non-empty string")
    for group, keys in (("session_dimensions", SESSION_KEYS),
                        ("standard_dimensions", STANDARD_KEYS)):
        d = row.get(group)
        if not isinstance(d, dict):
            errs.append("%s must be an object" % group)
            continue
        extra = sorted(set(d) - set(keys))
        if extra:
            errs.append("%s has keys the rubric does not define: %s"
                        % (group, ", ".join(extra)))
        for k in keys:
            dim = d.get(k)
            if not isinstance(dim, dict):
                errs.append("%s.%s missing or not an object" % (group, k))
                continue
            if not _score_ok(dim.get("score")):
                errs.append("%s.%s.score must be a number in [1, 5], got %r"
                            % (group, k, dim.get("score")))
            r = dim.get("rationale")
            if not isinstance(r, str) or not r.strip():
                errs.append("%s.%s.rationale must be a non-empty string"
                            % (group, k))
    sd = row.get("session_dimensions")
    if isinstance(sd, dict):
        s5 = sd.get("S.5_agency_respect_session")
        if isinstance(s5, dict):
            vc = s5.get("violation_count")
            if not (isinstance(vc, int) and not isinstance(vc, bool) and vc >= 0):
                errs.append("S.5 violation_count must be a non-negative "
                            "integer, got %r" % (vc,))
        s6 = sd.get("S.6_temporal_reasoning")
        if isinstance(s6, dict):
            c = s6.get("contradictions")
            if not (isinstance(c, list) and all(isinstance(x, str) for x in c)):
                errs.append("S.6 contradictions must be a list of strings")
    qt = row.get("quality_trajectory")
    if not isinstance(qt, dict):
        errs.append("quality_trajectory must be an object")
    else:
        for k in TRAJECTORY_KEYS:
            if not _score_ok(qt.get(k)):
                errs.append("quality_trajectory.%s must be a number in "
                            "[1, 5], got %r" % (k, qt.get(k)))
        if not isinstance(qt.get("degradation_detected"), bool):
            errs.append("quality_trajectory.degradation_detected must be "
                        "true or false")
    if not _score_ok(row.get("overall")):
        errs.append("overall must be a number in [1, 5], got %r"
                    % (row.get("overall"),))
    if not isinstance(row.get("overall_notes"), str):
        errs.append("overall_notes must be a string")
    return errs


def load_rows(path):
    """A returned file is a JSON array of rows. Tolerate a code fence around
    it, which chat clients add, but nothing else."""
    text = Path(path).read_text(encoding="utf-8").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("the file must contain one JSON array of row objects")
    return data


def main(argv):
    if len(argv) != 2:
        print("usage: python validate_output.py chunk_NN.out.json")
        return 2
    here = Path(__file__).resolve().parent
    items = json.loads((here / "ITEMS.json").read_text(encoding="utf-8"))
    expected = [sid for part in items["parts"].values() for sid in part]
    try:
        rows = load_rows(argv[1])
    except Exception as e:                      # noqa: BLE001
        print("FAIL: cannot read %s: %s" % (argv[1], e))
        return 1
    problems = []
    seen = {}
    for i, r in enumerate(rows):
        sid = r.get("session_id") if isinstance(r, dict) else None
        for e in validate_row(r):
            problems.append("row %d (%s): %s" % (i, sid, e))
        if sid in seen:
            problems.append("session_id %s appears twice" % sid)
        seen[sid] = i
    missing = [s for s in expected if s not in seen]
    foreign = [s for s in seen if s not in set(expected)]
    if foreign:
        problems.append("ids not in this chunk: %s" % ", ".join(map(str, foreign[:10])))
    order_ok = [r.get("session_id") for r in rows if isinstance(r, dict)] == \
        [s for s in expected if s in seen]
    for p in problems[:50]:
        print("FAIL:", p)
    if len(problems) > 50:
        print("... and %d more" % (len(problems) - 50))
    done_parts = [p for p, ids in items["parts"].items()
                  if all(s in seen for s in ids)]
    print("rows: %d of %d expected; complete parts: %d of %d"
          % (len(seen), len(expected), len(done_parts), len(items["parts"])))
    if missing:
        print("MISSING %d id(s), first: %s" % (len(missing), ", ".join(missing[:10])))
    if not order_ok:
        print("NOTE: rows are not in ITEMS.json order (accepted, but please keep "
              "that order)")
    if problems or missing:
        return 1
    print("OK: every id present once, every field valid")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
