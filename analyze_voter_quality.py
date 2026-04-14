#!/usr/bin/env python3
"""Per-voter catch-pair pass rate from arena vote log.

Reads web/data/votes.jsonl (the arena server's vote log) and reports, for
each voter id, how often they picked the pre-declared good side on
calibration pairs. Voters with low pass rates are candidates for
down-weighting or exclusion in downstream analyses.

Usage:
    python3 analyze_voter_quality.py [path/to/votes.jsonl]

Thresholds in the output are advisory, not hard cutoffs — we report them
so a human can make the call.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("web/data/votes.jsonl")
    if not path.exists():
        print(f"Not found: {path}")
        sys.exit(1)

    # Per-voter: total arena votes, catch attempts, catch correct
    total = defaultdict(int)
    catches = defaultdict(int)
    correct = defaultdict(int)
    per_catch = defaultdict(lambda: {"total": 0, "correct": 0})

    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            v = json.loads(line)
        except Exception:
            continue
        if v.get("mode") != "arena":
            continue
        voter = v.get("voter_id", "anonymous")
        total[voter] += 1
        if v.get("is_catch"):
            catches[voter] += 1
            per_catch[v["scenario_id"]]["total"] += 1
            if v.get("catch_correct"):
                correct[voter] += 1
                per_catch[v["scenario_id"]]["correct"] += 1

    if not total:
        print("No arena votes.")
        return

    print(f"Arena voters: {len(total)}, total votes: {sum(total.values())}")
    print()
    print("=" * 72)
    print("PER-VOTER CATCH PASS RATE")
    print("=" * 72)
    print(f'{"Voter id (truncated)":<26}{"Votes":<8}{"Catches":<10}{"Pass":<7}{"Rate":<10}{"Flag":<10}')
    print("-" * 72)

    rows = []
    for voter in total:
        v_votes = total[voter]
        v_catches = catches[voter]
        v_correct = correct[voter]
        rate = v_correct / v_catches if v_catches else None
        rows.append((voter, v_votes, v_catches, v_correct, rate))

    # Sort: voters with catches first, then by pass rate ascending (worst first)
    rows.sort(key=lambda r: (r[2] == 0, r[4] if r[4] is not None else -1))

    for voter, v_votes, v_catches, v_correct, rate in rows:
        rate_str = f"{rate*100:.0f}%" if rate is not None else "-"
        if v_catches == 0:
            flag = "(no catches yet)"
        elif v_catches < 2:
            flag = "(too few)"
        elif rate < 0.5:
            flag = "SUSPECT"
        elif rate < 0.75:
            flag = "marginal"
        else:
            flag = "ok"
        short = (voter[:10] + "...") if len(voter) > 13 else voter
        print(f'{short:<26}{v_votes:<8}{v_catches:<10}{v_correct:<7}{rate_str:<10}{flag:<10}')

    print()
    print("=" * 72)
    print("PER-CATCH SCENARIO FAIL RATE (which catches are we losing on?)")
    print("=" * 72)
    print(f'{"Catch scenario":<36}{"Attempts":<10}{"Correct":<10}{"Pass rate":<10}')
    print("-" * 72)
    for sid in sorted(per_catch, key=lambda s: per_catch[s]["correct"] / max(per_catch[s]["total"], 1)):
        rec = per_catch[sid]
        rate = rec["correct"] / rec["total"] if rec["total"] else 0
        print(f'{sid:<36}{rec["total"]:<10}{rec["correct"]:<10}{rate*100:.0f}%')


if __name__ == "__main__":
    main()
