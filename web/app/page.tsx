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
          href="/arena"
          className="block p-6 rounded-lg border border-[var(--border)] bg-[var(--card)] hover:border-[var(--accent)] transition group"
        >
          <h2 className="text-xl font-semibold mb-1 group-hover:text-[var(--accent)] transition">
            Arena
          </h2>
          <p className="text-sm text-[var(--muted)]">
            Two responses, side by side, models hidden. Pick the better one.
            Fast and fun — each vote takes 30 seconds.
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
