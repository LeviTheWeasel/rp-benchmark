"use client";

import { useState, useCallback, useEffect } from "react";
import { Vote } from "@/lib/types";
import { saveVote } from "@/lib/votes";
import { SAMPLE_SCENARIOS } from "@/lib/sample-data";
import { BENCHMARK_SCENARIOS } from "@/lib/benchmark-data";
import { CATCH_PAIRS } from "@/lib/catch-pairs";

const CATCH_CADENCE = 10; // inject a catch pair every Nth slot

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

function isNSFW(scenario: { id: string }) {
  return scenario.id.includes("erp_");
}

export default function ArenaPage() {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [winner, setWinner] = useState<"A" | "B" | "tie" | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [voteCount, setVoteCount] = useState(0);
  const [showNSFW, setShowNSFW] = useState(false);
  const [nsfwDismissed, setNsfwDismissed] = useState(false);

  // Scenario list ordered by vote-count priority, with scenarios this voter
  // has already voted on filtered out. Initial render uses a random shuffle;
  // once /api/vote-counts resolves we re-sort by ascending vote count (random
  // tiebreak) and remove already-voted pairs. Order is then frozen for the
  // session so new votes don't teleport the user.
  const [scenarios, setScenarios] = useState(() => {
    const all = [...SAMPLE_SCENARIOS, ...BENCHMARK_SCENARIOS];
    for (let i = all.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [all[i], all[j]] = [all[j], all[i]];
    }
    return all;
  });
  const [exhausted, setExhausted] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/vote-counts")
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        const counts: Record<string, number> = data.counts ?? {};
        const votedByMe = new Set<string>(data.voted_by_me ?? []);
        setScenarios((prev) => {
          const catchIds = new Set(CATCH_PAIRS.map((c) => c.id));
          // Main pool = real scenarios the voter hasn't seen, sorted by coverage.
          const main = prev.filter((s) => !votedByMe.has(s.id) && !catchIds.has(s.id));
          const mainDecorated = main.map((s) => ({
            scenario: s,
            votes: counts[s.id] ?? 0,
            jitter: Math.random(),
          }));
          mainDecorated.sort((a, b) => a.votes - b.votes || a.jitter - b.jitter);
          const mainOrdered = mainDecorated.map((d) => d.scenario);

          // Catch pool = catches the voter hasn't seen, shuffled so each voter
          // gets a different sequence of catches.
          const catches = CATCH_PAIRS.filter((c) => !votedByMe.has(c.id));
          for (let i = catches.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [catches[i], catches[j]] = [catches[j], catches[i]];
          }

          // Interleave: every CATCH_CADENCE-th slot pulls the next catch. If
          // catches run out we just continue with the main pool.
          const interleaved: typeof mainOrdered = [];
          let mi = 0;
          let ci = 0;
          const total = mainOrdered.length + catches.length;
          for (let slot = 0; slot < total; slot++) {
            const isCatchSlot =
              slot > 0 && slot % CATCH_CADENCE === 0 && ci < catches.length;
            if (isCatchSlot) {
              interleaved.push(catches[ci++]);
            } else if (mi < mainOrdered.length) {
              interleaved.push(mainOrdered[mi++]);
            } else if (ci < catches.length) {
              interleaved.push(catches[ci++]);
            }
          }

          if (interleaved.length === 0) {
            setExhausted(true);
            return prev;
          }
          return interleaved;
        });
      })
      .catch(() => {
        // Non-fatal: keep the random order we already seeded with.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const current = scenarios[currentIdx % scenarios.length];
  const currentIsNSFW = isNSFW(current);

  // A/B side assignment is keyed by scenario id so re-sorting the scenarios
  // list after counts load doesn't cause the same matchup to show with
  // inverted sides.
  const [sideFlips] = useState(() => {
    const m: Record<string, 0 | 1> = {};
    for (const s of [...SAMPLE_SCENARIOS, ...BENCHMARK_SCENARIOS]) {
      m[s.id] = Math.random() > 0.5 ? 1 : 0;
    }
    return m;
  });
  const flip = sideFlips[current.id] ?? 0;
  const order: [number, number] = flip === 0 ? [0, 1] : [1, 0];
  const responseA = current.responses[order[0]];
  const responseB = current.responses[order[1]];

  const handleVote = useCallback(
    async (choice: "A" | "B" | "tie") => {
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
      const result = await saveVote(vote);
      if (result.ok) {
        setVoteCount((c) => c + 1);
        return;
      }
      if (result.alreadyVoted) {
        // Race: another tab or the same voter already logged this pair.
        // Drop it from the visible list and move on without counting.
        setScenarios((prev) => {
          const next = prev.filter((s) => s.id !== current.id);
          if (next.length === 0) setExhausted(true);
          return next;
        });
      }
    },
    [current, responseA, responseB, order]
  );

  const handleNext = () => {
    setCurrentIdx((i) => i + 1);
    setWinner(null);
    setRevealed(false);
    setShowNSFW(false);
  };

  if (exhausted || !current) {
    return (
      <div className="flex flex-col h-[calc(100vh-3.5rem)] items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="text-xl font-semibold mb-3">All matchups covered</div>
          <p className="text-sm text-[var(--muted)] mb-6">
            You&apos;ve voted on every pair available for this voter id. Thank you — your votes are saved server-side. Check back after new scenarios are added, or clear the <code>rpbench_voter_id</code> cookie to start fresh.
          </p>
          <div className="text-sm text-[var(--muted)]">Votes this session: <span className="text-[var(--accent)] font-semibold">{voteCount}</span></div>
        </div>
      </div>
    );
  }

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
        <div className="text-sm text-[var(--muted)] flex gap-4">
          <span>Matchup {(currentIdx % scenarios.length) + 1} / {scenarios.length}</span>
          <span>Votes: <span className="text-[var(--accent)] font-semibold">{voteCount}</span></span>
        </div>
      </div>

      {/* NSFW warning */}
      {currentIsNSFW && !showNSFW && !nsfwDismissed && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center p-8 max-w-md">
            <div className="text-2xl mb-3 text-[var(--red)]">NSFW Content</div>
            <p className="text-sm text-[var(--muted)] mb-6">
              This matchup contains explicit sexual content (ERP). These responses are part of the benchmark for evaluating erotic writing quality.
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => setShowNSFW(true)}
                className="px-6 py-2.5 rounded-lg bg-[var(--red)] text-[var(--background)] font-semibold hover:opacity-90"
              >
                Show anyway
              </button>
              <button
                onClick={() => { setNsfwDismissed(true); setShowNSFW(true); }}
                className="px-6 py-2.5 rounded-lg border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)]"
              >
                Show all NSFW (don't ask again)
              </button>
              <button
                onClick={handleNext}
                className="px-6 py-2.5 rounded-lg border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)]"
              >
                Skip
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main content (hidden if NSFW warning is showing) */}
      {(!currentIsNSFW || showNSFW || nsfwDismissed) && <>

      {/* Character info + Context */}
      <div className="shrink-0 border-b border-[var(--border)] bg-[var(--card)]">
        {current.character_info && (
          <div className="px-4 py-2 flex gap-6 text-xs border-b border-[var(--border)]">
            <span><span className="text-[var(--muted)]">Character:</span> <span className="text-[var(--accent)]">{current.character_info.character_name}</span></span>
            <span><span className="text-[var(--muted)]">User plays:</span> <span className="text-[var(--purple)]">{current.character_info.user_name}</span></span>
          </div>
        )}
        <details>
          <summary className="px-4 py-2 text-xs uppercase tracking-wider text-[var(--muted)] cursor-pointer hover:text-[var(--foreground)] select-none">
            Scene Context {current.character_info ? `& Setting` : ''}
          </summary>
          <div className="px-4 pb-3 text-sm max-h-40 overflow-y-auto space-y-2">
            {current.character_info && (
              <p className="text-[var(--muted)] text-xs leading-relaxed">
                {current.character_info.setting_summary}
              </p>
            )}
            <div className="rp-prose">{formatRP(current.context)}</div>
          </div>
        </details>
      </div>

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

      </>}

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
