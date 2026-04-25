"""RP-Bench Leaderboard — HuggingFace Spaces interactive view.

Renders all the project's findings as sortable, filterable Gradio
DataFrames + per-model profile cards + methodology callouts. Data is
pulled from the `lazyweasel/roleplay-bench` HF dataset on startup so
the Space stays in sync with the source of truth.

Run locally:
    pip install gradio pandas pyarrow huggingface_hub
    python app.py

Deploy: push this folder to a new HF Space (Gradio template).
"""
from __future__ import annotations

import json
import os
from io import StringIO
from pathlib import Path

import gradio as gr
import pandas as pd

try:
    from huggingface_hub import hf_hub_download
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

DATASET_REPO = "lazyweasel/roleplay-bench"


def fetch(filename: str, subdir: str = "") -> Path | None:
    """Try local first (when running in repo), then HF hub.

    Order:
    1. ../results/<filename>      — repo's analysis output dir
    2. ../hf_dataset/analysis/<filename>  — bundled analysis copy
    3. ../hf_dataset/<filename>
    4. ../<filename>
    5. ./<filename>
    6. HF dataset analysis/<filename>
    7. HF dataset <filename> (root)
    """
    local_paths = [
        Path("..") / "results" / filename,
        Path("..") / "hf_dataset" / "analysis" / filename,
        Path("..") / "hf_dataset" / filename,
        Path("..") / filename,
        Path(filename),
    ]
    for p in local_paths:
        if p.exists():
            return p
    if HF_AVAILABLE:
        # Try analysis/ subdir first, then root
        for candidate in (f"analysis/{filename}", filename):
            try:
                path_str = hf_hub_download(
                    repo_id=DATASET_REPO, filename=candidate, repo_type="dataset"
                )
                return Path(path_str)
            except Exception:
                continue
    return None


def safe_load_json(filename: str) -> dict | None:
    p = fetch(filename)
    if not p:
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def safe_read_text(filename: str) -> str:
    p = fetch(filename)
    return p.read_text() if p else f"_{filename} not found_"


# -----------------------------------------------------------------------------
# Data loaders
# -----------------------------------------------------------------------------

def community_arena_df() -> pd.DataFrame:
    """Bayesian-corrected community arena leaderboard."""
    bayes = safe_load_json("community_arena_bayesian.json")
    freq = safe_load_json("community_arena_2000.json")
    if not bayes:
        return pd.DataFrame({"note": ["Community arena data unavailable"]})

    rows = []
    freq_by_model = {e["model"]: e for e in (freq or {}).get("leaderboard", [])}
    for e in bayes["leaderboard"]:
        f = freq_by_model.get(e["model"], {})
        rows.append({
            "Rank": e["rank"],
            "Model": e["model"],
            "Bayesian ELO": round(e["elo_mean"], 0),
            "± std": round(e["elo_std"], 0),
            "95% CI": f"[{e['ci_low_95']:.0f}, {e['ci_high_95']:.0f}]",
            "Frequentist ELO": round(f.get("elo", 0), 0) if f else None,
            "Win rate": f"{f.get('overall_winrate', 0):.0f}%" if f else "—",
            "SFW": f"{f.get('sfw_winrate', 0):.0f}%" if f else "—",
            "NSFW": f"{f.get('nsfw_winrate', 0):.0f}%" if f else "—",
            "Votes": f.get("overall_n", 0) if f else 0,
        })
    return pd.DataFrame(rows)


def multiturn_df() -> pd.DataFrame:
    """LLM-judge multi-turn leaderboard (full 20 models)."""
    profiles = safe_load_json("model_profiles.json")
    if not profiles:
        return pd.DataFrame({"note": ["Profile data unavailable"]})

    rows = []
    for m, p in profiles.items():
        mt = p.get("multiturn_llm_judge", {}).get("overall_mean")
        fm = p.get("failure_modes", {})
        rows.append({
            "Model": m,
            "MT mean": mt,
            "F1 agency": fm.get("F1_agency", {}).get("mean"),
            "F2 POV": fm.get("F2_pov_tense", {}).get("mean"),
            "F3 lore": fm.get("F3_lore_contradiction", {}).get("mean"),
            "F8 momentum": fm.get("F8_narrative_momentum", {}).get("mean"),
            "F12 sysprompt": fm.get("F12_instruction_drift", {}).get("mean"),
            "F13 big-card": fm.get("F13_context_attention_loss", {}).get("mean"),
            "Avg fail rank": p.get("avg_failure_rank"),
        })
    return pd.DataFrame(rows).sort_values("MT mean", ascending=False).reset_index(drop=True)


