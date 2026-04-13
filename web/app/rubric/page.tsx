"use client";

import { useState, useCallback } from "react";
import { Vote, RUBRIC_DIMENSIONS } from "@/lib/types";
import { saveVote } from "@/lib/votes";
import { SAMPLE_SCENARIOS } from "@/lib/sample-data";
import { BENCHMARK_SCENARIOS } from "@/lib/benchmark-data";

function formatRP(text: string) {
  return text
    .split("\n\n")
    .map((p, i) => {
      const html = p.replace(/\*([^*]+)\*/g, "<em>$1</em>");
      return (
        <p key={i} className="mb-3" dangerouslySetInnerHTML={{ __html: html }} />
      );
    });
}

const SCORE_LABELS: Record<number, string> = {
  1: "Broken",
  2: "Below avg",
  3: "Adequate",
  4: "Strong",
  5: "Exceptional",
};

const SCORE_COLORS: Record<number, string> = {
  1: "var(--red)",
  2: "var(--amber)",
  3: "var(--muted)",
  4: "var(--green)",
  5: "var(--accent)",
};

function ScoreButton({
  value,
  selected,
  onClick,
}: {
  value: number;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center gap-0.5 transition"
      style={{
        color: selected ? SCORE_COLORS[value] : "var(--muted)",
        opacity: selected ? 1 : 0.5,
      }}
    >
      <span className={`text-lg font-bold ${selected ? "scale-125" : ""} transition-transform`}>
        {value}
      </span>
      <span className="text-[10px]">{SCORE_LABELS[value]}</span>
    </button>
  );
}

interface FlatResponse {
  scenario_id: string;
  context: string;
  model: string;
  content: string;
}

export default function RubricPage() {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [voteCount, setVoteCount] = useState(0);

  // Flatten all responses into a shuffled list
  const [responses] = useState(() => {
    const flat: FlatResponse[] = [];
    for (const s of [...SAMPLE_SCENARIOS, ...BENCHMARK_SCENARIOS]) {
      for (const r of s.responses) {
        flat.push({
          scenario_id: s.id,
          context: s.context,
          model: r.model,
          content: r.content,
        });
      }
    }
    // Shuffle
    for (let i = flat.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [flat[i], flat[j]] = [flat[j], flat[i]];
    }
    return flat;
  });

  const current = responses[currentIdx % responses.length];

  // Alias for compatibility with the rest of the component
  const response = { model: current.model, content: current.content };

  const handleScore = (dimId: string, value: number) => {
    setScores((prev) => ({ ...prev, [dimId]: value }));
  };

  const scoredCount = Object.keys(scores).length;
  const allScored = scoredCount >= RUBRIC_DIMENSIONS.length;

  const handleSubmit = useCallback(() => {
    const vote: Vote = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      mode: "rubric",
      scenario_id: current.scenario_id,
      context: current.context,
      model: response.model,
      response: response.content,
      scores,
      notes,
    };
    saveVote(vote);
    setSubmitted(true);
    setVoteCount((c) => c + 1);
  }, [current, response, scores, notes]);

  const handleNext = () => {
    setCurrentIdx((i) => i + 1);
    setScores({});
    setNotes("");
    setSubmitted(false);
  };

  const tier1 = RUBRIC_DIMENSIONS.filter((d) => d.tier === 1);
  const tier2 = RUBRIC_DIMENSIONS.filter((d) => d.tier === 2);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Rubric Score</h1>
          <p className="text-sm text-[var(--muted)]">
            Rate this response on each dimension. Model is hidden until you submit.
          </p>
        </div>
        <div className="text-sm text-[var(--muted)] flex gap-4">
          <span>Response {(currentIdx % responses.length) + 1} / {responses.length}</span>
          <span>Scored: <span className="text-[var(--accent)]">{voteCount}</span></span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Context + Response */}
        <div className="space-y-4">
          <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--card)]">
            <div className="text-xs uppercase tracking-wider text-[var(--muted)] mb-2">
              Context
            </div>
            <div className="rp-prose text-sm max-h-36 overflow-y-auto">
              {formatRP(current.context)}
            </div>
          </div>

          <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--card)]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs uppercase tracking-wider text-[var(--muted)]">
                Response
              </span>
              {submitted && (
                <span className="text-xs px-2 py-0.5 rounded bg-[var(--border)]">
                  {response.model}
                </span>
              )}
            </div>
            <div className="rp-prose text-sm max-h-[60vh] overflow-y-auto">
              {formatRP(response.content)}
            </div>
          </div>
        </div>

        {/* Right: Scoring rubric */}
        <div className="space-y-4">
          {/* Tier 1 */}
          <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--card)]">
            <h3 className="text-sm font-semibold text-[var(--green)] mb-3">
              Tier 1: Fundamentals
            </h3>
            <div className="space-y-4">
              {tier1.map((dim) => (
                <div key={dim.id}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">{dim.name}</span>
                    <span className="text-xs text-[var(--muted)]">{dim.description}</span>
                  </div>
                  <div className="flex gap-4 justify-between">
                    {[1, 2, 3, 4, 5].map((v) => (
                      <ScoreButton
                        key={v}
                        value={v}
                        selected={scores[dim.id] === v}
                        onClick={() => !submitted && handleScore(dim.id, v)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Tier 2 */}
          <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--card)]">
            <h3 className="text-sm font-semibold text-[var(--amber)] mb-3">
              Tier 2: Quality Control
            </h3>
            <div className="space-y-4">
              {tier2.map((dim) => (
                <div key={dim.id}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">{dim.name}</span>
                    <span className="text-xs text-[var(--muted)]">{dim.description}</span>
                  </div>
                  <div className="flex gap-4 justify-between">
                    {[1, 2, 3, 4, 5].map((v) => (
                      <ScoreButton
                        key={v}
                        value={v}
                        selected={scores[dim.id] === v}
                        onClick={() => !submitted && handleScore(dim.id, v)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Notes */}
          <textarea
            placeholder="Optional notes — what stood out? (good or bad)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={submitted}
            className="w-full p-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm text-[var(--foreground)] placeholder-[var(--muted)] resize-none h-20 focus:outline-none focus:border-[var(--accent)]"
          />

          {/* Submit */}
          {!submitted ? (
            <button
              onClick={handleSubmit}
              disabled={!allScored}
              className={`w-full py-3 rounded-lg font-semibold transition ${
                allScored
                  ? "bg-[var(--accent)] text-[var(--background)] hover:bg-[var(--accent-hover)]"
                  : "bg-[var(--border)] text-[var(--muted)] cursor-not-allowed"
              }`}
            >
              {allScored
                ? "Submit Scores"
                : `Score all dimensions (${scoredCount}/${RUBRIC_DIMENSIONS.length})`}
            </button>
          ) : (
            <button
              onClick={handleNext}
              className="w-full py-3 rounded-lg font-semibold bg-[var(--green)] text-[var(--background)] hover:opacity-90 transition"
            >
              Next response
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
