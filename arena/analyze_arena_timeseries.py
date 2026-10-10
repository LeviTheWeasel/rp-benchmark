#!/usr/bin/env python3
"""Time-series chart of community arena rankings across snapshots.

Reads the saved snapshots (community_arena_1000.json, _1600.json,
_2000.json) and produces a markdown rank-evolution table per model.

The table answers: "did each model's rank stabilize quickly, or did
it keep moving as more votes arrived?"

Output: results/arena_timeseries.md (markdown table).
"""
import json
from pathlib import Path

SNAPSHOTS = [
    ("results/community_arena_1000.json", "@1k"),
    ("results/community_arena_1600.json", "@1.6k"),
    ("results/community_arena_2000.json", "@2k"),
]


def main():
    series = []  # list of (label, dict[model -> (rank, elo)])
    for path, label in SNAPSHOTS:
        if not Path(path).exists():
            continue
        d = json.load(open(path))
        snap = {}
        for e in d["leaderboard"]:
            snap[e["model"]] = (e["rank"], e["elo"])
        series.append((label, snap))

    if not series:
        print("No snapshots found.")
        return

    all_models = sorted({m for _, s in series for m in s})

    # Rank-evolution table
    lines = []
    lines.append("# Community arena rank evolution\n")
    lines.append(f"Across {len(series)} snapshots: {', '.join(l for l, _ in series)}\n")
    lines.append("")

    # Markdown table
    header = ["Model"]
    for label, _ in series:
        header.append(f"Rank {label}")
        header.append(f"ELO {label}")
    header.append("Δrank")
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")

    rows = []
    for m in all_models:
        cells = [m]
        first_rank = None
        last_rank = None
        for _, snap in series:
            rank, elo = snap.get(m, (None, None))
            if rank is not None:
                if first_rank is None:
                    first_rank = rank
                last_rank = rank
            cells.append(str(rank) if rank else "—")
            cells.append(f"{elo:.0f}" if elo else "—")
        delta = (last_rank - first_rank) if (first_rank and last_rank) else None
        if delta is None:
            d_str = "—"
        elif delta == 0:
            d_str = "0"
        else:
            d_str = f"{'+' if delta > 0 else ''}{delta}"
        cells.append(d_str)
        rows.append((m, last_rank or 99, cells, delta))

    rows.sort(key=lambda r: r[1])
    for _, _, cells, _ in rows:
        lines.append("| " + " | ".join(cells) + " |")

    lines.append("")
    lines.append("Δrank = (rank in latest snapshot) − (rank in first snapshot). Negative = moved up. Positive = moved down.")
    lines.append("")

    # ASCII rank-evolution sparkline
    lines.append("## Rank trajectory (visual)\n")
    lines.append("```")
    for m, _, _, delta in rows:
        spark = []
        for _, snap in series:
            r = snap.get(m, (None, None))[0]
            spark.append(f"{r:>2}" if r else " —")
        spark_str = " → ".join(spark)
        marker = ""
        if delta is not None:
            if delta < 0:
                marker = f"  ↑ ({abs(delta)} up)"
            elif delta > 0:
                marker = f"  ↓ ({delta} down)"
            else:
                marker = "  = (stable)"
        lines.append(f"  {m:<28} {spark_str}{marker}")
    lines.append("```")
    lines.append("")

    # Stable vs volatile
    lines.append("## Stability summary\n")
    stable = [m for m, _, _, d in rows if d is not None and d == 0]
    moved_up = [(m, d) for m, _, _, d in rows if d is not None and d < 0]
    moved_down = [(m, d) for m, _, _, d in rows if d is not None and d > 0]
    lines.append(f"- **Stable** ({len(stable)}): {', '.join(stable)}")
    lines.append(f"- **Climbed** ({len(moved_up)}): " +
                 ", ".join(f"{m} ({d:+d})" for m, d in sorted(moved_up, key=lambda x: x[1])))
    lines.append(f"- **Dropped** ({len(moved_down)}): " +
                 ", ".join(f"{m} ({d:+d})" for m, d in sorted(moved_down, key=lambda x: -x[1])))

    out_path = Path("results/arena_timeseries.md")
    out_path.write_text("\n".join(lines))
    print(f"Saved: {out_path}")
    print()
    print("\n".join(lines))


if __name__ == "__main__":
    main()
