#!/usr/bin/env python3
"""Aggregate the round-3 (NSFW) multi-turn judge data into a leaderboard.

Reads results/round3gen_R3_nsfw.json (dual-judge: claude_sonnet + deepseek_r1).
Outputs:
  - results/round3_nsfw_leaderboard.json — per-model aggregates
  - a markdown table (stdout) for the README, ranked by the discriminating
    judge (Sonnet); DeepSeek R1 is reported alongside (it ceilings near 5.0).

Refusal is a SEPARATE willingness axis: % of sessions where any judge flagged
refused_midscene. NOT folded into the craft scores.

Usage: python3 rounds/r3/analyze_round3_nsfw.py
"""
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

SRC = Path("results/round3gen_R3_nsfw.json")
OUT = Path("results/round3_nsfw_leaderboard.json")

NAMES = {
    "claude_opus_4_6": "Claude Opus 4.6", "claude_opus_4_7": "Claude Opus 4.7",
    "claude_opus_4_8": "Claude Opus 4.8", "claude_sonnet_4_5": "Claude Sonnet 4.5",
    "claude_sonnet_4_6": "Claude Sonnet 4.6", "gpt_4_1": "GPT-4.1", "gpt_5_5": "GPT-5.5",
    "gemini_2_5_flash": "Gemini 2.5 Flash", "gemini_3_1_pro": "Gemini 3.1 Pro",
    "gemini_3_1_flash_lite": "Gemini 3.1 Flash Lite", "gemini_3_5_flash": "Gemini 3.5 Flash",
    "deepseek_v3_2": "DeepSeek V3.2", "deepseek_v3_0324": "DeepSeek V3 0324",
    "deepseek_v4_pro": "DeepSeek V4 Pro", "deepseek_v4_flash": "DeepSeek V4 Flash",
    "deepseek_r1_0528": "DeepSeek R1 0528", "glm_4_7": "GLM 4.7", "glm_5_1": "GLM 5.1",
    "gemma_4_26b": "Gemma 4 26B", "gemma_4_31b": "Gemma 4 31B", "grok_4_3": "Grok 4.3",
    "minimax_m2_7": "MiniMax M2.7", "minimax_m3": "MiniMax M3",
    "qwen3_5_flash": "Qwen 3.5 Flash", "qwen3_6_27b": "Qwen 3.6 27B",
    "qwen3_6_35b_a3b": "Qwen 3.6 35B A3B", "qwen3_7_max": "Qwen 3.7 Max",
    "kimi_k2_5": "Kimi K2.5", "kimi_k2_6": "Kimi K2.6", "mimo_2_5_pro": "MiMo 2.5 Pro",
    "owl_alpha": "Owl Alpha", "llama_4_maverick": "Llama 4 Maverick",
    "mistral_small_2603": "Mistral Small 2603", "euryale_70b": "Euryale L3.3 70B",
    "magnum_v4_72b": "Magnum v4 72B", "cydonia_24b": "Cydonia 24B",
    "skyfall_36b": "Skyfall 36B", "lunaris_8b": "Lunaris 8B",
    "rocinante_12b": "Rocinante 12B", "unslopnemo_12b": "UnslopNemo 12B",
}
SPECIALISTS = {"euryale_70b", "magnum_v4_72b", "cydonia_24b", "skyfall_36b",
               "lunaris_8b", "rocinante_12b", "unslopnemo_12b"}


def dim(sd, *names):
    for n in names:
        v = sd.get(n)
        if isinstance(v, dict) and v.get("score") is not None:
            return v["score"]
    return None


def main():
    d = json.load(open(SRC))
    sessions = [s for s in d["sessions"] if "error" not in s and s.get("judges")]
    acc = defaultdict(lambda: {"sonnet": [], "r1": [], "s7": [], "s8": [], "s9": [],
                               "s1": [], "s2": [], "s3": [], "refused_sessions": 0, "n": 0})
    for s in sessions:
        m = acc[s["test_model"]]
        m["n"] += 1
        refused = False
        for jk, jd in s["judges"].items():
            sc = jd.get("scores", {})
            if sc.get("parse_error"):
                continue
            ov = sc.get("overall")
            if ov is not None:
                m["sonnet" if jk == "claude_sonnet" else "r1"].append(ov)
            sdm = sc.get("session_dimensions", {})
            for k, names in [("s7", ["S.7_escalation_pacing"]),
                             ("s8", ["S.8_anatomical_spatial_coherence", "S.8_anatomical_coherence"]),
                             ("s9", ["S.9_consent_agency_intimacy", "S.9_consent_agency"]),
                             ("s1", ["S.1_consistency_over_time"]),
                             ("s2", ["S.2_degradation_resistance"]),
                             ("s3", ["S.3_narrative_momentum"])]:
                v = dim(sdm, *names)
                if v is not None:
                    m[k].append(v)
            if (sc.get("refusal") or {}).get("refused_midscene") is True:
                refused = True
        if refused:
            m["refused_sessions"] += 1

    mean = lambda x: round(st.mean(x), 2) if x else None
    rows = []
    for k, m in acc.items():
        rows.append({
            "model": k, "name": NAMES.get(k, k), "n": m["n"],
            "is_specialist": k in SPECIALISTS,
            "sonnet_overall": mean(m["sonnet"]), "r1_overall": mean(m["r1"]),
            "craft_mean": mean(m["sonnet"] + m["r1"]),
            "S7_escalation_pacing": mean(m["s7"]),
            "S8_anatomical_coherence": mean(m["s8"]),
            "S9_consent_agency": mean(m["s9"]),
            "S1_consistency": mean(m["s1"]), "S2_degradation": mean(m["s2"]),
            "S3_momentum": mean(m["s3"]),
            "refusal_rate_pct": round(100 * m["refused_sessions"] / m["n"], 1) if m["n"] else None,
        })
    # rank by the discriminating judge (Sonnet), then mean
    rows.sort(key=lambda r: (r["sonnet_overall"] or 0, r["craft_mean"] or 0), reverse=True)

    out = {
        "round": 3, "type": "nsfw_multiturn_judge", "n_sessions": len(sessions),
        "n_models": len(rows), "judges": ["claude_sonnet", "deepseek_r1"],
        "note": "Judge-scored only (no human arena votes yet). Ranked by Sonnet "
                "overall; DeepSeek R1 ceilings ~5.0 (low discrimination). Refusal "
                "is a separate willingness axis. venice_dolphin_24b dropped (:free unusable).",
        "leaderboard": rows,
    }
    json.dump(out, open(OUT, "w"), indent=2, ensure_ascii=False)
    print(f"wrote {OUT}  ({len(rows)} models, {len(sessions)} sessions)\n")

    # markdown table for README
    print("| Rank | Model | Craft (Sonnet) | Craft (R1) | Pacing | Anatomy | Consent | Refusal % | n |")
    print("|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        nm = r["name"] + (" *(RP-tuned)*" if r["is_specialist"] else "")
        print(f"| #{i} | {nm} | {r['sonnet_overall']:.2f} | {r['r1_overall']:.2f} | "
              f"{r['S7_escalation_pacing']:.2f} | {r['S8_anatomical_coherence']:.2f} | "
              f"{r['S9_consent_agency']:.2f} | {r['refusal_rate_pct']:.0f} | {r['n']} |")


if __name__ == "__main__":
    main()
