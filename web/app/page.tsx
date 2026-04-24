import Link from "next/link";

export default function Home() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <h1 className="text-3xl font-bold text-[var(--accent)] mb-2">RP-Bench</h1>
      <p className="text-[var(--muted)] mb-10">
        Help calibrate the roleplay benchmark by rating AI responses.
        Your votes validate whether our LLM judges agree with real humans.
      </p>

      <div className="grid gap-4">
        <Link
          href="/multiturn-arena"
          className="block p-6 rounded-lg border border-[var(--accent)]/30 bg-[var(--card)] hover:border-[var(--accent)] transition group"
        >
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-semibold group-hover:text-[var(--accent)] transition">
              Multi-Turn Arena
            </h2>
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-[var(--accent)]/10 text-[var(--accent)] font-semibold">
              Active
            </span>
          </div>
          <p className="text-sm text-[var(--muted)]">
            Compare full 12-turn RP sessions side by side. Tests consistency,
            degradation, and narrative momentum across a whole scene. ~5 min per vote.
          </p>
        </Link>

        <Link
          href="/arena"
          className="block p-6 rounded-lg border border-[var(--border)] bg-[var(--card)] hover:border-[var(--muted)] transition group opacity-60"
        >
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-semibold group-hover:text-[var(--muted)] transition">
              Single-Turn Arena
            </h2>
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-[var(--green)]/10 text-[var(--green)] font-semibold">
              Complete — 2,000+ votes
            </span>
          </div>
          <p className="text-sm text-[var(--muted)]">
            Two responses side by side, models hidden. Voting is closed —
            see results below.
          </p>
        </Link>

        <Link
          href="/rubric"
          className="block p-6 rounded-lg border border-[var(--border)] bg-[var(--card)] hover:border-[var(--purple)] transition group"
        >
          <h2 className="text-xl font-semibold mb-1 group-hover:text-[var(--purple)] transition">
            Rubric Score
          </h2>
          <p className="text-sm text-[var(--muted)]">
            Score a single response on 12 dimensions. More detailed — helps
            us understand what makes RP good or bad, not just which is better.
          </p>
        </Link>

        <Link
          href="/results"
          className="block p-6 rounded-lg border border-[var(--border)] bg-[var(--card)] hover:border-[var(--green)] transition group"
        >
          <h2 className="text-xl font-semibold mb-1 group-hover:text-[var(--green)] transition">
            Results
          </h2>
          <p className="text-sm text-[var(--muted)]">
            See aggregated votes and how they compare to the LLM judges.
          </p>
        </Link>
      </div>
    </div>
  );
}