def flaw_hunter_df() -> pd.DataFrame:
    fh = safe_load_json("flaw_hunter_session_summary.json")
    if not fh:
        return pd.DataFrame({"note": ["Flaw hunter data unavailable"]})

    rows = []
    for m, d in fh["per_model"].items():
        rows.append({
            "Model": m,
            "Mean": d["mean"],
            "Median": d["median"],
            "Min": d["min"],
            "Max": d["max"],
            "Fatal/session": d["fatal_per_session"],
            "Major/session": d["major_per_session"],
            "n": d["n"],
        })
    return pd.DataFrame(rows).sort_values("Mean", ascending=False).reset_index(drop=True)


def cost_efficiency_df() -> pd.DataFrame:
    ce = safe_load_json("cost_efficiency.json")
    if not ce:
        return pd.DataFrame({"note": ["Cost data unavailable"]})

    rows = []
    for r in ce["leaderboard"]:
        rows.append({
            "Model": r["model"],
            "$/1M": r["cost_per_1m"],
            "Likert": r["likert"],
            "Likert/$": r["likert_per_dollar"],
            "Flaw hunter": r["fh"],
            "FH/$": r["fh_per_dollar"],
            "Bayesian ELO": r["bayesian_elo"],
        })
    return pd.DataFrame(rows)


def behavioral_df() -> pd.DataFrame:
    b = safe_load_json("behavioral_metrics.json")
    if not b:
        return pd.DataFrame({"note": ["Behavioral metrics unavailable"]})

    pop = b["population"]
    rows = []
    for m, d in b["per_model"].items():
        rows.append({
            "Model": m,
            "Avg words": round(d["word_count"]["mean"], 0),
            "Unique-word ratio": round(d["unique_word_ratio"]["mean"], 3),
            "Bigram repetition": round(d["bigram_repetition"]["mean"], 3),
            "Sentence-length var": round(d["sentence_length_var"]["mean"], 1),
        })
    df = pd.DataFrame(rows).sort_values("Unique-word ratio", ascending=False).reset_index(drop=True)
    return df


def correlation_df() -> pd.DataFrame:
    c = safe_load_json("method_correlations.json")
    if not c:
        return pd.DataFrame({"note": ["Correlation data unavailable"]})

    methods = c["methods"]
    matrix = c["spearman_matrix"]
    rows = []
    for a in methods:
        row = {"method": a}
        for b in methods:
            v = matrix[a][b]
            row[b] = v if v is not None else "—"
        rows.append(row)
    return pd.DataFrame(rows)


def profile_card(model: str) -> str:
    """Render a single model's profile card from profile_cards.md."""
    p = fetch("profile_cards.md")
    if not p:
        return "_Profile card data unavailable_"
    text = p.read_text()
    # Find the section starting with `### {model}` until the next `### `
    needle = f"### {model}\n"
    idx = text.find(needle)
    if idx < 0:
        return f"_No profile card for {model}_"
    end = text.find("### ", idx + len(needle))
    return text[idx:end] if end > 0 else text[idx:]


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

INTRO = """
# RP-Bench: Roleplay Quality Benchmark

Multi-judge, community-calibrated benchmark for LLM roleplay quality. **2,013 community arena votes / 338 voters / 20 models / 336 multi-turn sessions / 270 flaw hunter scores.**

Three core findings drive everything else:

1. **LLM judges disagree with humans.** Spearman correlation between Bayesian community ELO and every LLM-judge method is between **−0.31 and −0.07**. The community measures something the judges cannot.
2. **Engagement and reliability are orthogonal axes.** Community ranks Gemma 4 26B / Mistral / Gemini at the top. Frontier closed models (Opus, Sonnet, GPT-4.1) lead on rule-following but trail on community engagement. Pick by use case.
3. **Position bias breaks single-pass pairwise.** When we ran the same 168 LLM-judged pairwise comparisons twice with A/B swapped, **64% of pairs flipped** their answer. Bidirectional evaluation is mandatory.

Data: [`lazyweasel/roleplay-bench`](https://huggingface.co/datasets/lazyweasel/roleplay-bench).  Code: [github.com/LeviTheWeasel/rp-benchmark](https://github.com/LeviTheWeasel/rp-benchmark).
Live community arena: [arena.l3vi4th4n.ai](https://arena.l3vi4th4n.ai/arena).
"""

