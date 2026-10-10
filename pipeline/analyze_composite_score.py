#!/usr/bin/env python3
"""Composite RP-Bench Score — single sortable headline + dimensional breakdown.

Aggregates metrics across the 20-model pool into a quality composite and
three independent dimensions (Engagement, Speed, Cost), reflecting the
paper's central finding that single-message and multi-turn evaluations
measure different latent qualities.

Composite (sustained-quality axis, 0–100):
    0.35  multi-turn arena ELO  (humans, full dialogues)
    0.25  LLM-judge multi-turn Likert  (Sonnet 4 holistic, 1–5)
    0.20  single-turn 27-dim rubric overall  (Sonnet 4)
    0.15  flaw-hunter session mean  (Sonnet 4 with primer)
    0.05  behavioral composite  (TTR + 1 − bigram_repetition, z-mean)

Each metric -> z-score across pool -> weighted sum -> percentile -> 0-100.
Missing values impute z=0 (population mean) and the row gets a "*" flag.

Engagement (separate axis, 0-100):
    Single-message community arena ELO percentile.
    Surfaces snap-judgment-engagement quality. Not folded into Composite
    because the paper shows it measures a different latent.

Speed (0-100):  1 / median_gen_seconds  percentile.
Cost  (0-100):  1 / median_actual_cost  percentile (BYOK = top).

Output:
    results/composite_leaderboard.json
    + sorted table to stdout
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "results"

WEIGHTS = {
    "mt_arena":   0.35,
    "llm_judge":  0.25,
    "rubric":     0.20,
    "flaw":       0.15,
    "behavioral": 0.05,
}


def safe_load(name):
    p = ROOT / name
    if not p.exists():
        return None
    return json.loads(p.read_text())


def load_27dim_rubric():
    """Return {model: overall_score} from any available 27-dim leaderboards.
    Merges Phase A + Phase B if both exist; takes max-models-coverage version
    when overlap occurs.
    """
    out = {}
    for f in sorted(ROOT.glob("leaderboard_*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if not (isinstance(d, dict) and "leaderboard" in d):
            continue
        for entry in d["leaderboard"]:
            m = entry.get("model")
            score = entry.get("overall")
            if m and score is not None:
                # If model already there, keep the LATER (higher run_id) version
                # (later sort iteration overwrites)
                out[m] = score
    return out


def zscore(values: dict[str, float]) -> dict[str, float]:
    """Z-score a per-model dict. Returns {} if fewer than 2 values."""
    vals = [v for v in values.values() if v is not None]
    if len(vals) < 2:
        return {m: 0.0 for m in values}
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / max(1, len(vals) - 1)
    sd = math.sqrt(var) if var > 0 else 1.0
    return {m: (v - mean) / sd if v is not None else 0.0
            for m, v in values.items()}


def percentile_0_100(values: dict[str, float]) -> dict[str, float]:
    """Convert per-model values to a 0-100 percentile rank."""
    items = [(m, v) for m, v in values.items() if v is not None]
    if not items:
        return {m: None for m in values}
    items.sort(key=lambda x: x[1])
    n = len(items)
    rank = {m: (i + 0.5) / n * 100 for i, (m, _) in enumerate(items)}
    return {m: rank.get(m) for m in values}


def main():
    # --- Load each metric source ---
    mt_arena_raw = safe_load("multiturn_arena_bayesian.json")
    profiles     = safe_load("model_profiles.json")
    flaw_summary = safe_load("flaw_hunter_session_summary.json")
    behavioral   = safe_load("behavioral_metrics.json")
    ca_arena     = safe_load("community_arena_bayesian.json")
    latency      = safe_load("latency_leaderboard.json")

    rubric_overall = load_27dim_rubric()

    # Per-model values
    mt_arena = {e["model"]: e["elo_mean"]
                for e in mt_arena_raw["leaderboard"]} if mt_arena_raw else {}
    likert = {m: (p.get("multiturn_llm_judge") or {}).get("overall_mean")
              for m, p in (profiles or {}).items()}
    flaw_mean = {m: d["mean"] for m, d in
                 (flaw_summary.get("per_model") if flaw_summary else {} or {}).items()}
    ca_elo = {e["model"]: e["elo_mean"]
              for e in ca_arena["leaderboard"]} if ca_arena else {}
    lat = (latency or {}).get("per_model", {})

    # Behavioral composite: per-model average z-score across (TTR, 1 − repetition).
    # Both higher = better.
    behav_per_model = (behavioral or {}).get("per_model", {})
    ttr = {m: d["unique_word_ratio"]["mean"] for m, d in behav_per_model.items()}
    inv_rep = {m: 1 - d["bigram_repetition"]["mean"] for m, d in behav_per_model.items()}
    z_ttr = zscore(ttr)
    z_inv_rep = zscore(inv_rep)
    behav_composite = {
        m: (z_ttr.get(m, 0) + z_inv_rep.get(m, 0)) / 2
        for m in set(ttr) | set(inv_rep)
    }

    # --- Determine the model pool ---
    # All 20 production models from anywhere available, excluding the user
    # simulator role (gemini_2_5_flash dual-role; we keep it as a test model
    # but flag elsewhere) and the judges (claude_sonnet / claude_sonnet_4 /
    # ref:* reference characters / sukuna baseline).
    EXCLUDE = {"claude_sonnet", "claude_sonnet_4", "ref:sukuna", "sukuna", "prebuilt"}
    models = sorted((set(
        list(mt_arena) + list(likert) + list(flaw_mean) + list(rubric_overall)
    )) - EXCLUDE)

    # --- Z-score each metric ---
    z_mt_arena   = zscore({m: mt_arena.get(m) for m in models})
    z_llm_judge  = zscore({m: likert.get(m) for m in models})
    z_rubric     = zscore({m: rubric_overall.get(m) for m in models})
    z_flaw       = zscore({m: flaw_mean.get(m) for m in models})
    z_behavioral = {m: behav_composite.get(m, 0.0) for m in models}

    # --- Composite z and percentile ---
    composite_z = {}
    flags = {}
    for m in models:
        missing = []
        if mt_arena.get(m) is None:        missing.append("MT")
        if likert.get(m) is None:           missing.append("LJ")
        if rubric_overall.get(m) is None:   missing.append("RB")
        if flaw_mean.get(m) is None:        missing.append("FH")
        flags[m] = "*" if missing else ""
        composite_z[m] = (
            WEIGHTS["mt_arena"]   * z_mt_arena.get(m, 0)
          + WEIGHTS["llm_judge"]  * z_llm_judge.get(m, 0)
          + WEIGHTS["rubric"]     * z_rubric.get(m, 0)
          + WEIGHTS["flaw"]       * z_flaw.get(m, 0)
          + WEIGHTS["behavioral"] * z_behavioral.get(m, 0)
        )
    composite_pct = percentile_0_100(composite_z)

    # --- Independent axes ---
    engagement_pct = percentile_0_100({m: ca_elo.get(m) for m in models})

    speed_raw = {m: 1.0 / lat[m]["median_gen_ms"] if m in lat and lat[m]["median_gen_ms"] else None
                 for m in models}
    speed_pct = percentile_0_100(speed_raw)

    # Cost: 1 / median_actual_cost; BYOK ($0) gets top percentile via a sentinel
    cost_raw = {}
    for m in models:
        if m not in lat:
            cost_raw[m] = None
            continue
        c = lat[m].get("median_actual_cost_usd")
        if c is None:
            cost_raw[m] = None
        elif c <= 0:
            cost_raw[m] = 1e9  # BYOK / free → top of the pile
        else:
            cost_raw[m] = 1.0 / c
    cost_pct = percentile_0_100(cost_raw)

    # --- Build leaderboard ---
    rows = []
    for m in models:
        rows.append({
            "model": m,
            "composite_score": round(composite_pct.get(m, 0) or 0, 1),
            "composite_z": round(composite_z.get(m, 0), 3),
            "engagement_score": (None if engagement_pct.get(m) is None
                                 else round(engagement_pct[m], 1)),
            "speed_score":     (None if speed_pct.get(m) is None
                                else round(speed_pct[m], 1)),
            "cost_score":      (None if cost_pct.get(m) is None
                                else round(cost_pct[m], 1)),
            "missing_flag":    flags[m],
            "raw": {
                "mt_arena_elo":          mt_arena.get(m),
                "llm_judge_likert":      likert.get(m),
                "rubric_overall":        rubric_overall.get(m),
                "flaw_hunter_mean":      flaw_mean.get(m),
                "behavioral_composite_z": round(z_behavioral.get(m, 0), 3),
                "ca_arena_elo":          ca_elo.get(m),
                "median_gen_ms":         lat.get(m, {}).get("median_gen_ms"),
                "median_actual_cost":    lat.get(m, {}).get("median_actual_cost_usd"),
            },
        })
    rows.sort(key=lambda r: -r["composite_score"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    # --- Print ---
    print("=" * 100)
    print("RP-BENCH COMPOSITE LEADERBOARD")
    print("=" * 100)
    print(f"{'Rank':<6}{'Model':<26}{'Composite':<11}{'Engagement':<12}{'Speed':<8}{'Cost':<8}{'Flag'}")
    print("-" * 100)
    for r in rows:
        eng = "—" if r["engagement_score"] is None else f"{r['engagement_score']:.0f}"
        spd = "—" if r["speed_score"]      is None else f"{r['speed_score']:.0f}"
        cst = "—" if r["cost_score"]       is None else f"{r['cost_score']:.0f}"
        print(f"{r['rank']:<6}{r['model']:<26}"
              f"{r['composite_score']:<11.1f}{eng:<12}{spd:<8}{cst:<8}{r['missing_flag']}")

    print()
    print("Composite weights: 0.35 MT-arena ELO + 0.25 LLM-judge Likert + 0.20 27-dim rubric")
    print("                 + 0.15 flaw-hunter mean + 0.05 behavioral (TTR + 1-bigram_rep).")
    print("Flag * = at least one component missing; imputed as population mean (z=0).")
    print()
    print("Engagement = single-message arena ELO percentile (separate latent dimension).")
    print("Speed      = 1 / median generation seconds, percentile.")
    print("Cost       = 1 / median per-call $ (BYOK / free = top percentile).")

    out = {
        "weights": WEIGHTS,
        "n_models": len(rows),
        "leaderboard": rows,
    }
    out_path = ROOT / "composite_leaderboard.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
