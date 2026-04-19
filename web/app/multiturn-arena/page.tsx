"use client";

import { useState, useCallback, useEffect } from "react";
import { Vote } from "@/lib/types";
import { saveVote } from "@/lib/votes";
import { MULTITURN_SESSIONS, MULTITURN_PAIRS, SEED_METADATA } from "@/lib/multiturn-data";
import { MultiturnSession, MultiturnPair } from "@/lib/multiturn-types";

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

/** Look up the session for a given (seed, model) combo. */
function findSession(seedId: string, model: string): MultiturnSession | undefined {
  return MULTITURN_SESSIONS.find(
    (s) => s.seed_id === seedId && s.test_model === model
  );
}

/** Readable seed label. */
function seedLabel(seedId: string): string {
  return seedId
    .replace("adv_", "")
    .replace(/_0\d$/, "")
    .replaceAll("_", " ");
}

export default function MultiturnArenaPage() {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [winner, setWinner] = useState<"A" | "B" | "tie" | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [voteCount, setVoteCount] = useState(0);
  const [rateLimit, setRateLimit] = useState<{ retryAfterSeconds: number } | null>(null);
  const [pairVotes, setPairVotes] = useState<Record<string, number>>({});

  // Pairs ordered by coverage priority, already-voted filtered out.
  const [pairs, setPairs] = useState<MultiturnPair[]>(() => {
    const shuffled = [...MULTITURN_PAIRS];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  });
  const [exhausted, setExhausted] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/vote-counts?mode=multiturn_arena")
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        const counts: Record<string, number> = data.counts ?? {};
        setPairVotes(counts);
        const votedByMe = new Set<string>(data.voted_by_me ?? []);
        setPairs((prev) => {
          const filtered = prev.filter((p) => !votedByMe.has(p.id));
          if (filtered.length === 0) {
            setExhausted(true);
            return prev;
          }
          const decorated = filtered.map((p) => ({
            pair: p,
            votes: counts[p.id] ?? 0,
            jitter: Math.random(),
          }));
          decorated.sort((a, b) => a.votes - b.votes || a.jitter - b.jitter);
          return decorated.map((d) => d.pair);
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!rateLimit) return;
    const t = setTimeout(
      () => setRateLimit(null),
      Math.max(1, rateLimit.retryAfterSeconds) * 1000
    );
    return () => clearTimeout(t);
  }, [rateLimit]);

  const current = pairs[currentIdx % pairs.length];

  // A/B side flip keyed by pair id.
  const [sideFlips] = useState(() => {
    const m: Record<string, 0 | 1> = {};
    for (const p of MULTITURN_PAIRS) {
      m[p.id] = Math.random() > 0.5 ? 1 : 0;
    }
    return m;
  });

  const flip = current ? (sideFlips[current.id] ?? 0) : 0;
  const modelA = current ? (flip === 0 ? current.model_a : current.model_b) : "";
  const modelB = current ? (flip === 0 ? current.model_b : current.model_a) : "";
  const sessionA = current ? findSession(current.seed_id, modelA) : undefined;
  const sessionB = current ? findSession(current.seed_id, modelB) : undefined;
  const charName = sessionA?.character_name ?? "Character";
  const userName = sessionA?.user_name ?? "User";

  const handleVote = useCallback(
    async (choice: "A" | "B" | "tie") => {
      if (!current) return;
      setWinner(choice);
      setRevealed(true);

      const vote: Vote = {
        id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        mode: "multiturn_arena",
        scenario_id: current.id,
        context: current.seed_id,
        model_a: modelA,
        model_b: modelB,
        winner: choice,
      };
      const result = await saveVote(vote);
      if (result.ok) {
        setVoteCount((c) => c + 1);
        setPairVotes((counts) => ({
          ...counts,
          [current.id]: (counts[current.id] ?? 0) + 1,
        }));
        return;
      }
      if (result.alreadyVoted) {
        setPairs((prev) => {
          const next = prev.filter((p) => p.id !== current.id);
          if (next.length === 0) setExhausted(true);
          return next;
        });
        return;
      }
      if (result.rateLimited) {
        setRevealed(false);
        setWinner(null);
        setRateLimit({ retryAfterSeconds: result.retryAfterSeconds ?? 3 });
      }
    },
    [current, modelA, modelB]
  );

  const handleNext = () => {
    setCurrentIdx((i) => i + 1);
    setWinner(null);
    setRevealed(false);
  };

  if (exhausted || !current) {
    return (
      <div className="flex flex-col h-[calc(100vh-3.5rem)] items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="text-xl font-semibold mb-3">All multi-turn matchups covered</div>
          <p className="text-sm text-[var(--muted)] mb-6">
            You&apos;ve voted on every multi-turn pair. Thank you for the deep reads.
          </p>
          <div className="text-sm text-[var(--muted)]">
            Votes this session: <span className="text-[var(--accent)] font-semibold">{voteCount}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 flex items-center justify-between border-b border-[var(--border)]">
        <div>
          <span className="font-semibold">Multi-Turn Arena</span>
          <span className="text-sm text-[var(--muted)] ml-3">
            Compare full 12-turn RP sessions. Which session is better overall?
          </span>
        </div>
        <div className="text-sm text-[var(--muted)] flex gap-4">
          <span>Pair {(currentIdx % pairs.length) + 1} / {pairs.length}</span>
          <span>
            This pair:{" "}
            <span className="text-[var(--foreground)] font-semibold">
              {pairVotes[current.id] ?? 0}
            </span>{" "}
            {(pairVotes[current.id] ?? 0) === 1 ? "vote" : "votes"}
          </span>
          <span>Your votes: <span className="text-[var(--accent)] font-semibold">{voteCount}</span></span>
        </div>
      </div>

      {/* Seed info */}
      {(() => {
        const meta = SEED_METADATA[current.seed_id];
        const failTarget = meta?.failure_target?.replaceAll("_", " ") ?? "";
        return (
          <div className="shrink-0 border-b border-[var(--border)] bg-[var(--card)]">
            <div className="px-4 py-2 flex gap-6 text-xs border-b border-[var(--border)]">
              <span>
                <span className="text-[var(--muted)]">Seed:</span>{" "}
                <span className="text-[var(--accent)] capitalize">{seedLabel(current.seed_id)}</span>
              </span>
              <span>
                <span className="text-[var(--muted)]">Character:</span>{" "}
                <span className="text-[var(--accent)]">{charName}</span>
              </span>
              <span>
                <span className="text-[var(--muted)]">User:</span>{" "}
                <span className="text-[var(--purple)]">{userName}</span>
              </span>
              <span>
                <span className="text-[var(--muted)]">Turns:</span>{" "}
                {sessionA?.dialogue.length ?? "?"}
              </span>
              {failTarget && (
                <span>
                  <span className="text-[var(--muted)]">Tests:</span>{" "}
                  <span className="text-[var(--amber)] capitalize">{failTarget}</span>
                </span>
              )}
            </div>
            {meta?.setting_summary && (
              <details>
                <summary className="px-4 py-2 text-xs uppercase tracking-wider text-[var(--muted)] cursor-pointer hover:text-[var(--foreground)] select-none">
                  Character &amp; Setting
                </summary>
                <div className="px-4 pb-3 text-sm text-[var(--muted)] leading-relaxed">
                  {meta.setting_summary}
                </div>
              </details>
            )}
          </div>
        );
      })()}

      {/* Sessions side by side */}
      <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-2 gap-0 md:gap-px bg-[var(--border)]">
        {[
          { label: "Session A", session: sessionA, model: modelA, key: "A" as const },
          { label: "Session B", session: sessionB, model: modelB, key: "B" as const },
        ].map(({ label, session, model, key }) => (
          <div
            key={key}
            className={`flex flex-col overflow-hidden transition-colors ${
              winner === key
                ? "bg-[var(--green)]/5"
                : winner && winner !== key && winner !== "tie"
                  ? "bg-[var(--background)] opacity-40"
                  : "bg-[var(--background)]"
            }`}
          >
            {/* Session header */}
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
                  {model}
                </span>
              )}
              {winner === key && (
                <span className="text-xs px-2 py-0.5 rounded bg-[var(--green)]/20 text-[var(--green)] font-semibold">
                  Winner
                </span>
              )}
            </div>

            {/* Dialogue — scrollable */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {session?.dialogue.map((msg, i) => {
                const isUser = msg.role === "user";
                const turnNum = Math.floor(i / 2);
                const isNewTurn = i % 2 === 0;
                return (
                  <div key={i}>
                    {isNewTurn && (
                      <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-2 mt-2 border-t border-[var(--border)] pt-2">
                        Turn {turnNum + 1}
                      </div>
                    )}
                    <div
                      className={`${
                        isUser
                          ? "text-[var(--muted)] text-sm pl-2 border-l-2 border-[var(--border)]"
                          : "rp-prose"
                      }`}
                    >
                      <span className="text-[10px] font-semibold uppercase tracking-wider block mb-1">
                        {isUser ? userName : charName}
                      </span>
                      {formatRP(msg.content)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Vote bar */}
      <div className="shrink-0 border-t border-[var(--border)] bg-[var(--card)] px-4 py-3">
        {rateLimit && (
          <div className="mb-2 text-center text-xs text-[var(--amber)]">
            Slow down — please wait ~{rateLimit.retryAfterSeconds}s before the next vote.
          </div>
        )}
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
                {winner === "tie" ? "Tie" : `Session ${winner}`}
              </span>
              {winner !== "tie" && (
                <> ({winner === "A" ? modelA : modelB})</>
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
