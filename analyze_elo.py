#!/usr/bin/env python3
"""ELO ratings for RP-Bench models.

Computes ELO ratings from pairwise matchups. Can use:
1. Score-based matchups (infer winner from flaw hunter score difference)
2. Comparative judge results (direct A/B preference)
3. Human votes (from arena data)

ELO formula:
  expected_a = 1 / (1 + 10^((rating_b - rating_a) / 400))
  new_rating_a = rating_a + K * (actual_a - expected_a)
  K = 32 (standard), higher K = faster adjustment, lower K = more stable
"""
import json
import random
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


INITIAL_RATING = 1500
K_FACTOR = 32


def expected_score(rating_a: float, rating_b: float) -> float:
    """Expected probability of A beating B."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_elo(
    rating_a: float,
    rating_b: float,
    outcome_a: float,  # 1 = A wins, 0 = A loses, 0.5 = tie
    k: float = K_FACTOR,
) -> tuple[float, float]:
    """Return new (rating_a, rating_b) after one matchup."""
    exp_a = expected_score(rating_a, rating_b)
    exp_b = 1 - exp_a
    outcome_b = 1 - outcome_a

    new_a = rating_a + k * (outcome_a - exp_a)
    new_b = rating_b + k * (outcome_b - exp_b)
    return new_a, new_b


def extract_matchups_from_scores(run_path: Path) -> list[tuple]:
    """Build pairwise matchups from a flaw hunter run.

    For each scenario, compare every pair of models.
    Higher score = winner. Ties = ties.

    Returns: list of (scenario_id, model_a, model_b, outcome_a)
    """
    with open(run_path) as f:
        run = json.load(f)

    # Group by scenario
    by_scenario = defaultdict(list)
    for r in run["results"]:
        if not r.get("generation"):
            continue
        model = r.get("test_model")
        sid = r.get("scenario_id")

        # Find score in any judge
        score = None
        for jdata in r.get("judges", {}).values():
            scores = jdata.get("scores", {})
            if "final_score" in scores:
                score = scores["final_score"]
                break
        if score is None:
            continue

        by_scenario[sid].append((model, score))

    matchups = []
    for sid, entries in by_scenario.items():
        if len(entries) < 2:
            continue
        for (m_a, s_a), (m_b, s_b) in combinations(entries, 2):
            if s_a > s_b:
                outcome = 1.0  # A wins
            elif s_a < s_b:
                outcome = 0.0  # A loses
            else:
                outcome = 0.5  # tie
            matchups.append((sid, m_a, m_b, outcome))
    return matchups


def compute_elo(
    matchups: list[tuple],
    initial: float = INITIAL_RATING,
    k: float = K_FACTOR,
    num_shuffles: int = 100,
) -> dict:
    """Compute ELO ratings from matchups.

    To reduce order-dependence, we run the matchups in random order
    multiple times and average the final ratings.
    """
    all_models = set()
    for _, a, b, _ in matchups:
        all_models.add(a)
        all_models.add(b)

    final_ratings = defaultdict(list)

    for shuffle_idx in range(num_shuffles):
        ratings = {m: initial for m in all_models}
        shuffled = matchups.copy()
        random.seed(shuffle_idx)
        random.shuffle(shuffled)

        for _, a, b, outcome in shuffled:
            new_a, new_b = update_elo(ratings[a], ratings[b], outcome, k)
            ratings[a] = new_a
            ratings[b] = new_b

        for m, r in ratings.items():
            final_ratings[m].append(r)

    # Average across shuffles
    avg_ratings = {m: sum(rs) / len(rs) for m, rs in final_ratings.items()}

    # Also compute stability (std dev across shuffles)
    stability = {}
    for m, rs in final_ratings.items():
        avg = avg_ratings[m]
        var = sum((r - avg) ** 2 for r in rs) / len(rs)
        stability[m] = var ** 0.5

    return avg_ratings, stability


def compute_winrate(matchups: list[tuple]) -> dict:
    """Compute head-to-head win rates for each model pair."""
    wins = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0}))

    for _, a, b, outcome in matchups:
        if outcome == 1.0:
            wins[a][b]["wins"] += 1
            wins[b][a]["losses"] += 1
        elif outcome == 0.0:
            wins[a][b]["losses"] += 1
            wins[b][a]["wins"] += 1
        else:
            wins[a][b]["ties"] += 1
            wins[b][a]["ties"] += 1

    return wins


def main():
    run_path = sys.argv[1] if len(sys.argv) > 1 else "results/run_20260413_231835.json"
    run_path = Path(run_path)

    matchups = extract_matchups_from_scores(run_path)
    print(f"Extracted {len(matchups)} matchups from {run_path.name}")
    print()

    ratings, stability = compute_elo(matchups)
    winrates = compute_winrate(matchups)

    # Sort by rating
    ranked = sorted(ratings.items(), key=lambda x: -x[1])

    print("=" * 80)
    print("  RP-BENCH ELO LEADERBOARD")
    print("  (pairwise matchups from flaw hunter scores, 100 shuffles averaged)")
    print("=" * 80)
    print()
    print(f'  {"Rank":<5} {"Model":<28} {"ELO":<8} {"±":<7} {"Wins":<8} {"Losses":<8} {"Ties":<6}')
    print("  " + "-" * 74)

    for i, (model, rating) in enumerate(ranked):
        # Total W/L/T across all opponents
        total_w = total_l = total_t = 0
        for opp in ratings:
            if opp == model:
                continue
            rec = winrates[model].get(opp, {"wins": 0, "losses": 0, "ties": 0})
            total_w += rec["wins"]
            total_l += rec["losses"]
            total_t += rec["ties"]

        stab = stability[model]
        print(f'  #{i+1:<4} {model:<28} {rating:<8.0f} {stab:<7.1f} {total_w:<8} {total_l:<8} {total_t:<6}')
    print("  " + "-" * 74)

    # Head-to-head matrix
    print()
    print("  HEAD-TO-HEAD WIN RATES (row vs column)")
    print("  " + "-" * 74)

    models = [m for m, _ in ranked]
    short = {m: m[:10] for m in models}

    # Print header
    header = "  " + " " * 22
    for m in models:
        header += f'{short[m]:<12}'
    print(header)

    for m in models:
        row = f'  {short[m]:<22}'
        for opp in models:
            if m == opp:
                row += '  --        '
                continue
            rec = winrates[m].get(opp, {"wins": 0, "losses": 0, "ties": 0})
            total = rec["wins"] + rec["losses"] + rec["ties"]
            if total == 0:
                row += '  -         '
            else:
                wr = 100 * (rec["wins"] + 0.5 * rec["ties"]) / total
                row += f'  {wr:5.1f}%    '
        print(row)

    # Save
    out = run_path.parent / "elo_leaderboard.json"
    with open(out, "w") as f:
        json.dump({
            "ratings": {m: round(r, 1) for m, r in ratings.items()},
            "stability": {m: round(s, 2) for m, s in stability.items()},
            "total_matchups": len(matchups),
            "winrates": {m: dict(opps) for m, opps in winrates.items()},
        }, f, indent=2)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
