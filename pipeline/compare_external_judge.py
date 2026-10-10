#!/usr/bin/env python3
"""Cross-FAMILY agreement: the Sonnet 5 pass vs an external judge.

The calibration already run compared two Sonnet 5 agents and got r = +0.908
per session. That is within-family. It cannot tell a well-defined scale apart
from a shared family bias -- two judges from one family that both prefer dense
prose will agree with each other and be wrong together.

This compares the Sonnet pass against a judge from a different family on the
same 120 stratified sessions. Read the result as:

  close to +0.9   the SUBJECTIVE block measures the writing
  much lower      it measures something about the judge, and the block should
                  be reported as a band the way the flaw hunter is

Drop the external judge's files into results/external_judge_package/ as
external_part*.json, then run this.

Usage:
    python3 pipeline/compare_external_judge.py
"""
import argparse
import glob
import json
import statistics as st
from pathlib import Path
CARD = {"S.1_consistency_over_time": "tone_consistency",
        "S.3_narrative_momentum": "engagement",
        "S.4_adaptive_responsiveness": "collaboration"}


def num(d, k):
    v = (d or {}).get(k)
    if isinstance(v, dict):
        v = v.get("score")
    return v if isinstance(v, (int, float)) else None


def pearson(pairs):
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = st.mean(xs), st.mean(ys)
    n = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    d = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** .5
    return n / d if d else 0.0


def spearman(pairs):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    return pearson(list(zip(rank([p[0] for p in pairs]),
                            rank([p[1] for p in pairs]))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("package", nargs="?",
                    default="results/external_judge_package",
                    help="judge package directory to compare")
    args = ap.parse_args()
    PKG = Path(args.package)
    print("package: %s\n" % PKG)
    files = sorted(glob.glob(str(PKG / "external_part*.json")))
    if not files:
        raise SystemExit(
            "no external_part*.json in %s -- drop the external judge's files "
            "there first" % PKG)

    ext = {}
    malformed = []
    for f in files:
        try:
            rows = json.load(open(f))
        except Exception as e:
            malformed.append((Path(f).name, repr(e)))
            continue
        for r in rows:
            sid = r.get("session_id")
            if sid:
                ext[sid] = r

    mine = {}
    for line in open("results/session_judge_v2.jsonl"):
        if line.strip():
            r = json.loads(line)
            mine[r["session_id"]] = r

    # The manifest belongs to the PACKAGE; a judge may return its files in a
    # subdirectory of it, so look upward rather than demanding a flat layout.
    mp = PKG / "_manifest.json"
    if not mp.exists() and (PKG.parent / "_manifest.json").exists():
        mp = PKG.parent / "_manifest.json"
    man = json.load(open(mp))
    keymap = man.get("keymap") or {}
    if keymap:                      # opaque ids -> real session ids
        ext = {keymap.get(k, k): v for k, v in ext.items()}
    manifest = man["session_ids"]
    # Sessions with no model text at all force every dimension to the 1.0
    # floor for BOTH judges, which is not agreement about writing -- it is two
    # judges hitting the same wall. Including them lifted r from +0.726 to
    # +0.782 on the first run.
    empty = {s for s in manifest
             if (mine.get(s) or {}).get("overall") == 1.0
             and (ext.get(s) or {}).get("overall") == 1.0}
    both = [s for s in manifest if s in ext and s in mine and s not in empty]
    if empty:
        print("  excluded %d session(s) scored 1.0 by both (no model text to "
              "judge)" % len(empty))

    print("CROSS-FAMILY JUDGE AGREEMENT")
    print("  sample:      %d sessions (stratified, seed %s)"
          % (len(manifest), man["seed"]))
    print("  external judge returned: %d" % len(ext))
    print("  comparable:  %d" % len(both))
    if malformed:
        print("  UNREADABLE FILES:")
        for n, e in malformed:
            print("      %-28s %s" % (n, e))
    extra = sorted(set(ext) - set(manifest))
    if extra:
        print("  %d session_id(s) not in the sample -- ignored: %s"
              % (len(extra), ", ".join(extra[:3])))
    if len(both) < 20:
        raise SystemExit("\n  too few comparable sessions to report a number")

    # out-of-scale scores would quietly distort every correlation below
    bad = [(s, k, v) for s in both for k, v in
           [(k, num(ext[s].get("session_dimensions"), k)) for k in CARD]
           if v is not None and not (1.0 <= v <= 5.0)]
    if bad:
        print("  %d external score(s) outside the 1-5 scale:" % len(bad))
        for s, k, v in bad[:5]:
            print("      %-44s %-28s %s" % (s, k, v))

    print("\n  %-22s %8s %9s %10s %9s %10s"
          % ("dimension", "r", "spearman", "mean diff", "med |d|", "within 0.5"))
    rows = [(k, CARD[k]) for k in CARD] + [("overall", "overall")]
    for key, label in rows:
        pairs = []
        for s in both:
            a = (mine[s].get("overall") if key == "overall"
                 else (mine[s].get("session_dimensions") or {}).get(key))
            b = (ext[s].get("overall") if key == "overall"
                 else num(ext[s].get("session_dimensions"), key))
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                pairs.append((a, b))
        if len(pairs) < 20:
            continue
        diffs = [x - y for x, y in pairs]
        print("  %-22s %+8.3f %+9.3f %+10.2f %9.2f %9.0f%%"
              % (label, pearson(pairs), spearman(pairs), st.mean(diffs),
                 st.median([abs(d) for d in diffs]),
                 100 * sum(1 for d in diffs if abs(d) <= 0.5) / len(diffs)))

    print("\n  Reference, the WITHIN-family pass on this same rubric:")
    print("    overall r = +0.908, mean diff 0.00, median |d| 0.20")
    print("  A large drop here means the block reflects the judge's family,")
    print("  not the writing, and should be reported as a band.")


if __name__ == "__main__":
    main()
