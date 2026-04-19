"use client";

import { useState, useEffect } from "react";
import { getServerVotes, exportVotes } from "@/lib/votes";
import { Vote, RUBRIC_DIMENSIONS } from "@/lib/types";

export default function ResultsPage() {
  const [votes, setVotes] = useState<Vote[]>([]);
  const [stats, setStats] = useState({ total: 0, arena: 0, rubric: 0, multiturn: 0 });

  useEffect(() => {
    getServerVotes().then((v) => {
      setVotes(v);
      const arena = v.filter((x) => x.mode === "arena").length;
      const rubric = v.filter((x) => x.mode === "rubric").length;
      const multiturn = v.filter((x) => x.mode === "multiturn_arena").length;
      setStats({ total: v.length, arena, rubric, multiturn });
    });
  }, []);

  // Arena win rates
  const arenaVotes = votes.filter((v) => v.mode === "arena");

  // Coverage: per-pair vote count across all arena votes we can see.
  // Excludes catch pairs since they're for voter-quality, not model ranking.
  const coverageCounts: Record<string, number> = {};
  for (const v of arenaVotes) {
    if (v.is_catch) continue;
    coverageCounts[v.scenario_id] = (coverageCounts[v.scenario_id] ?? 0) + 1;
  }
  const coverageValues = Object.values(coverageCounts);
  const coverageSorted = [...coverageValues].sort((a, b) => a - b);
  const coverage = {
    uniquePairs: Object.keys(coverageCounts).length,
    min: coverageSorted[0] ?? 0,
    median: coverageSorted.length
      ? coverageSorted[Math.floor(coverageSorted.length / 2)]
      : 0,
    max: coverageSorted[coverageSorted.length - 1] ?? 0,
    zeroCount: 0, // set below once total scenario count is known (not tracked here)
  };
  // Histogram buckets
  const buckets = [0, 1, 2, 3, 5, 10] as const;
  const histogram = buckets.map((b, i) => {
    const upper = buckets[i + 1];
    const label = upper === undefined ? `${b}+` : `${b}-${upper - 1}`;
    const count = coverageValues.filter(
      (v) => v >= b && (upper === undefined || v < upper)
    ).length;
    return { label, count };
  });
  // Least-voted leaderboard (bottom 10)
  const leastVoted = Object.entries(coverageCounts)
    .sort((a, b) => a[1] - b[1])
    .slice(0, 10);

  const modelWins: Record<string, { wins: number; losses: number; ties: number }> = {};
  for (const v of arenaVotes) {
    const models = [v.model_a!, v.model_b!];
    for (const m of models) {
      if (!modelWins[m]) modelWins[m] = { wins: 0, losses: 0, ties: 0 };
    }
    if (v.winner === "tie") {
      modelWins[v.model_a!].ties++;
      modelWins[v.model_b!].ties++;
    } else {
      const winnerModel = v.winner === "A" ? v.model_a! : v.model_b!;
      const loserModel = v.winner === "A" ? v.model_b! : v.model_a!;
      modelWins[winnerModel].wins++;
      modelWins[loserModel].losses++;
    }
  }

  // Multi-turn arena
  const multiturnVotes = votes.filter((v) => v.mode === "multiturn_arena");
  const mtCoverageCounts: Record<string, number> = {};
  for (const v of multiturnVotes) {
    mtCoverageCounts[v.scenario_id] = (mtCoverageCounts[v.scenario_id] ?? 0) + 1;
  }
  const mtCoverageValues = Object.values(mtCoverageCounts);
  const mtCoverageSorted = [...mtCoverageValues].sort((a, b) => a - b);
  const mtCoverage = {
    uniquePairs: Object.keys(mtCoverageCounts).length,
    min: mtCoverageSorted[0] ?? 0,
    median: mtCoverageSorted.length
      ? mtCoverageSorted[Math.floor(mtCoverageSorted.length / 2)]
      : 0,
    max: mtCoverageSorted[mtCoverageSorted.length - 1] ?? 0,
  };

  const mtModelWins: Record<string, { wins: number; losses: number; ties: number }> = {};
  for (const v of multiturnVotes) {
    const models = [v.model_a!, v.model_b!];
    for (const m of models) {
      if (!mtModelWins[m]) mtModelWins[m] = { wins: 0, losses: 0, ties: 0 };
    }
    if (v.winner === "tie") {
      mtModelWins[v.model_a!].ties++;
      mtModelWins[v.model_b!].ties++;
    } else {
      const winnerModel = v.winner === "A" ? v.model_a! : v.model_b!;
      const loserModel = v.winner === "A" ? v.model_b! : v.model_a!;
      mtModelWins[winnerModel].wins++;
      mtModelWins[loserModel].losses++;
    }
  }

  // Rubric averages per model
  const rubricVotes = votes.filter((v) => v.mode === "rubric");
  const modelRubric: Record<string, Record<string, number[]>> = {};
  for (const v of rubricVotes) {
    const m = v.model!;
    if (!modelRubric[m]) modelRubric[m] = {};
    for (const [dim, score] of Object.entries(v.scores || {})) {
      if (!modelRubric[m][dim]) modelRubric[m][dim] = [];
      modelRubric[m][dim].push(score);
    }
  }

  const handleExport = () => {
    const data = exportVotes();
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rpbench_votes_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Results</h1>
          <p className="text-sm text-[var(--muted)]">
            {stats.total} votes ({stats.arena} arena, {stats.multiturn} multi-turn, {stats.rubric} rubric)
          </p>
        </div>
        <button
          onClick={handleExport}
          className="px-4 py-2 rounded-lg border border-[var(--border)] text-sm hover:border-[var(--accent)] transition"
        >
          Export JSON
        </button>
      </div>

      {stats.total === 0 ? (
        <div className="text-center py-16 text-[var(--muted)]">
          <p className="text-lg mb-2">No votes yet</p>
          <p className="text-sm">Head to the Arena or Rubric page to start rating.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Coverage — shows how evenly votes are spread across pairs */}
          {coverage.uniquePairs > 0 && (
            <div className="p-6 rounded-lg border border-[var(--border)] bg-[var(--card)]">
              <h2 className="text-lg font-semibold mb-1">Coverage</h2>
              <p className="text-xs text-[var(--muted)] mb-4">
                Arena votes spread across {coverage.uniquePairs} pairs. More even = tighter per-pair confidence. Catch/calibration pairs excluded.
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
                <div className="px-3 py-2 rounded border border-[var(--border)]">
                  <div className="text-xs text-[var(--muted)]">Min</div>
                  <div className="text-lg font-semibold">{coverage.min}</div>
                </div>
                <div className="px-3 py-2 rounded border border-[var(--border)]">
                  <div className="text-xs text-[var(--muted)]">Median</div>
                  <div className="text-lg font-semibold">{coverage.median}</div>
                </div>
                <div className="px-3 py-2 rounded border border-[var(--border)]">
                  <div className="text-xs text-[var(--muted)]">Max</div>
                  <div className="text-lg font-semibold">{coverage.max}</div>
                </div>
                <div className="px-3 py-2 rounded border border-[var(--border)]">
                  <div className="text-xs text-[var(--muted)]">Pairs covered</div>
                  <div className="text-lg font-semibold">{coverage.uniquePairs}</div>
                </div>
              </div>
              <div className="space-y-1 mb-5">
                <div className="text-xs uppercase tracking-wider text-[var(--muted)]">Votes per pair</div>
                {histogram.map((h) => {
                  const max = Math.max(1, ...histogram.map((x) => x.count));
                  const pct = (h.count / max) * 100;
                  return (
                    <div key={h.label} className="flex items-center gap-3 text-sm">
                      <span className="w-12 text-[var(--muted)] text-xs">{h.label}</span>
                      <div className="flex-1 h-4 bg-[var(--background)] rounded overflow-hidden">
                        <div
                          className="h-full bg-[var(--accent)]"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="w-10 text-xs text-[var(--muted)] text-right">{h.count}</span>
                    </div>
                  );
                })}
              </div>
              {leastVoted.length > 0 && (
                <div>
                  <div className="text-xs uppercase tracking-wider text-[var(--muted)] mb-2">
                    Least-voted pairs (help these out next)
                  </div>
                  <ul className="space-y-1 text-xs">
                    {leastVoted.map(([sid, count]) => (
                      <li key={sid} className="flex justify-between gap-4">
                        <span className="truncate font-mono text-[var(--muted)]">{sid}</span>
                        <span className="text-[var(--foreground)]">
                          {count} {count === 1 ? "vote" : "votes"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Arena results */}
          {Object.keys(modelWins).length > 0 && (
            <div className="p-6 rounded-lg border border-[var(--border)] bg-[var(--card)]">
              <h2 className="text-lg font-semibold text-[var(--accent)] mb-4">
                Arena Win Rates
              </h2>
              <div className="space-y-3">
                {Object.entries(modelWins)
                  .sort((a, b) => b[1].wins - a[1].wins)
                  .map(([model, record]) => {
                    const total = record.wins + record.losses + record.ties;
                    const winRate = total > 0 ? (record.wins / total) * 100 : 0;
                    return (
                      <div key={model} className="flex items-center gap-3">
                        <span className="text-sm w-48 truncate">{model}</span>
                        <div className="flex-1 h-6 bg-[var(--background)] rounded overflow-hidden">
                          <div
                            className="h-full rounded transition-all"
                            style={{
                              width: `${winRate}%`,
                              backgroundColor:
                                winRate >= 60
                                  ? "var(--green)"
                                  : winRate >= 40
                                    ? "var(--amber)"
                                    : "var(--red)",
                            }}
                          />
                        </div>
                        <span className="text-xs text-[var(--muted)] w-32 text-right">
                          {record.wins}W / {record.losses}L / {record.ties}T ({winRate.toFixed(0)}%)
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Multi-turn arena results */}
          {multiturnVotes.length > 0 && (
            <div className="p-6 rounded-lg border border-[var(--border)] bg-[var(--card)]">
              <h2 className="text-lg font-semibold text-[var(--accent)] mb-1">
                Multi-Turn Arena
              </h2>
              <p className="text-xs text-[var(--muted)] mb-4">
                Full 12-turn session comparisons. {multiturnVotes.length} votes across {mtCoverage.uniquePairs} pairs
                {mtCoverage.uniquePairs > 0 && (
                  <> (coverage: min {mtCoverage.min}, median {mtCoverage.median}, max {mtCoverage.max})</>
                )}.
              </p>
              <div className="space-y-3">
                {Object.entries(mtModelWins)
                  .sort((a, b) => {
                    const aTotal = a[1].wins + a[1].losses + a[1].ties;
                    const bTotal = b[1].wins + b[1].losses + b[1].ties;
                    const aWr = aTotal > 0 ? (a[1].wins + 0.5 * a[1].ties) / aTotal : 0;
                    const bWr = bTotal > 0 ? (b[1].wins + 0.5 * b[1].ties) / bTotal : 0;
                    return bWr - aWr;
                  })
                  .map(([model, record]) => {
                    const total = record.wins + record.losses + record.ties;
                    const winRate = total > 0 ? ((record.wins + 0.5 * record.ties) / total) * 100 : 0;
                    return (
                      <div key={model} className="flex items-center gap-3">
                        <span className="text-sm w-48 truncate">{model}</span>
                        <div className="flex-1 h-6 bg-[var(--background)] rounded overflow-hidden">
                          <div
                            className="h-full rounded transition-all"
                            style={{
                              width: `${winRate}%`,
                              backgroundColor:
                                winRate >= 60
                                  ? "var(--green)"
                                  : winRate >= 40
                                    ? "var(--amber)"
                                    : "var(--red)",
                            }}
                          />
                        </div>
                        <span className="text-xs text-[var(--muted)] w-32 text-right">
                          {record.wins}W / {record.losses}L / {record.ties}T ({winRate.toFixed(0)}%)
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Rubric results */}
          {Object.keys(modelRubric).length > 0 && (
            <div className="p-6 rounded-lg border border-[var(--border)] bg-[var(--card)]">
              <h2 className="text-lg font-semibold text-[var(--purple)] mb-4">
                Rubric Scores
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[var(--muted)] text-xs">
                      <th className="text-left py-2 pr-4">Model</th>
                      {RUBRIC_DIMENSIONS.map((d) => (
                        <th key={d.id} className="text-center px-1 py-2" title={d.description}>
                          {d.name.slice(0, 8)}
                        </th>
                      ))}
                      <th className="text-center px-2 py-2">Avg</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(modelRubric).map(([model, dims]) => {
                      const allScores = Object.values(dims).flat();
                      const avg = allScores.length > 0
                        ? allScores.reduce((a, b) => a + b, 0) / allScores.length
                        : 0;
                      return (
                        <tr key={model} className="border-t border-[var(--border)]">
                          <td className="py-2 pr-4">{model}</td>
                          {RUBRIC_DIMENSIONS.map((d) => {
                            const vals = dims[d.id] || [];
                            const dimAvg = vals.length > 0
                              ? vals.reduce((a, b) => a + b, 0) / vals.length
                              : null;
                            return (
                              <td
                                key={d.id}
                                className="text-center px-1 py-2"
                                style={{
                                  color: dimAvg
                                    ? dimAvg >= 4
                                      ? "var(--green)"
                                      : dimAvg >= 3
                                        ? "var(--amber)"
                                        : "var(--red)"
                                    : "var(--muted)",
                                }}
                              >
                                {dimAvg ? dimAvg.toFixed(1) : "-"}
                              </td>
                            );
                          })}
                          <td
                            className="text-center px-2 py-2 font-semibold"
                            style={{
                              color: avg >= 4 ? "var(--green)" : avg >= 3 ? "var(--amber)" : "var(--red)",
                            }}
                          >
                            {avg.toFixed(2)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
