#!/usr/bin/env python3
"""Is every derived artifact still built from the files on disk?

Four round-4 artifacts record a hash of each of their inputs. That makes
staleness detectable, and tests/test_round4_continuity.py already asserts it --
but only at test time, and only for one of the four. So the ordering they imply
lived nowhere: rebuild the leaderboard, forget the artifacts downstream of it,
and nothing says so until a test fails and names one stale input at a time.
That is exactly how it was found.

This turns the implied ordering into something runnable:

    PYTHONPATH=. .venv/bin/python pipeline/check_freshness.py

Exit 0 when everything matches, 1 when an artifact was built from a file that
has since changed, naming the script to re-run. `--order` prints the rebuild
order without checking anything.

The order is DERIVED, not declared: an artifact that records another artifact
as an input must be rebuilt after it, and that relation is read out of the
files themselves. round4_continuity records round4_overview, so the overview is
rebuilt first and continuity last -- and if that relation ever changes in the
code, this picks the change up instead of enforcing a stale constant.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# The artifact -> the command that rebuilds it. Only these four record input
# hashes; a fifth would be picked up by the scan below but would need its
# rebuild command added here.
REBUILD = {
    "round4_willingness_leaderboard.json": "rounds/r4/analyze_round4_willingness.py",
    "round4_overview.json": "rounds/r4/analyze_round4_overview.py",
    "round4_second_judge.json": "rounds/r4/analyze_round4_second_judge.py",
    # judge_elo is written by the OVERVIEW script (its OUT_ELO), not by
    # second_judge. Mapping it to second_judge would have told someone to run
    # the wrong script to fix a stale artifact.
    "round4_judge_elo.json": "rounds/r4/analyze_round4_overview.py",
    "round4_continuity.json": "rounds/r4/analyze_round4_continuity.py",
}

HASH_KEYS = ("inputs", "input_hashes", "sources", "source_hashes")


def sha(path: Path) -> str:
    """Same 16-hex prefix the artifacts record (analyze_round4_overview.sha)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def artifacts():
    """Every results/*.json carrying a {filename: hash} map of its inputs."""
    out = {}
    for f in sorted(RESULTS.glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        for k in HASH_KEYS:
            v = d.get(k)
            if (isinstance(v, dict) and v
                    and all(isinstance(x, str) and 16 <= len(x) <= 64
                            for x in v.values())):
                out[f.name] = v
                break
    return out


def rebuild_order(arts):
    """Topological: an artifact that is another's input is rebuilt first.

    Read from the recorded input maps rather than declared here, so the order
    follows the code. Falls back to a stable alphabetical order for artifacts
    with no relation to each other.
    """
    names = set(arts)
    # edge a -> b when b records a as an input
    deps = {b: {a for a in names if a in arts[b] and a != b} for b in names}
    order, placed = [], set()
    while len(placed) < len(names):
        ready = sorted(n for n in names - placed if deps[n] <= placed)
        if not ready:                      # a cycle: report it rather than hang
            raise SystemExit("cyclic dependency among %s"
                             % sorted(names - placed))
        order.extend(ready)
        placed.update(ready)
    return order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--order", action="store_true",
                    help="print the rebuild order and exit")
    args = ap.parse_args()

    arts = artifacts()
    if not arts:
        print("no artifact records input hashes; nothing to check")
        return 0
    order = rebuild_order(arts)

    if args.order:
        print("rebuild in this order (earlier artifacts are inputs to later):")
        for i, name in enumerate(order, 1):
            cmd = REBUILD.get(name, "(no rebuild command registered)")
            print("  %d. %-30s %s" % (i, name, cmd))
        return 0

    stale, missing = [], []
    for name in order:
        for dep, recorded in sorted(arts[name].items()):
            p = RESULTS / dep
            if not p.exists():
                missing.append((name, dep))
                continue
            now = sha(p)
            if now != recorded[:len(now)]:
                stale.append((name, dep, recorded, now))

    checked = sum(len(v) for v in arts.values())
    print("checked %d recorded inputs across %d artifacts" % (checked, len(arts)))
    if missing:
        print("\n%d recorded input(s) no longer on disk:" % len(missing))
        for name, dep in missing[:10]:
            print("  %-30s is missing %s" % (name, dep))

    if not stale:
        print("all fresh")
        return 1 if missing else 0

    print("\n%d artifact/input pair(s) STALE -- the artifact was built from a "
          "file that has since changed:" % len(stale))
    seen = []
    for name, dep, was, now in stale:
        print("  %-30s <- %-40s %s -> %s" % (name, dep, was[:12], now[:12]))
        if name not in seen:
            seen.append(name)
    # One script can build several artifacts (second_judge writes both
    # round4_second_judge.json and round4_judge_elo.json), so print commands
    # once, in the order their first artifact appears.
    print("\nrebuild, in this order:")
    done = set()
    for name in order:
        if name not in seen:
            continue
        cmd = REBUILD.get(name)
        if cmd is None:
            print("  (no rebuild command registered for %s)" % name)
            continue
        if cmd in done:
            continue
        done.add(cmd)
        print("  PYTHONPATH=. .venv/bin/python %s" % cmd)
    return 1


if __name__ == "__main__":
    sys.exit(main())
