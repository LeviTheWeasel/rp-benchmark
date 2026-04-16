#!/usr/bin/env python3
"""Community arena analysis — rankings, splits, H2H, and ELO from live votes.

Reads the arena vote log (either a local votes.jsonl or a live API URL),
filters out suspect voters (catch pass rate < 50% on >= 2 non-ambiguous
catches), and produces:

  - Community ELO with 100-shuffle stability band
  - SFW / NSFW split win rates per model
  - Top-tier head-to-head matrix
  - Catch statistics, including the ambiguous catch's split

Output is printed to stdout and written to a JSON file for the README
badges / blog post to consume.

Usage:
    python3 analyze_community_arena.py [--url URL | --file PATH] [--out PATH]

Defaults to pulling https://arena.l3vi4th4n.ai/api/votes and writing
results/community_arena.json.
"""
import argparse
import json
import random
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

# Catches marked ambiguous (community legitimately disagrees on the
# "right" answer). Excluded from voter-quality scoring but tracked as a
# standalone preference-split datapoint.
AMBIGUOUS_CATCHES = {"catch_user_hijack_cafe"}

DEFAULT_URL = "https://arena.l3vi4th4n.ai/api/votes"
DEFAULT_OUT = Path("results/community_arena.json")


def load_votes(url: str | None, file: str | None) -> list[dict]:
    if file:
        with open(file) as f:
            if file.endswith(".jsonl"):
                return [json.loads(l) for l in f if l.strip()]
            return json.load(f).get("votes", [])
    assert url, "must pass --url or --file"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp).get("votes", [])


def is_nsfw(sid: str) -> bool:
    return "erp_" in (sid or "")


def expected(a: float, b: float) -> float:
    return 1 / (1 + 10 ** ((b - a) / 400))


def compute_elo(matchups, shuffles=100, k=32):
    models = set()
    for a, b, _ in matchups:
        models.add(a)
        models.add(b)
    runs = defaultdict(list)
    for seed in range(shuffles):
        r = {m: 1500 for m in models}
        sh = matchups.copy()
        random.seed(seed)
        random.shuffle(sh)
        for a, b, o in sh:
            e = expected(r[a], r[b])
            r[a] += k * (o - e)
            r[b] += k * ((1 - o) - (1 - e))
        for m, v in r.items():
            runs[m].append(v)
    avg = {m: sum(vs) / len(vs) for m, vs in runs.items()}
    stab = {m: (sum((v - avg[m]) ** 2 for v in vs) / len(vs)) ** 0.5 for m, vs in runs.items()}
    return avg, stab


def tally(votes):
    mw = defaultdict(lambda: [0, 0, 0])
    for v in votes:
        a, b, w = v.get("model_a"), v.get("model_b"), v.get("winner")
        if not a or not b or not w:
            continue
        if w == "tie":
            mw[a][2] += 1
            mw[b][2] += 1
        elif w == "A":
            mw[a][0] += 1
            mw[b][1] += 1
        elif w == "B":
            mw[b][0] += 1
            mw[a][1] += 1
    return mw


