import Link from "next/link";

export default function ArenaPage() {
  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] items-center justify-center p-8">
      <div className="max-w-lg text-center">
        <div className="text-2xl font-semibold mb-3">Single-Turn Arena Complete</div>
        <p className="text-sm text-[var(--muted)] mb-4">
          Over 2,000 community votes have been collected across 271 pairs at
          median 7 votes per pair. The single-turn leaderboard is now locked.
          Thank you to all 338 voters who participated.
        </p>
        <p className="text-sm text-[var(--muted)] mb-8">
          We&apos;re now running the <strong>Multi-Turn Arena</strong> — compare
          full 12-turn RP sessions side by side. This tests what single
          responses can&apos;t: consistency, degradation, and narrative momentum
          across a whole scene.
        </p>
        <Link
          href="/multiturn-arena"
          className="inline-block px-8 py-3 rounded-lg bg-[var(--accent)] text-[var(--background)] font-semibold hover:bg-[var(--accent-hover)] transition"
        >
          Go to Multi-Turn Arena
        </Link>
        <div className="mt-6">
          <Link
            href="/results"
            className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition"
          >
            View single-turn results
          </Link>
        </div>
      </div>
    </div>
  );
}
