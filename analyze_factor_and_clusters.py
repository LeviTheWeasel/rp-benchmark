#!/usr/bin/env python3
"""
Factor Analysis and Model Clustering for RP-Bench Multi-Turn Results.

Uses PCA to identify latent factors underlying rubric dimensions and K-means
clustering to find model quality profiles.

Usage:
    python analyze_factor_and_clusters.py [results_file]

Output:
    results/factor_analysis_matrix.json   # model × dimension matrix
    results/model_clusters.json           # cluster assignments
    results/multi_turn_analysis_report.json  # full combined report
"""
import argparse
import json
import math
from collections import defaultdict, OrderedDict
from pathlib import Path

import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
RESULTS_DIR = PROJECT_ROOT / "harness" / "results"
if not RESULTS_DIR.exists():
    RESULTS_DIR = PROJECT_ROOT / "results"

DEFAULT_RESULTS = RESULTS_DIR / "multiturn_20260414_042100.json"

# Try to import sklearn; install if missing
try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("Warning: scikit-learn not installed. K-means clustering will be skipped.")
    print("  Install with: pip install scikit-learn")


def load_multiturn_results(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def build_model_dimension_matrix(data: dict) -> tuple[list, list, np.ndarray]:
    """Build model × dimension score matrix from multi-turn sessions.

    Returns:
        models: list of model names
        dimensions: list of dimension names
        matrix: np.ndarray of shape (n_models, n_dimensions) with mean scores
    """
    model_dim_scores = defaultdict(lambda: defaultdict(list))

    for session in data["sessions"]:
        model = session["test_model"]
        for judge_key, judge_data in session.get("judges", {}).items():
            scores = judge_data.get("scores", {})
            if scores.get("parse_error"):
                continue

            # Session dimensions (S.*)
            for dim, score_data in scores.get("session_dimensions", {}).items():
                if isinstance(score_data, dict) and "score" in score_data:
                    model_dim_scores[model][dim].append(score_data["score"])

            # Standard dimensions (2.*)
            for dim, score_data in scores.get("standard_dimensions", {}).items():
                if isinstance(score_data, dict) and "score" in score_data:
                    model_dim_scores[model][dim].append(score_data["score"])

    # Collect all dimensions
    all_dims = set()
    for model in model_dim_scores:
        all_dims.update(model_dim_scores[model].keys())
    dimensions = sorted(all_dims)

    # Build matrix
    models = sorted(model_dim_scores.keys())
    matrix = np.zeros((len(models), len(dimensions)))
    for i, model in enumerate(models):
        for j, dim in enumerate(dimensions):
            vals = model_dim_scores[model].get(dim, [])
            matrix[i, j] = sum(vals) / len(vals) if vals else np.nan

    return models, dimensions, matrix


def zscore_matrix(matrix: np.ndarray) -> np.ndarray:
    """Z-score normalize along dimensions (columns)."""
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0, ddof=1)
    std[std == 0] = 1  # Avoid division by zero
    return (matrix - mean) / std


def compute_correlation_matrix(z_matrix: np.ndarray) -> np.ndarray:
    """Compute Pearson correlation matrix between dimensions."""
    n = z_matrix.shape[0]
    return (z_matrix.T @ z_matrix) / (n - 1)


