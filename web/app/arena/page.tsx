"use client";

import { useState, useCallback } from "react";
import { Vote } from "@/lib/types";
import { saveVote } from "@/lib/votes";
import { SAMPLE_SCENARIOS } from "@/lib/sample-data";

function formatRP(text: string) {
  // Convert *actions* to italics and preserve paragraph breaks
  return text
    .split("\n\n")
    .map((p, i) => {
      const html = p.replace(/\*([^*]+)\*/g, "<em>$1</em>");
      return (
        <p key={i} className="mb-3" dangerouslySetInnerHTML={{ __html: html }} />
      );
    });
}

export default function ArenaPage() {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [winner, setWinner] = useState<"A" | "B" | "tie" | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [voteCount, setVoteCount] = useState(0);

  const scenarios = SAMPLE_SCENARIOS;
  const current = scenarios[currentIdx % scenarios.length];

  // Randomize which model is A/B
  const [shuffled] = useState(() =>
    scenarios.map((s) => (Math.random() > 0.5 ? [0, 1] : [1, 0]))
  );
  const order = shuffled[currentIdx % shuffled.length];
  const responseA = current.responses[order[0]];
  const responseB = current.responses[order[1]];

  const handleVote = useCallback(
    (choice: "A" | "B" | "tie") => {
      setWinner(choice);
      setRevealed(true);

      const vote: Vote = {
        id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        mode: "arena",
        scenario_id: current.id,
        context: current.context,
        model_a: responseA.model,
        model_b: responseB.model,
        response_a: responseA.content,
        response_b: responseB.content,
        winner:
          choice === "A"
            ? (order[0] === 0 ? "A" : "B")
            : choice === "B"
              ? (order[1] === 0 ? "A" : "B")
              : "tie",
      };
      saveVote(vote);
      setVoteCount((c) => c + 1);
    },
    [current, responseA, responseB, order]
  );

  const handleNext = () => {
    setCurrentIdx((i) => i + 1);
    setWinner(null);
    setRevealed(false);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Arena</h1>
          <p className="text-sm text-[var(--muted)]">
            Which response is better? Models are hidden until you vote.
          </p>
        </div>
        <div className="text-sm text-[var(--muted)]">
          Votes this session: <span className="text-[var(--accent)]">{voteCount}</span>
        </div>
      </div>

      {/* Context */}
      <div className="mb-6 p-4 rounded-lg border border-[var(--border)] bg-[var(--card)]">
        <div className="text-xs uppercase tracking-wider text-[var(--muted)] mb-2">
          Conversation Context
        </div>
        <div className="rp-prose text-sm max-h-48 overflow-y-auto">
          {formatRP(current.context)}
        </div>
      </div>

      {/* Responses side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {[
          { label: "Response A", response: responseA, key: "A" as const },
          { label: "Response B", response: responseB, key: "B" as const },
        ].map(({ label, response, key }) => (
          <div
            key={key}
            className={`rounded-lg border p-4 transition cursor-pointer ${
              winner === key
                ? "border-[var(--green)] bg-[var(--green)]/5"
                : winner && winner !== key && winner !== "tie"
                  ? "border-[var(--border)] opacity-50"
                  : "border-[var(--border)] bg-[var(--card)] hover:border-[var(--accent)]"
            }`}
            onClick={() => !revealed && handleVote(key)}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-semibold text-[var(--accent)]">
                {label}
              </span>
              {revealed && (
                <span className="text-xs px-2 py-0.5 rounded bg-[var(--border)] text-[var(--foreground)]">
                  {response.model}
                </span>
              )}
            </div>
            <div className="rp-prose text-sm max-h-96 overflow-y-auto">
              {formatRP(response.content)}
            </div>
          </div>
        ))}
      </div>

      {/* Vote buttons */}
      {!revealed ? (
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => handleVote("A")}
            className="px-6 py-2.5 rounded-lg bg-[var(--accent)] text-[var(--background)] font-semibold hover:bg-[var(--accent-hover)] transition"
          >
            A is better
          </button>
          <button
            onClick={() => handleVote("tie")}
            className="px-6 py-2.5 rounded-lg border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--muted)] transition"
          >
            Tie
          </button>
          <button
            onClick={() => handleVote("B")}
            className="px-6 py-2.5 rounded-lg bg-[var(--purple)] text-[var(--background)] font-semibold hover:opacity-90 transition"
          >
            B is better
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <div className="text-sm text-[var(--muted)]">
            You picked{" "}
            <span className="text-[var(--foreground)] font-semibold">
              {winner === "tie" ? "Tie" : `Response ${winner}`}
            </span>
            {winner !== "tie" && (
              <>
                {" "}({winner === "A" ? responseA.model : responseB.model})
              </>
            )}
          </div>
          <button
            onClick={handleNext}
            className="px-6 py-2.5 rounded-lg bg-[var(--green)] text-[var(--background)] font-semibold hover:opacity-90 transition"
          >
            Next matchup
          </button>
        </div>
      )}
    </div>
  );
}
