#!/usr/bin/env python3
"""Aggregate flaw hunter results (0-100 scale with quoted flaws)."""
import json
import sys
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def main():
    run_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not run_path:
        # Find latest
        results_dir = Path(__file__).parent / "results"
        runs = sorted(results_dir.glob("run_*.json"), reverse=True)
        if not runs:
            print("No runs found")
            return
        run_path = runs[0]

    with open(run_path) as f:
        run = json.load(f)

    # Collect scores per model
    model_scores = defaultdict(list)
    model_flaw_counts = defaultdict(lambda: {"fatal": [], "major": [], "minor": [], "bonuses": []})
    model_scenarios = defaultdict(list)
    flaw_types = defaultdict(lambda: Counter())

    total_evals = 0
    parse_failures = 0

    for r in run["results"]:
        if "error" in r:
            continue
        model = r.get("test_model")
        scenario = r.get("scenario_id", "")

        # Detect language
        lang = "ru" if any(x in scenario for x in ["lucian", "agora", "valdrian", "narlos", "rowena", "exiledking"]) else "en"

        for judge, jdata in r.get("judges", {}).items():
            total_evals += 1
            scores = jdata.get("scores", {})

            if "final_score" not in scores:
                parse_failures += 1
                continue

            model_scores[model].append(scores["final_score"])
            model_scenarios[model].append({"scenario": scenario, "score": scores["final_score"], "lang": lang})

            fatal = scores.get("fatal_flaws", [])
            major = scores.get("major_flaws", [])
            minor = scores.get("minor_flaws", [])
            bonuses = scores.get("bonuses", [])

            model_flaw_counts[model]["fatal"].append(len(fatal))
            model_flaw_counts[model]["major"].append(len(major))
            model_flaw_counts[model]["minor"].append(len(minor))
            model_flaw_counts[model]["bonuses"].append(len(bonuses))

            for f in fatal:
                flaw_types[model][f.get("flaw", "unknown")] += 1
            for f in major:
                flaw_types[model][f.get("flaw", "unknown")] += 1

    # Leaderboard
    leaderboard = []
    for model, scores in model_scores.items():
        if not scores:
            continue
        avg = sum(scores) / len(scores)
        mn = min(scores)
        mx = max(scores)

        fc = model_flaw_counts[model]
        avg_fatal = sum(fc["fatal"]) / len(fc["fatal"]) if fc["fatal"] else 0
        avg_major = sum(fc["major"]) / len(fc["major"]) if fc["major"] else 0
        avg_minor = sum(fc["minor"]) / len(fc["minor"]) if fc["minor"] else 0
        avg_bonus = sum(fc["bonuses"]) / len(fc["bonuses"]) if fc["bonuses"] else 0

        leaderboard.append({
            "model": model,
            "avg_score": round(avg, 1),
            "min": mn,
            "max": mx,
            "n": len(scores),
            "avg_fatal": round(avg_fatal, 2),
            "avg_major": round(avg_major, 1),
            "avg_minor": round(avg_minor, 1),
            "avg_bonus": round(avg_bonus, 2),
        })

    leaderboard.sort(key=lambda x: -x["avg_score"])

    print()
    print("=" * 86)
    print("  RP-BENCH FLAW HUNTER LEADERBOARD")
    print("  Run: %s | Evals: %d | Parse failures: %d" % (
        Path(run_path).stem, total_evals, parse_failures,
    ))
    print("=" * 86)
    print()
    print("  %-5s %-24s %-9s %-7s %-7s %-9s %-9s %-9s %-9s" % (
        "Rank", "Model", "Score", "Min", "Max", "Fatal", "Major", "Minor", "Bonus"
    ))
    print("  " + "-" * 82)
    for i, entry in enumerate(leaderboard):
        print("  #%-4d %-24s %-9.1f %-7d %-7d %-9.2f %-9.1f %-9.1f %-9.2f" % (
            i + 1,
            entry["model"],
            entry["avg_score"],
            entry["min"],
            entry["max"],
            entry["avg_fatal"],
            entry["avg_major"],
            entry["avg_minor"],
            entry["avg_bonus"],
        ))
    print("  " + "-" * 82)

    # Per-language breakdown
    print()
    print("  BREAKDOWN BY LANGUAGE")
    print("  " + "-" * 50)
    for model in [e["model"] for e in leaderboard]:
        en_scores = [s["score"] for s in model_scenarios[model] if s["lang"] == "en"]
        ru_scores = [s["score"] for s in model_scenarios[model] if s["lang"] == "ru"]
        en_avg = sum(en_scores) / len(en_scores) if en_scores else 0
        ru_avg = sum(ru_scores) / len(ru_scores) if ru_scores else 0
        diff = ru_avg - en_avg if en_scores and ru_scores else 0
        print("  %-24s EN %.1f (%d) | RU %.1f (%d) | RU-EN: %+.1f" % (
            model, en_avg, len(en_scores), ru_avg, len(ru_scores), diff
        ))

    # Most common flaws per model
    print()
    print("  TOP FLAWS PER MODEL")
    print("  " + "-" * 60)
    for model in [e["model"] for e in leaderboard]:
        top = flaw_types[model].most_common(3)
        top_str = ", ".join("%s(%d)" % (f, c) for f, c in top)
        print("  %-24s %s" % (model, top_str))

    # Save aggregate
    out_path = Path(run_path).parent / ("flaw_leaderboard_%s.json" % Path(run_path).stem.replace("run_", ""))
    with open(out_path, "w") as f:
        json.dump({
            "run_id": Path(run_path).stem,
            "total_evals": total_evals,
            "parse_failures": parse_failures,
            "leaderboard": leaderboard,
            "flaw_types_by_model": {m: dict(c) for m, c in flaw_types.items()},
        }, f, indent=2, ensure_ascii=False)
    print()
    print("Saved: %s" % out_path)


if __name__ == "__main__":
    main()