NOTES = {
    "Community arena": "Bayesian Bradley-Terry ELO from 1,857 clean (suspect-filtered) human pairwise votes. 95% CI is wide (~260 points) — the top tier is statistically tied. Frequentist columns from the 100-shuffle ELO for comparison.",
    "Multi-turn judge": "Sonnet 4 holistic Likert scores per session. F1-F13 columns are means on the seeds that target each failure mode. Lower 'Avg fail rank' = better cross-mode reliability.",
    "Flaw hunter": "Strict 100-point deduction rubric. Mean ~36, median ~42 across all sessions — the methodology forces lower scores than the Likert. Fatal/session column is the rate of -15 deductions; high values flag catastrophic single sessions.",
    "Cost efficiency": "Quality per dollar at OpenRouter prices (60/40 input/output blend, $/1M tokens). DeepSeek V4 Flash is 281× more cost-efficient than Opus 4.7 on flaw hunter for marginal quality difference.",
    "Behavioral": "Pure prose statistics across all 3,569 model-generated responses. Cannot be gamed by judge taste. Length-biased — compare within tiers, not across.",
    "Correlations": "Spearman rank correlation between every pair of methods. **Bayesian ELO row** is the headline: it's uncorrelated with every LLM-judge method.",
}


def model_list() -> list[str]:
    profiles = safe_load_json("model_profiles.json") or {}
    return sorted(profiles.keys())


with gr.Blocks(title="RP-Bench Leaderboard", theme=gr.themes.Soft()) as demo:
    gr.Markdown(INTRO)

    with gr.Tabs():
        with gr.Tab("Community Arena (humans)"):
            gr.Markdown("### " + NOTES["Community arena"])
            gr.DataFrame(value=community_arena_df, interactive=False, wrap=True)

        with gr.Tab("Multi-Turn Judge"):
            gr.Markdown("### " + NOTES["Multi-turn judge"])
            gr.DataFrame(value=multiturn_df, interactive=False, wrap=True)

        with gr.Tab("Flaw Hunter"):
            gr.Markdown("### " + NOTES["Flaw hunter"])
            gr.DataFrame(value=flaw_hunter_df, interactive=False, wrap=True)

        with gr.Tab("Cost Efficiency"):
            gr.Markdown("### " + NOTES["Cost efficiency"])
            gr.DataFrame(value=cost_efficiency_df, interactive=False, wrap=True)

        with gr.Tab("Behavioral Metrics"):
            gr.Markdown("### " + NOTES["Behavioral"])
            gr.DataFrame(value=behavioral_df, interactive=False, wrap=True)

        with gr.Tab("Method Correlations"):
            gr.Markdown("### " + NOTES["Correlations"])
            gr.DataFrame(value=correlation_df, interactive=False, wrap=True)

        with gr.Tab("Profile Cards"):
            gr.Markdown("### Per-model multi-signal profile (failure rates, behavioral, flaw hunter, subjective, ELO)")
            with gr.Row():
                model_picker = gr.Dropdown(
                    choices=model_list(),
                    label="Pick a model",
                    value=(model_list()[0] if model_list() else None),
                )
            card_view = gr.Markdown()
            model_picker.change(profile_card, inputs=model_picker, outputs=card_view)
            # Initialize
            if model_list():
                card_view.value = profile_card(model_list()[0])

    gr.Markdown(
        """
---
**Methodology limitations** documented in the [experiment design doc](https://github.com/LeviTheWeasel/rp-benchmark/blob/main/docs/EXPERIMENT_DESIGN.md). The benchmark is calibrated against ~12 chats by ~5 RP users plus 338 community arena voters. Findings reflect the taste distribution of those participants, not "universal RP quality." For decisions, see the [pick-a-model decision tree](https://github.com/LeviTheWeasel/rp-benchmark/blob/main/results/pick_a_model.md).
"""
    )


if __name__ == "__main__":
    demo.launch()
