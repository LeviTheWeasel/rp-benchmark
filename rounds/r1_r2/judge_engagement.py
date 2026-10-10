#!/usr/bin/env python3
"""Engagement-proxy judge — score "snap-judgment first-impression" quality on
existing single-turn responses, as a proxy for the human single-message
community arena ELO (which only covers 11 of the 20 models).

Re-judges responses already generated in:
    results/run_20260413_155910.json  (Phase A, 11 models)
    results/run_20260502_084528.json  (Phase B, 9 models)
on the SAME scenarios, but with a prompt focused on first-impression
engagement dimensions (hook, voice, sensory density, momentum, vividness)
rather than the full 27-dim rubric.

Output:
    results/engagement_proxy_run.json    (per-response scores)
    results/engagement_proxy.json        (per-model aggregate + validation)

Validation: Spearman ρ between this proxy and Bayesian single-message
arena ELO on the 11 Phase A models. If ρ > 0.7, the proxy is trustworthy
for Phase B. If ρ < 0.4, it measures something different and Phase B
proxy numbers should not be folded into composite.

Cost: ~$1-2 for Sonnet 4 judge × 540 responses (no regeneration).
Time: ~30 min sequential.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.api import chat_completion
from harness.config import JUDGE_MODELS, JUDGE_CONFIG

ROOT = Path(__file__).resolve().parents[2] / "results"
OUT_RAW = ROOT / "engagement_proxy_run.json"
OUT_AGG = ROOT / "engagement_proxy.json"

# Phase A and Phase B single-turn run files. Re-judge their generations.
SOURCES = [
    ROOT / "run_20260413_155910.json",  # Phase A, 11 models × 27 scenarios
    ROOT / "run_20260502_084528.json",  # Phase B, 9 models × 27 scenarios
]


ENGAGEMENT_JUDGE_SYSTEM = """You are evaluating a single-message roleplay response on FIRST-IMPRESSION ENGAGEMENT only. This is the snap-judgment "would I keep reading?" quality, NOT sustained narrative quality over a long arc.

Score each dimension 1-5. For each dimension, write the rationale BEFORE the numeric score.

## Dimensions (score 1-5 each)

**Hook** — Does the opening 1-2 sentences pull the reader in? Strong = an immediate situation, image, or voice that compels attention. Weak = generic setup, exposition, or boilerplate descriptors.

**Voice** — Does the character feel singular and recognizable? Strong = specific cadence, idiosyncratic phrasing, vocabulary that fits ONE character. Weak = could be any character; default-novel narration.

**Sensory** — Does the response invoke concrete senses (sight, sound, touch, smell, taste, kinesthetic)? Strong = specific imagery the reader can see/feel. Weak = abstract emotional words, vague atmosphere.

**Momentum** — Does the response invite the reader to continue? Strong = ends on a charged moment, an unanswered beat, an action that demands response. Weak = closes the scene cleanly with nothing pulling forward.

**Vividness** — Does the prose reward reading? Strong = word choices that are surprising-yet-fitting, specific details, precise verbs. Weak = bland default phrasing, generic adjectives, hedge words.

## Output (strict JSON, keys in order)

```json
{
  "engagement_summary": "2-3 sentence holistic overall impression of the response's first-read appeal. Cite specific phrasing or images. Comes BEFORE any scored dimension.",
  "dimensions": {
    "hook":      {"rationale": "", "score": 0.0},
    "voice":     {"rationale": "", "score": 0.0},
    "sensory":   {"rationale": "", "score": 0.0},
    "momentum":  {"rationale": "", "score": 0.0},
    "vividness": {"rationale": "", "score": 0.0}
  },
  "overall_engagement": 0.0
}
```

