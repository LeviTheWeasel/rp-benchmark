"""Visualizations for RP-Bench leaderboard data."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns

from .config import RESULTS_DIR
from .aggregate import DIMENSION_NAMES, TIER_LABELS

# RP-Bench color palette
PALETTE = {
    "bg": "#0d1117",
    "card": "#161b22",
    "border": "#30363d",
    "text": "#e6edf3",
    "text_dim": "#8b949e",
    "accent": "#58a6ff",
    "tier1": "#3fb950",   # green - fundamentals
    "tier2": "#d29922",   # amber - quality control
    "tier3": "#bc8cff",   # purple - genre craft
    "overall": "#58a6ff", # blue
    "good": "#3fb950",
    "mid": "#d29922",
    "bad": "#f85149",
}

MODEL_COLORS = [
    "#58a6ff", "#bc8cff", "#3fb950", "#d29922",
    "#f85149", "#79c0ff", "#d2a8ff", "#56d364",
]


def _setup_style():
    """Apply dark theme."""
    sns.set_theme(style="dark", rc={
        "figure.facecolor": PALETTE["bg"],
        "axes.facecolor": PALETTE["card"],
        "axes.edgecolor": PALETTE["border"],
        "axes.labelcolor": PALETTE["text"],
        "text.color": PALETTE["text"],
        "xtick.color": PALETTE["text_dim"],
        "ytick.color": PALETTE["text_dim"],
        "grid.color": PALETTE["border"],
        "legend.facecolor": PALETTE["card"],
        "legend.edgecolor": PALETTE["border"],
        "font.family": "monospace",
    })


def _score_color(score: float) -> str:
    """Return color based on score value."""
    if score >= 4.0:
        return PALETTE["good"]
    elif score >= 3.0:
        return PALETTE["mid"]
    return PALETTE["bad"]


def _competitive_models(agg: dict) -> dict:
    """Return only competitive model stats (exclude reference data)."""
    return {
        m: s for m, s in agg.get("models", {}).items()
        if not s.get("is_reference")
    }


def plot_overall(agg: dict, save_path: Path | None = None):
    """Horizontal bar chart of overall rankings."""
    _setup_style()
    lb = agg["leaderboard"]  # already excludes reference data
    if not lb:
        return

    models = [e["model"] for e in reversed(lb)]
    scores = [e["overall"] or 0 for e in reversed(lb)]
    colors = [MODEL_COLORS[i % len(MODEL_COLORS)] for i in range(len(models))]
    colors.reverse()

    fig, ax = plt.subplots(figsize=(10, max(3, len(models) * 0.8 + 1.5)))

    bars = ax.barh(models, scores, color=colors, height=0.6, edgecolor=PALETTE["border"], linewidth=0.5)

    # Score labels on bars
    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_width() - 0.15, bar.get_y() + bar.get_height() / 2,
            "%.2f" % score, va="center", ha="right",
            fontsize=12, fontweight="bold", color=PALETTE["bg"],
        )

    ax.set_xlim(0, 5)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.set_xlabel("Score (1-5)")
    ax.set_title("RP-Bench Overall Ranking", fontsize=16, fontweight="bold", pad=15)

    # Rating zones
    for threshold, label, alpha in [(4.5, "Exceptional", 0.06), (3.5, "Strong", 0.04), (2.5, "Adequate", 0.03)]:
        ax.axvline(x=threshold, color=PALETTE["text_dim"], linestyle="--", linewidth=0.5, alpha=0.5)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print("Saved: %s" % save_path)
    return fig


def plot_tier_comparison(agg: dict, save_path: Path | None = None):
    """Grouped bar chart comparing models across tiers."""
    _setup_style()
    lb = agg["leaderboard"]
    if not lb:
        return

    models = [e["model"] for e in lb]
    tier_data = {
        "Fundamentals": [e.get("tier1") or 0 for e in lb],
        "Quality Control": [e.get("tier2") or 0 for e in lb],
        "Genre Craft": [e.get("tier3") or 0 for e in lb],
    }
    tier_colors = [PALETTE["tier1"], PALETTE["tier2"], PALETTE["tier3"]]

    x = np.arange(len(models))
    width = 0.25

    fig, ax = plt.subplots(figsize=(max(8, len(models) * 2.5), 6))

    for i, (tier_name, scores) in enumerate(tier_data.items()):
        offset = (i - 1) * width
        bars = ax.bar(
            x + offset, scores, width, label=tier_name,
            color=tier_colors[i], edgecolor=PALETTE["border"], linewidth=0.5,
        )
        for bar, score in zip(bars, scores):
            if score > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                    "%.1f" % score, ha="center", va="bottom",
                    fontsize=9, color=tier_colors[i], fontweight="bold",
                )

    ax.set_ylim(0, 5.5)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.set_ylabel("Score (1-5)")
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=11)
    ax.legend(loc="upper right", fontsize=10)
    ax.set_title("RP-Bench Tier Comparison", fontsize=16, fontweight="bold", pad=15)

    ax.axhline(y=3.5, color=PALETTE["text_dim"], linestyle="--", linewidth=0.5, alpha=0.4)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print("Saved: %s" % save_path)
    return fig


def plot_dimension_heatmap(agg: dict, save_path: Path | None = None):
    """Heatmap of all models x all dimensions."""
    _setup_style()
    model_stats = _competitive_models(agg)
    if not model_stats:
        return

    models = sorted(model_stats.keys())

    # Collect all dimensions that have data
    all_dims = set()
    for stats in model_stats.values():
        all_dims.update(stats["dimensions"].keys())
    dims = sorted(all_dims)

    # Build matrix
    matrix = []
    dim_labels = []
    for dim in dims:
        row = []
        for model in models:
            score = model_stats[model]["dimensions"].get(dim, {}).get("mean")
            row.append(score if score is not None else np.nan)
        matrix.append(row)
        dim_labels.append(DIMENSION_NAMES.get(dim, dim))

    matrix = np.array(matrix)

    fig, ax = plt.subplots(figsize=(max(8, len(models) * 2.5), max(8, len(dims) * 0.45)))

    # Custom colormap: red -> yellow -> green
    cmap = sns.diverging_palette(10, 135, s=80, l=55, n=256, as_cmap=True)

    sns.heatmap(
        matrix, ax=ax,
        xticklabels=models, yticklabels=dim_labels,
        annot=True, fmt=".1f", annot_kws={"size": 9},
        cmap=cmap, center=3.0, vmin=1, vmax=5,
        linewidths=0.5, linecolor=PALETTE["border"],
        cbar_kws={"label": "Score (1-5)", "shrink": 0.6},
        mask=np.isnan(matrix),
    )

    ax.set_title("RP-Bench Dimension Heatmap", fontsize=16, fontweight="bold", pad=15)
    ax.tick_params(axis="x", labelsize=11, rotation=0)
    ax.tick_params(axis="y", labelsize=9)

    # Color dimension labels by tier
    for i, label in enumerate(ax.get_yticklabels()):
        dim = dims[i]
        if dim.startswith("1."):
            label.set_color(PALETTE["tier1"])
        elif dim.startswith("2."):
            label.set_color(PALETTE["tier2"])
        elif dim.startswith("3."):
            label.set_color(PALETTE["tier3"])

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print("Saved: %s" % save_path)
    return fig


def plot_radar(agg: dict, save_path: Path | None = None):
    """Radar/spider chart comparing models on tier-level scores."""
    _setup_style()
    lb = agg["leaderboard"]
    if not lb:
        return

    categories = ["Fundamentals", "Quality Control", "Genre Craft"]
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # close the polygon

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.set_facecolor(PALETTE["card"])
    fig.patch.set_facecolor(PALETTE["bg"])

    for i, entry in enumerate(lb):
        values = [
            entry.get("tier1") or 0,
            entry.get("tier2") or 0,
            entry.get("tier3") or 0,
        ]
        values += values[:1]

        color = MODEL_COLORS[i % len(MODEL_COLORS)]
        ax.plot(angles, values, "o-", linewidth=2, color=color, label=entry["model"])
        ax.fill(angles, values, alpha=0.1, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=12, color=PALETTE["text"])
    ax.set_ylim(0, 5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=8, color=PALETTE["text_dim"])
    ax.yaxis.grid(True, color=PALETTE["border"], linewidth=0.5)
    ax.xaxis.grid(True, color=PALETTE["border"], linewidth=0.5)
    ax.spines["polar"].set_color(PALETTE["border"])

    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=10)
    ax.set_title("RP-Bench Tier Radar", fontsize=16, fontweight="bold", pad=20, color=PALETTE["text"])

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print("Saved: %s" % save_path)
    return fig


def plot_dimension_bars(agg: dict, tier: str = "1", save_path: Path | None = None):
    """Grouped horizontal bar chart for dimensions within a single tier."""
    _setup_style()
    model_stats = _competitive_models(agg)
    if not model_stats:
        return

    models = sorted(model_stats.keys())
    tier_color = {"1": PALETTE["tier1"], "2": PALETTE["tier2"], "3": PALETTE["tier3"]}

    # Get dimensions for this tier
    all_dims = set()
    for stats in model_stats.values():
        for dim in stats["dimensions"]:
            if dim.startswith(tier + "."):
                all_dims.add(dim)
    dims = sorted(all_dims)

    if not dims:
        return

    dim_labels = [DIMENSION_NAMES.get(d, d) for d in dims]
    y = np.arange(len(dims))
    height = 0.8 / len(models)

    fig, ax = plt.subplots(figsize=(10, max(4, len(dims) * 0.7 + 1.5)))

    for i, model in enumerate(models):
        scores = []
        for dim in dims:
            s = model_stats[model]["dimensions"].get(dim, {}).get("mean", 0)
            scores.append(s)

        offset = (i - len(models) / 2 + 0.5) * height
        color = MODEL_COLORS[i % len(MODEL_COLORS)]
        bars = ax.barh(
            y + offset, scores, height, label=model,
            color=color, edgecolor=PALETTE["border"], linewidth=0.5, alpha=0.85,
        )

        for bar, score in zip(bars, scores):
            if score > 0:
                ax.text(
                    bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                    "%.1f" % score, va="center", ha="left",
                    fontsize=8, color=color,
                )

    ax.set_xlim(0, 5.5)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.set_xlabel("Score (1-5)")
    ax.set_yticks(y)
    ax.set_yticklabels(dim_labels, fontsize=10)
    ax.legend(loc="lower right", fontsize=9)
    tier_label = TIER_LABELS.get(tier, "Tier %s" % tier)
    ax.set_title("RP-Bench: %s Dimensions" % tier_label, fontsize=14, fontweight="bold", pad=15)

    ax.axvline(x=3.5, color=PALETTE["text_dim"], linestyle="--", linewidth=0.5, alpha=0.4)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print("Saved: %s" % save_path)
    return fig


def plot_judge_agreement(agg: dict, save_path: Path | None = None):
    """Scatter plot showing inter-judge agreement per model."""
    _setup_style()
    model_stats = _competitive_models(agg)

    # Find models with multiple judges
    multi_judge = {}
    for model, stats in model_stats.items():
        jo = stats.get("judge_overalls", {})
        if len(jo) >= 2:
            multi_judge[model] = jo

    if not multi_judge:
        return

    judges = sorted({j for jo in multi_judge.values() for j in jo})
    if len(judges) < 2:
        return

    fig, ax = plt.subplots(figsize=(7, 7))

    j1, j2 = judges[0], judges[1]
    for i, (model, jo) in enumerate(multi_judge.items()):
        if j1 in jo and j2 in jo:
            color = MODEL_COLORS[i % len(MODEL_COLORS)]
            ax.scatter(jo[j1], jo[j2], s=120, color=color, edgecolor="white", linewidth=0.5, zorder=3)
            ax.annotate(
                model, (jo[j1], jo[j2]),
                textcoords="offset points", xytext=(8, 8),
                fontsize=10, color=color,
            )

    # Perfect agreement line
    ax.plot([1, 5], [1, 5], "--", color=PALETTE["text_dim"], linewidth=0.5, alpha=0.5)

    ax.set_xlim(1, 5)
    ax.set_ylim(1, 5)
    ax.set_xlabel(j1, fontsize=12)
    ax.set_ylabel(j2, fontsize=12)
    ax.set_aspect("equal")
    ax.set_title("Inter-Judge Agreement", fontsize=14, fontweight="bold", pad=15)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print("Saved: %s" % save_path)
    return fig


def generate_all(agg: dict, output_dir: Path | None = None):
    """Generate all visualization charts and save to output directory."""
    if output_dir is None:
        output_dir = RESULTS_DIR / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating charts in %s..." % output_dir)

    plot_overall(agg, output_dir / "01_overall_ranking.png")
    plot_tier_comparison(agg, output_dir / "02_tier_comparison.png")
    plot_radar(agg, output_dir / "03_tier_radar.png")
    plot_dimension_heatmap(agg, output_dir / "04_dimension_heatmap.png")

    for tier in ["1", "2", "3"]:
        tier_label = TIER_LABELS.get(tier, tier).lower().replace(" ", "_")
        plot_dimension_bars(agg, tier=tier, save_path=output_dir / ("05_%s_dimensions.png" % tier_label))

    plot_judge_agreement(agg, output_dir / "06_judge_agreement.png")

    plt.close("all")
    print("Done. %d charts generated." % len(list(output_dir.glob("*.png"))))
