#!/usr/bin/env python3
"""ELO from LLM-judged pairwise adversarial comparisons.

Reads results/adversarial_pairwise_raw.jsonl (produced by
judge_adversarial_pairwise.py), runs standard ELO with 100-shuffle
averaging, prints the leaderboard and H2H matrix, and saves aggregated
results to results/adversarial_pairwise_elo.json.

Also compares against the score-delta ELO in results/adversarial_elo.json
if present — the two are independent estimates of the same underlying
ranking and their agreement/disagreement is itself a signal.
"""
import json
import random
from collections import defaultdict
from pathlib import Path

RAW = Path("results/adversarial_pairwise_raw.jsonl")
RAW_SWAPPED = Path("results/adversarial_pairwise_raw_swapped.jsonl")
OUT = Path("results/adversarial_pairwise_elo.json")
SCORE_DELTA_ELO = Path("results/adversarial_elo.json")
INITIAL = 1500
K = 32
SHUFFLES = 100


def expected(a, b):
    return 1 / (1 + 10 ** ((b - a) / 400))


def update(a, b, oa, k=K):
    ea = expected(a, b)
    return a + k * (oa - ea), b + k * ((1 - oa) - (1 - ea))


def main():
    if not RAW.exists():
        print(f"Missing {RAW}. Run judge_adversarial_pairwise.py first.")
        return

    records = []
    with open(RAW) as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except Exception:
                pass

    swapped_records = []
    if RAW_SWAPPED.exists():
        with open(RAW_SWAPPED) as f:
            for line in f:
                try:
                    swapped_records.append(json.loads(line))
                except Exception:
                    pass

    # Position-bias check on original pass
    a_wins = sum(1 for r in records if r.get("winner_ab") == "A")
    b_wins = sum(1 for r in records if r.get("winner_ab") == "B")
    print(f"Original pass:  {len(records)} records, A wins {a_wins} ({100*a_wins/max(a_wins+b_wins,1):.0f}%)")
    if swapped_records:
        swa = sum(1 for r in swapped_records if r.get("winner_ab") == "A")
        swb = sum(1 for r in swapped_records if r.get("winner_ab") == "B")
        print(f"Swapped pass:   {len(swapped_records)} records, A wins {swa} ({100*swa/max(swa+swb,1):.0f}%)")

    # Combine: for each canonical pair, produce a matchup outcome by aggregating
    # the original result and the swapped result (if present). This neutralizes
    # position bias: a "real" win must win in both orderings.
    def key(r):
        a, b = sorted([r["model_a"], r["model_b"]])
        return (r["seed_id"], a, b)

    by_key = defaultdict(list)
    for r in records:
        by_key[key(r)].append(r)
    for r in swapped_records:
        by_key[key(r)].append(r)

    matchups = []
    both_agree = 0
    split = 0
    for (seed, m1, m2), rs in by_key.items():
        # Aggregate outcomes: 1 point for each time m1 won (winner_model == m1)
        m1_points = 0.0
        total = 0.0
        for r in rs:
            w = r.get("winner_model")
            if w == m1:
                m1_points += 1
            elif w == m2:
                m1_points += 0
            else:
                m1_points += 0.5
            total += 1
        if total == 0:
            continue
        outcome = m1_points / total
        matchups.append((seed, m1, m2, outcome))
        if len(rs) >= 2:
            if outcome == 1.0 or outcome == 0.0:
                both_agree += 1
            else:
                split += 1

    ties = sum(1 for m in matchups if m[3] == 0.5)
    print(f"Canonical pairs: {len(matchups)}, ties/splits: {ties} ({100*ties/max(len(matchups),1):.0f}%)")
    if swapped_records:
        print(f"Both orderings agree: {both_agree}, disagree (split): {split}  ← position-bias rate: {100*split/max(both_agree+split,1):.0f}%")

    models = {a for _, a, _, _ in matchups} | {b for _, _, b, _ in matchups}
    final = defaultdict(list)
    for shuffle_idx in range(SHUFFLES):
        ratings = {m: INITIAL for m in models}
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

    print()
    print("=" * 60)
    print("ADVERSARIAL ELO — LLM-judged pairwise")
    print("=" * 60)
    print(f'{"Rank":<5}{"Model":<28}{"ELO":<7}{"±":<6}')
    print("-" * 50)
    ranked = sorted(avg.items(), key=lambda x: -x[1])
    for i, (m, r) in enumerate(ranked):
        print(f"#{i+1:<4}{m:<28}{r:<7.0f}{stab[m]:<6.1f}")

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
    print("H2H WIN RATES")
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

    # Compare vs score-delta ELO
    if SCORE_DELTA_ELO.exists():
        sd = json.load(open(SCORE_DELTA_ELO))
        sd_elo = sd["elo"]
        print()
        print("=" * 60)
        print("COMPARISON: score-delta ELO vs LLM-judged ELO")
        print("=" * 60)
        print(f'{"Model":<28}{"Score-Δ":<10}{"LLM":<10}{"Δ":<8}')
        print("-" * 55)
        for m, r in sorted(avg.items(), key=lambda x: -x[1]):
            sd_r = sd_elo.get(m, 0)
            print(f"{m:<28}{sd_r:<10.0f}{r:<10.0f}{r - sd_r:<+8.0f}")

    out = {
        "method": "LLM-judged pairwise comparative ELO",
        "n_matchups": len(matchups),
        "n_ties": ties,
        "elo": {m: round(r, 1) for m, r in avg.items()},
        "stability": {m: round(s, 2) for m, s in stab.items()},
        "head_to_head": {
            m: {
                opp: {"wins": wins[m][opp][0], "losses": wins[m][opp][1], "ties": wins[m][opp][2]}
                for opp in avg
                if opp != m
            }
            for m in avg
        },
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}")


if __name__ == "__main__":
    main()
