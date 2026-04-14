#!/usr/bin/env python3
"""ELO ratings for the adversarial multi-turn run.

Raw overall-score means from the adversarial run compress into a 0.25-point
band (4.19-4.44). This script converts the same session data into pairwise
matchups per seed and runs the standard ELO formula to recover real spread.

Matchup rule: for a given seed, model A beats model B if A's overall score
is higher. If overall scores are equal, the sum of session-dimension scores
is used as a tiebreaker (reduces tie rate from ~29% to ~16%). The dimension
sum is treated as a secondary signal only — it never overrides a primary
overall-score delta.

Usage:
    python3 analyze_adversarial_elo.py [run.json]
"""
import json
import random
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

INITIAL_RATING = 1500
K_FACTOR = 32
NUM_SHUFFLES = 100


def expected(a, b):
    return 1 / (1 + 10 ** ((b - a) / 400))


def update(a, b, outcome_a, k=K_FACTOR):
    ea = expected(a, b)
    return a + k * (outcome_a - ea), b + k * ((1 - outcome_a) - (1 - ea))


def session_score(judge_scores):
    o = judge_scores.get("overall")
    if o is None:
        return None
    dim_sum = 0.0
    for _, info in judge_scores.get("session_dimensions", {}).items():
        if isinstance(info, dict) and "score" in info:
            dim_sum += info["score"]
    return (o, dim_sum)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results/multiturn_20260414_042100.json")
    data = json.load(open(path))
    if data.get("type") != "multiturn":
        print(f"Not a multiturn file: {path}")
        sys.exit(1)

    scores = {}
    for s in data["sessions"]:
        if "judges" not in s or "test_model" not in s:
            continue
        j = list(s["judges"].values())[0]["scores"]
        sc = session_score(j)
        if sc is None:
            continue
        scores[(s["seed_id"], s["test_model"])] = sc

    by_seed = defaultdict(list)
    for (seed, model), sc in scores.items():
        by_seed[seed].append((model, sc))

    matchups = []
    for seed, entries in by_seed.items():
        for (a, sa), (b, sb) in combinations(entries, 2):
            if sa > sb:
                matchups.append((seed, a, b, 1.0))
            elif sa < sb:
                matchups.append((seed, a, b, 0.0))
            else:
                matchups.append((seed, a, b, 0.5))

    ties = sum(1 for m in matchups if m[3] == 0.5)
    print(f"Adversarial ELO from {path.name}")
    print(f"Matchups: {len(matchups)} across {len(by_seed)} seeds, {ties} ties ({100*ties/len(matchups):.0f}%)")
    print()

    models = {a for _, a, _, _ in matchups} | {b for _, _, b, _ in matchups}
    final = defaultdict(list)
    for shuffle_idx in range(NUM_SHUFFLES):
        ratings = {m: INITIAL_RATING for m in models}
        sh = matchups.copy()
        random.seed(shuffle_idx)
        random.shuffle(sh)
        for _, a, b, o in sh:
            na, nb = update(ratings[a], ratings[b], o)
            ratings[a], ratings[b] = na, nb
        for m, r in ratings.items():
            final[m].append(r)

    avg = {m: sum(rs) / len(rs) for m, rs in final.items()}
    stab = {m: (sum((r - avg[m]) ** 2 for r in rs) / len(rs)) ** 0.5 for m, rs in final.items()}

    mean_overall = defaultdict(list)
    for (_, m), sc in scores.items():
        mean_overall[m].append(sc[0])

    print("=" * 60)
    print("ADVERSARIAL ELO LEADERBOARD")
    print("=" * 60)
    print(f'{"Rank":<5}{"Model":<28}{"ELO":<7}{"±":<6}{"Mean":<7}')
    print("-" * 55)
    ranked = sorted(avg.items(), key=lambda x: -x[1])
    for i, (m, r) in enumerate(ranked):
        mo = sum(mean_overall[m]) / len(mean_overall[m])
        print(f"#{i+1:<4}{m:<28}{r:<7.0f}{stab[m]:<6.1f}{mo:<7.2f}")

    wins = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for _, a, b, o in matchups:
        if o == 1.0:
            wins[a][b][0] += 1
            wins[b][a][1] += 1
        elif o == 0.0:
            wins[a][b][1] += 1
            wins[b][a][0] += 1
        else:
            wins[a][b][2] += 1
            wins[b][a][2] += 1

    print()
    print("=" * 60)
    print("HEAD-TO-HEAD WIN RATES (row vs column)")
    print("=" * 60)
    order = [m for m, _ in ranked]
    short = {
        m: m.replace("claude_", "C_")
        .replace("gemini_", "G_")
        .replace("mistral_", "M_")
        .replace("deepseek_", "D_")
        .replace("_creative", "")
        .replace("_4_5", "45")
        .replace("_4_1", "41")[:9]
        for m in order
    }
    print(" " * 11 + "".join(f"{short[m]:<9}" for m in order))
    for m in order:
        row = f"{short[m]:<11}"
        for opp in order:
            if m == opp:
                row += f'{"--":<9}'
                continue
            w, l, t = wins[m][opp]
            tot = w + l + t
            wr = 100 * (w + 0.5 * t) / tot if tot else 0
            row += f"{wr:5.1f}%  "
        print(row)

    out_path = Path("results") / "adversarial_elo.json"
    out = {
        "source": str(path),
        "method": "score-delta ELO with dimension-sum tiebreak",
        "n_matchups": len(matchups),
        "n_ties": ties,
        "elo": {m: round(r, 1) for m, r in avg.items()},
        "stability": {m: round(s, 2) for m, s in stab.items()},
        "mean_overall": {m: round(sum(mean_overall[m]) / len(mean_overall[m]), 3) for m in avg},
        "head_to_head": {
            m: {
                opp: {"wins": wins[m][opp][0], "losses": wins[m][opp][1], "ties": wins[m][opp][2]}
                for opp in avg
                if opp != m
            }
            for m in avg
        },
    }
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