def winrate(t):
    w, l, tie = t
    n = w + l + tie
    return (w + 0.5 * tie) / n if n else 0.0, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    votes = load_votes(args.url if not args.file else None, args.file)
    arena = [v for v in votes if v.get("mode") == "arena"]
    catches = [v for v in arena if v.get("is_catch")]
    real = [v for v in arena if not v.get("is_catch")]

    # Voter quality — suspects defined as <50% pass rate on >=2 non-ambiguous catches
    per_voter = defaultdict(lambda: [0, 0])
    for v in catches:
        if v["scenario_id"] in AMBIGUOUS_CATCHES:
            continue
        vid = v.get("voter_id", "anon")
        per_voter[vid][0] += 1
        if v.get("catch_correct"):
            per_voter[vid][1] += 1
    suspects = {vid for vid, (t, c) in per_voter.items() if t >= 2 and c / t < 0.5}

    real_catches = [v for v in catches if v["scenario_id"] not in AMBIGUOUS_CATCHES]
    catch_pass = sum(1 for v in real_catches if v.get("catch_correct"))

    # Ambiguous catch — community preference split
    amb_attentive = [
        v for v in catches
        if v["scenario_id"] in AMBIGUOUS_CATCHES and v.get("voter_id") not in suspects
    ]
    amb_pref_restrained = sum(1 for v in amb_attentive if v.get("catch_correct"))

    # Clean pool
    clean = [v for v in real if v.get("voter_id") not in suspects]
    per_pair = Counter(v["scenario_id"] for v in clean)
    pair_counts = sorted(per_pair.values())

    # SFW / NSFW split
    sfw = [v for v in clean if not is_nsfw(v.get("scenario_id", ""))]
    nsfw = [v for v in clean if is_nsfw(v.get("scenario_id", ""))]

    mw_all = tally(clean)
    mw_sfw = tally(sfw)
    mw_nsfw = tally(nsfw)

    # ELO
    matchups = []
    for v in clean:
        a, b, w = v.get("model_a"), v.get("model_b"), v.get("winner")
        if not a or not b or not w:
            continue
        if w == "tie":
            matchups.append((a, b, 0.5))
        elif w == "A":
            matchups.append((a, b, 1.0))
        elif w == "B":
            matchups.append((a, b, 0.0))
    elo, stab = compute_elo(matchups)

    ranked = sorted(elo.items(), key=lambda x: -x[1])

    # Head-to-head (pairwise records)
    h2h = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for v in clean:
        a, b, w = v.get("model_a"), v.get("model_b"), v.get("winner")
        if not a or not b or not w:
            continue
        if w == "tie":
            h2h[a][b][2] += 1
            h2h[b][a][2] += 1
        elif w == "A":
            h2h[a][b][0] += 1
            h2h[b][a][1] += 1
        elif w == "B":
            h2h[b][a][0] += 1
            h2h[a][b][1] += 1

    # Report
    print(f'Arena votes: {len(arena)}  real: {len(real)}  catches: {len(catches)}')
    print(f'Voters: {len(set(v.get("voter_id","") for v in arena))}  suspects: {len(suspects)}')
    print(f'Catch pass rate (real): {catch_pass}/{len(real_catches)} = {100*catch_pass/max(len(real_catches),1):.0f}%')
    if amb_attentive:
        print(f'Ambiguous catch (restrained vs emotional): {amb_pref_restrained}/{len(amb_attentive)} prefer restrained ({100*amb_pref_restrained/len(amb_attentive):.0f}%)')
    print(f'Clean pool: {len(clean)} votes / {len(per_pair)} pairs')
    if pair_counts:
        print(f'Coverage  min: {pair_counts[0]}  median: {pair_counts[len(pair_counts)//2]}  max: {pair_counts[-1]}')
    print()

    print(f'{"Rank":<5}{"Model":<28}{"ELO":<7}{"±":<6}{"Overall":<14}{"SFW":<14}{"NSFW":<14}')
    print("-" * 88)
    for i, (m, r) in enumerate(ranked):
        a, an = winrate(mw_all[m])
        s, sn = winrate(mw_sfw[m])
        n, nn = winrate(mw_nsfw[m])
        print(
            f'#{i+1:<4}{m:<28}{r:<7.0f}{stab[m]:<6.1f}'
            f'{a*100:>3.0f}% (n={an:<4}){s*100:>3.0f}% (n={sn:<4}){n*100:>3.0f}% (n={nn:<4})'
        )

    # Persist
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "total_arena_votes": len(arena),
        "real_votes": len(real),
        "catch_votes": len(catches),
        "unique_voters": len(set(v.get("voter_id", "") for v in arena)),
        "suspect_voters": len(suspects),
        "catch_pass_rate": round(100 * catch_pass / max(len(real_catches), 1), 1),
        "ambiguous_catch": {
            "attentive_voters": len(amb_attentive),
            "prefer_restrained": amb_pref_restrained,
            "prefer_emotional": len(amb_attentive) - amb_pref_restrained,
            "restrained_pct": round(100 * amb_pref_restrained / max(len(amb_attentive), 1), 1),
        },
        "clean_pool": {
            "votes": len(clean),
            "pairs": len(per_pair),
            "coverage_min": pair_counts[0] if pair_counts else 0,
            "coverage_median": pair_counts[len(pair_counts) // 2] if pair_counts else 0,
            "coverage_max": pair_counts[-1] if pair_counts else 0,
        },
        "leaderboard": [
            {
                "rank": i + 1,
                "model": m,
                "elo": round(r, 1),
                "stability": round(stab[m], 2),
                "overall_winrate": round(winrate(mw_all[m])[0] * 100, 1),
                "overall_n": winrate(mw_all[m])[1],
                "sfw_winrate": round(winrate(mw_sfw[m])[0] * 100, 1),
                "sfw_n": winrate(mw_sfw[m])[1],
                "nsfw_winrate": round(winrate(mw_nsfw[m])[0] * 100, 1),
                "nsfw_n": winrate(mw_nsfw[m])[1],
            }
            for i, (m, r) in enumerate(ranked)
        ],
        "head_to_head": {
            m: {
                opp: {"wins": h2h[m][opp][0], "losses": h2h[m][opp][1], "ties": h2h[m][opp][2]}
                for opp in elo
                if opp != m and sum(h2h[m][opp]) > 0
            }
            for m in elo
        },
    }
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
