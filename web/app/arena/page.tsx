"use client";

import { useState, useCallback } from "react";
import { Vote } from "@/lib/types";
import { saveVote } from "@/lib/votes";
import { SAMPLE_SCENARIOS } from "@/lib/sample-data";

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

export default function ArenaPage() {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [winner, setWinner] = useState<"A" | "B" | "tie" | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [voteCount, setVoteCount] = useState(0);

  const scenarios = SAMPLE_SCENARIOS;
  const current = scenarios[currentIdx % scenarios.length];

  const [shuffled] = useState(() =>
    scenarios.map(() => (Math.random() > 0.5 ? [0, 1] : [1, 0]))
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
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Header bar */}
      <div className="shrink-0 px-4 py-3 flex items-center justify-between border-b border-[var(--border)]">
        <div>
          <span className="font-semibold">Arena</span>
          <span className="text-sm text-[var(--muted)] ml-3">
            Which response is better? Models hidden until you vote.
          </span>
        </div>
        <div className="text-sm text-[var(--muted)]">
          Votes: <span className="text-[var(--accent)] font-semibold">{voteCount}</span>
        </div>
      </div>

      {/* Context — collapsible, compact */}
      <details className="shrink-0 border-b border-[var(--border)] bg-[var(--card)]">
        <summary className="px-4 py-2 text-xs uppercase tracking-wider text-[var(--muted)] cursor-pointer hover:text-[var(--foreground)] select-none">
          Conversation Context
        </summary>
        <div className="px-4 pb-3 rp-prose text-sm max-h-40 overflow-y-auto">
          {formatRP(current.context)}
        </div>
      </details>

      {/* Responses — fill remaining height */}
      <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-2 gap-0 md:gap-px bg-[var(--border)]">
        {[
          { label: "Response A", response: responseA, key: "A" as const },
          { label: "Response B", response: responseB, key: "B" as const },
        ].map(({ label, response, key }) => (
          <div
            key={key}
            className={`flex flex-col overflow-hidden transition-colors ${
              winner === key
                ? "bg-[var(--green)]/5"
                : winner && winner !== key && winner !== "tie"
                  ? "bg-[var(--background)] opacity-40"
                  : "bg-[var(--background)] hover:bg-[var(--card)] cursor-pointer"
            }`}
            onClick={() => !revealed && handleVote(key)}
          >
            {/* Response header */}
            <div className="shrink-0 px-5 py-2.5 flex items-center justify-between border-b border-[var(--border)]">
              <span
                className={`text-sm font-semibold ${
                  key === "A" ? "text-[var(--accent)]" : "text-[var(--purple)]"
                }`}
              >
                {label}
              </span>
              {revealed && (
                <span className="text-xs px-2 py-0.5 rounded bg-[var(--card-raised)] text-[var(--foreground)]">
                  {response.model}
                </span>
              )}
              {winner === key && (
                <span className="text-xs px-2 py-0.5 rounded bg-[var(--green)]/20 text-[var(--green)] font-semibold">
                  Winner
                </span>
              )}
            </div>

            {/* Response body — scrollable, fills remaining space */}
            <div className="flex-1 overflow-y-auto px-5 py-4 rp-prose">
              {formatRP(response.content)}
            </div>
          </div>
        ))}
      </div>

      {/* Vote bar — pinned at bottom */}
      <div className="shrink-0 border-t border-[var(--border)] bg-[var(--card)] px-4 py-3">
        {!revealed ? (
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => handleVote("A")}
              className="px-8 py-2.5 rounded-lg bg-[var(--accent)] text-[var(--background)] font-semibold hover:bg-[var(--accent-hover)]"
            >
              A is better
            </button>
            <button
              onClick={() => handleVote("tie")}
              className="px-6 py-2.5 rounded-lg border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--muted)]"
            >
              Tie
            </button>
            <button
              onClick={() => handleVote("B")}
              className="px-8 py-2.5 rounded-lg bg-[var(--purple)] text-[var(--background)] font-semibold hover:opacity-90"
            >
              B is better
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-4">
            <span className="text-sm text-[var(--muted)]">
              You picked{" "}
              <span className="text-[var(--foreground)] font-semibold">
                {winner === "tie" ? "Tie" : `Response ${winner}`}
              </span>
              {winner !== "tie" && (
                <> ({winner === "A" ? responseA.model : responseB.model})</>
              )}
            </span>
            <button
              onClick={handleNext}
              className="px-6 py-2.5 rounded-lg bg-[var(--green)] text-[var(--background)] font-semibold hover:opacity-90"
            >
              Next matchup
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