`overall_engagement` is the unweighted mean of the 5 dimension scores. Calibration: 3 = adequate, 4 = strong, 5 = exceptional (rare). Most decent responses land 2.5-4.0."""


def judge_one(scenario_id: str, model_key: str, response_text: str, judge_model_id: str):
    """Score a single response on engagement dimensions. Returns parsed JSON or error dict."""
    user_msg = (
        f"<scenario>{scenario_id}</scenario>\n"
        f"<model>{model_key}</model>\n"
        f"<response>\n{response_text}\n</response>\n\n"
        "Score this single-message response on first-impression engagement only. "
        "Begin with engagement_summary, then per-dimension rationale-then-score, "
        "then overall_engagement (unweighted mean of the 5 scores)."
    )
    config = dict(JUDGE_CONFIG)
    config["max_tokens"] = 4000  # CoT prompt + 5 short rationales fit comfortably
    try:
        result = chat_completion(judge_model_id, ENGAGEMENT_JUDGE_SYSTEM, user_msg, config)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

    content = result["content"].strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(l for l in lines if not l.strip().startswith("```"))
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass
        return {"parse_error": True, "raw_content": result["content"]}


def collect_responses():
    """Load Phase A + B run files, return list of (scenario_id, model_key, response_text)."""
    items = []
    for src in SOURCES:
        if not src.exists():
            print(f"  WARN: {src} not found, skipping")
            continue
        d = json.loads(src.read_text())
        for r in d.get("results", []):
            sid = r.get("scenario_id")
            mk = r.get("test_model")
            content = (r.get("generation") or {}).get("content")
            if sid and mk and content:
                items.append((sid, mk, content, src.name))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", default=JUDGE_MODELS["claude_sonnet"],
                    help="Judge model id (OpenRouter slug)")
    ap.add_argument("--limit", type=int, default=None,
                    help="Cap the number of (scenario, model) pairs scored — for smoke testing")
    ap.add_argument("--resume", action="store_true",
                    help="Resume from existing engagement_proxy_run.json")
    args = ap.parse_args()

    items = collect_responses()
    print(f"Loaded {len(items)} (scenario, model) responses to score")

    # Load existing state for resume
    state = {"results": []} if not (args.resume and OUT_RAW.exists()) else json.loads(OUT_RAW.read_text())
    done = {(r["scenario_id"], r["test_model"]) for r in state["results"]}
    print(f"  already scored: {len(done)}")

    if args.limit:
        items = items[:args.limit]

    n_done = 0
    t_start = time.time()
    for sid, mk, content, src_name in items:
        if (sid, mk) in done:
            continue
        n_done += 1
        print(f"  [{n_done}] {sid:<32} {mk:<24}", end=" ", flush=True)
        t0 = time.time()
        scored = judge_one(sid, mk, content, args.judge)
        dt = time.time() - t0
        overall = scored.get("overall_engagement") if isinstance(scored, dict) else None
        if overall is None:
            print(f"PARSE-ERROR ({dt:.0f}s)")
        else:
            print(f"engagement={overall:.2f} ({dt:.0f}s)")
        state["results"].append({
            "scenario_id": sid,
            "test_model": mk,
            "source": src_name,
            "scores": scored,
        })
        OUT_RAW.write_text(json.dumps(state, indent=2))

    print(f"\n{n_done} new judgments in {time.time() - t_start:.0f}s")
    print(f"Saved per-response: {OUT_RAW}")

    # Aggregate per-model
    print("\nAggregating per-model engagement scores...")
    by_model = {}
    parse_errors = 0
    for r in state["results"]:
        sc = r["scores"]
        if not isinstance(sc, dict) or sc.get("parse_error") or sc.get("error"):
            parse_errors += 1
            continue
        ov = sc.get("overall_engagement")
        if ov is None:
            parse_errors += 1
            continue
        by_model.setdefault(r["test_model"], []).append(float(ov))

    if parse_errors:
        print(f"  parse-errors / missing scores: {parse_errors}")

    import statistics as st
    per_model = {
        m: {
            "engagement_mean": round(st.mean(vs), 4),
            "engagement_std":  round(st.stdev(vs), 4) if len(vs) > 1 else None,
            "n_scored":        len(vs),
        }
        for m, vs in sorted(by_model.items())
    }

    # Validate: Spearman ρ vs Bayesian single-message arena ELO on Phase A overlap
    arena_path = ROOT / "community_arena_bayesian.json"
    validation = None
    if arena_path.exists():
        arena = json.loads(arena_path.read_text())
        elo = {e["model"]: e["elo_mean"] for e in arena["leaderboard"]}
        common = sorted(m for m in per_model if m in elo)
        if len(common) >= 3:
            from scipy.stats import spearmanr
            xs = [per_model[m]["engagement_mean"] for m in common]
            ys = [elo[m] for m in common]
            rho, p = spearmanr(xs, ys)
            validation = {
                "n_models_overlap": len(common),
                "rho_vs_human_arena_elo": round(float(rho), 4),
                "p_value":               round(float(p), 4),
                "interpretation":        (
                    "trustworthy as proxy" if rho > 0.7
                    else "moderate proxy"   if rho > 0.4
                    else "weak / suspect proxy"
                ),
            }
            print(f"\nValidation: ρ(proxy, human arena ELO) on {len(common)} models = "
                  f"{rho:+.3f}  (p = {p:.3f})  [{validation['interpretation']}]")
        else:
            print("\nValidation skipped: too few models overlap with single-msg arena.")

    output = {
        "judge_model": args.judge,
        "n_responses_scored": sum(p["n_scored"] for p in per_model.values()),
        "validation_against_human_single_msg_arena": validation,
        "per_model": per_model,
    }
    OUT_AGG.write_text(json.dumps(output, indent=2))
    print(f"\nSaved per-model: {OUT_AGG}")


if __name__ == "__main__":
    main()