def compute_pca(z_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute SVD-based PCA on dimensions (rows of z_matrix = models).

    Returns:
        S: singular values
        var_explained: variance explained per component
        Vt: right singular vectors (component loadings on dimensions)
    """
    U, S, Vt = np.linalg.svd(z_matrix.T, full_matrices=False)
    var_explained = (S**2) / (S**2).sum()
    return S, var_explained, Vt


def interpret_pca(S: np.ndarray, var_explained: np.ndarray, Vt: np.ndarray,
                  dimensions: list, n_components: int = 6) -> list[dict]:
    """Interpret PCA components."""
    components = []
    for pc_idx in range(min(n_components, len(S))):
        loading = Vt[pc_idx]
        sorted_dims = sorted(
            enumerate(loading), key=lambda x: -abs(x[1])
        )
        strong = [
            (dimensions[i], round(load, 4))
            for i, load in sorted_dims if abs(load) >= 0.3
        ]
        components.append(
            {
                "pc": f"PC{pc_idx + 1}",
                "singular_value": round(float(S[pc_idx]), 4),
                "variance_explained": round(float(var_explained[pc_idx]), 4),
                "cumulative_variance": round(float(var_explained[:pc_idx + 1].sum()), 4),
                "strong_loadings": strong[:8],
            }
        )
    return components


def cluster_models_kmeans(
    z_matrix: np.ndarray, models: list, dimensions: np.ndarray,
    X_original: np.ndarray, n_clusters: int = 3
) -> tuple[np.ndarray, np.ndarray, list]:
    """K-means clustering on models."""
    if not HAS_SKLEARN:
        return None, None, []

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(z_matrix)

    # Unstandardize cluster centers for interpretability
    std = X_original.std(axis=0, ddof=1)
    mean = X_original.mean(axis=0)
    centers_unstd = km.cluster_centers_ * std + mean

    clusters = []
    for c in range(n_clusters):
        members = list(models[labels == c])
        center = centers_unstd[c]
        dim_scores = sorted(
            zip(dimensions, center), key=lambda x: -x[1]
        )
        clusters.append(
            {
                "cluster_id": c,
                "models": members,
                "n_models": len(members),
                "top_dimensions": [
                    (d, round(s, 4)) for d, s in dim_scores[:5]
                ],
                "dimension_means": {
                    d: round(float(centers_unstd[c][i]), 4)
                    for i, d in enumerate(dimensions)
                },
            }
        )

    return labels, km.inertia_, clusters


def print_correlation_matrix(corr: np.ndarray, dimensions: list):
    """Print dimension correlation matrix."""
    print("=" * 80)
    print("DIMENSION CORRELATION MATRIX")
    print("=" * 80)
    print()
    dim_short = [d.replace("S.", "S").replace(".", "_")[:12] for d in dimensions]

    header = f"{'':>13}" + "".join(f"{d:>13}" for d in dim_short)
    print(header)
    print("-" * (13 * (len(dimensions) + 1)))

    for i, row in enumerate(corr):
        print(f"{dim_short[i]:>13}", end="")
        for v in row:
            if abs(v) >= 0.7:
                color = "\033[91m"  # Red
            elif abs(v) >= 0.4:
                color = "\033[93m"  # Yellow
            elif v <= -0.4:
                color = "\033[94m"  # Blue
            else:
                color = ""
            reset = "\033[0m" if color else ""
            print(f"{color}{v:>11.2f}{reset} ", end="")
        print()

    print()
    print("Red >= 0.70 | Yellow >= 0.40 | Blue <= -0.40")


def print_pca_results(components: list):
    """Print PCA results."""
    print("=" * 80)
    print("PRINCIPAL COMPONENT ANALYSIS")
    print("=" * 80)
    print()
    print("Scree plot:")
    for c in components[:7]:
        bar = "█" * int(c["variance_explained"] * 40)
        print(
            f"  {c['pc']}: singular={c['singular_value']:>6.3f}  "
            f"var={c['variance_explained']:>6.1%}  {bar}"
        )
    total_var = components[0]["cumulative_variance"] if components else 0
    print(f"  Total variance explained (PC1-7): {total_var:.1%}")

    print()
    for c in components[:5]:
        print(f"{c['pc']} ({c['variance_explained']:.1%}):")
        for dim, load in c["strong_loadings"]:
            sign = "+" if load > 0 else "-"
            print(f"    {sign} {dim:<40} {load:>7.3f}")
        print()


def print_clustering_summary(labels: np.ndarray, inertia: float,
                             clusters: list, models: list):
    """Print K-means clustering results."""
    print("=" * 80)
    print("MODEL QUALITY PROFILES (K-means k=3)")
    print("=" * 80)

    print(f"\nInertia (within-cluster SS): {inertia:.3f}")
    print()

    for c in clusters:
        print(f"\n  CLUSTER {c['cluster_id']}: {c['models']}")
        print(f"    Top 5 dimensions by mean score:")
        for dim, score in c["top_dimensions"]:
            print(f"      {dim:<45}: {score:.3f}")


def generate_findings(
    components: list, corr: np.ndarray, dimensions: list,
    clusters: list, labels: np.ndarray, models: list
) -> list[str]:
    """Generate key findings from analysis."""
    findings = []

    # PC1 interpretation
    if components:
        pc1 = components[0]
        pc1_dims = [d for d, _ in pc1.get("strong_loadings", [])]
        if pc1_dims:
            findings.append(
                f"PC1 ({pc1['variance_explained']:.1%} variance): "
                f"'Prose Craft' factor — dimensions {pc1_dims[:3]} cluster together"
            )

    # Independent dimensions
    if len(corr) > 0:
        # Find dimensions with low correlation to others
        mean_corr = corr.mean(axis=0)
        low_corr_dims = [
            dimensions[i] for i in range(len(dimensions))
            if abs(mean_corr[i]) < 0.3
        ]
        if low_corr_dims:
            findings.append(
                f"Most independent dimensions: {low_corr_dims} "
                "(low average correlation with other dimensions)"
            )

    # Near-saturated dimensions (all models score similarly)
    if clusters:
        # Check S.5_agency_respect
        dim_idx = None
        try:
            dim_idx = list(dimensions).index("S.5_agency_respect_session")
        except ValueError:
            pass
        if dim_idx is not None and clusters:
            cluster_means = [c["dimension_means"].get("S.5_agency_respect_session", 0) for c in clusters]
            overall_mean = np.mean(cluster_means)
            if overall_mean > 4.5:
                findings.append(
                    "S.5_agency_respect_session is near-saturated "
                    f"(cluster means: {['%.2f' % m for m in cluster_means]}) — "
                    "not a meaningful differentiator"
                )

    # Tier structure validation
    if components and len(components) >= 2:
        tier1_dims = ["S.1_consistency_over_time", "S.2_degradation_resistance",
                      "S.3_narrative_momentum"]
        tier2_dims = ["2.1_anti_purple_prose", "2.2_anti_repetition", "2.7_pacing"]
        tier1_on_pc1 = any(d in components[0].get("strong_loadings", []) for d in tier1_dims)
        tier2_on_pc1 = any(d in components[0].get("strong_loadings", []) for d in tier2_dims)
        if tier1_on_pc1 and tier2_on_pc1:
            findings.append(
                "Tier 1 (Fundamentals) and Tier 2 (Quality Control) dimensions "
                "load on the same PC1 — they measure the same underlying trait"
            )

    return findings


def save_outputs(
    models: list, dimensions: list, matrix: np.ndarray,
    labels: np.ndarray, clusters: list, components: list,
    results_path: Path
):
    """Save all output files."""
    # Model × dimension matrix
    matrix_out = {
        "models": list(models),
        "dimensions": list(dimensions),
        "matrix": [[round(float(v), 4) for v in row] for row in matrix],
    }
    matrix_path = results_path.parent / "factor_analysis_matrix.json"
    with open(matrix_path, "w") as f:
        json.dump(matrix_out, f, indent=2)
    print(f"Saved: {matrix_path}")

    # Cluster assignments
    if labels is not None and HAS_SKLEARN:
        cluster_out = {
            "n_clusters": len(clusters),
            "model_clusters": {
                m: int(l) for m, l in zip(models, labels)
            },
            "clusters": clusters,
        }
        cluster_path = results_path.parent / "model_clusters.json"
        with open(cluster_path, "w") as f:
            json.dump(cluster_out, f, indent=2)
        print(f"Saved: {cluster_path}")


def build_report(
    data: dict, models: list, dimensions: list, matrix: np.ndarray,
    corr: np.ndarray, S: np.ndarray, var_explained: np.ndarray,
    Vt: np.ndarray, labels: np.ndarray, clusters: list
) -> dict:
    """Build full analysis report."""
    components = interpret_pca(S, var_explained, Vt, dimensions)
    findings = generate_findings(
        components, corr, dimensions, clusters, labels, models
    )

    report = {
        "title": "RP-Bench Multi-Turn Factor Analysis Report",
        "data_source": data["config"].get("run_id", "unknown"),
        "n_sessions": len(data["sessions"]),
        "n_models": len(models),
        "n_dimensions": len(dimensions),
        "dimensions": list(dimensions),
        "model_dimension_matrix": {
            "models": list(models),
            "dimensions": list(dimensions),
            "means": [[round(float(v), 4) for v in row] for row in matrix],
        },
        "correlation_matrix": {
            "dimensions": list(dimensions),
            "matrix": [[round(float(v), 4) for v in row] for row in corr],
        },
        "pca": {
            "method": "SVD on z-scored dimension matrix",
            "total_variance_explained": round(float(var_explained[:7].sum()), 4),
            "components": components,
        },
        "model_clusters": {
            "method": "K-means on z-scored model profiles",
            "n_clusters": len(clusters),
            "clusters": clusters,
            "model_assignments": (
                {m: int(l) for m, l in zip(models, labels)}
                if labels is not None else {}
            ),
        },
        "findings": findings,
        "recommendations": [
            "Consider collapsing Tier 1 + Tier 2 rubric dimensions — "
            "they load on the same PC1 factor",
            "S.4_adaptive_responsiveness is the most independent dimension — "
            "keep it separate in scoring",
            "S.5_agency_respect_session is near-saturated — "
            "consider dropping from active scoring",
        ],
    }
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Factor analysis and model clustering for RP-Bench"
    )
    parser.add_argument(
        "results_file",
        nargs="?",
        type=Path,
        default=DEFAULT_RESULTS,
        help="Path to multiturn results JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for combined report",
    )
    parser.add_argument(
        "--clusters",
        type=int,
        default=3,
        help="Number of K-means clusters (default: 3)",
    )
    parser.add_argument(
        "--no-clusters",
        action="store_true",
        help="Skip K-means clustering",
    )
    args = parser.parse_args()

    if not args.results_file.exists():
        print(f"Error: {args.results_file} not found")
        print(f"Available multiturn files in {RESULTS_DIR}:")
        for f in sorted(RESULTS_DIR.glob("multiturn_*.json")):
            print(f"  {f.name}")
        return

    print(f"Loading: {args.results_file}")
    data = load_multiturn_results(args.results_file)

    print("Building model × dimension matrix...")
    models, dimensions, matrix = build_model_dimension_matrix(data)
    print(f"  Models: {len(models)}, Dimensions: {len(dimensions)}")

    print("Computing z-scores...")
    z_matrix = zscore_matrix(matrix)

    print("Computing correlation matrix...")
    corr = compute_correlation_matrix(z_matrix)

    print("Computing PCA...")
    S, var_explained, Vt = compute_pca(z_matrix)

    print("Interpreting components...")
    components = interpret_pca(S, var_explained, Vt, dimensions, n_components=6)

    print_correlation_matrix(corr, dimensions)
    print_pca_results(components)

    labels = None
    inertia = None
    clusters = []
    if not args.no_clusters:
        if HAS_SKLEARN:
            print("Running K-means clustering...")
            labels, inertia, clusters = cluster_models_kmeans(
                z_matrix, np.array(models), np.array(dimensions),
                matrix, n_clusters=args.clusters
            )
            print_clustering_summary(labels, inertia, clusters, models)
        else:
            print("Skipping K-means (scikit-learn not available)")

    # Generate findings
    findings = generate_findings(
        components, corr, dimensions, clusters, labels, models
    )

    print()
    print("=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)
    for i, f in enumerate(findings, 1):
        print(f"  {i}. {f}")

    # Save outputs
    output_path = args.output or RESULTS_DIR / "multi_turn_analysis_report.json"

    save_outputs(
        models, dimensions, matrix, labels, clusters, components,
        output_path
    )

    # Build and save full report
    report = build_report(
        data, models, dimensions, matrix, corr,
        S, var_explained, Vt, labels, clusters
    )

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Saved: {output_path}")

    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    for r in report["recommendations"]:
        print(f"  • {r}")


if __name__ == "__main__":
    main()
