/**
 * Per-voter rate limiter for /api/vote.
 *
 * Two limits apply simultaneously:
 *   - minIntervalMs: the shortest allowed gap between two votes.
 *   - maxInWindow / windowMs: sliding-window cap on sustained volume.
 *
 * Both are held in a Map keyed by voter id. The map is process-local; a
 * multi-instance deployment would need to move this to Redis or similar.
 * For the single-server community campaign we plan to run, in-memory is
 * the right trade: the state dies with the process (so no DB schema, no
 * migration, no persistence bug surface), and if the process restarts
 * everyone's counter resets, which is fine — the goal is to stop
 * rapid-fire clicking within a session, not permanent banning.
 *
 * Stored on globalThis so Next.js hot reloads don't forget outstanding
 * state within a dev session.
 */

interface Bucket {
  timestamps: number[];
}

interface Store {
  buckets: Map<string, Bucket>;
}

const GLOBAL_KEY = "__rpbench_vote_rate_limit__";

function store(): Store {
  const g = globalThis as any;
  if (!g[GLOBAL_KEY]) {
    g[GLOBAL_KEY] = { buckets: new Map<string, Bucket>() } satisfies Store;
  }
  return g[GLOBAL_KEY];
}

export interface RateLimitConfig {
  minIntervalMs: number;
  windowMs: number;
  maxInWindow: number;
}

export const DEFAULT_VOTE_RATE_LIMIT: RateLimitConfig = {
  minIntervalMs: 3_000, // reading a matchup takes real time
  windowMs: 5 * 60_000, // 5-minute sliding window
  maxInWindow: 30, // ~ one every 10 seconds sustained
};

export type RateLimitDecision =
  | { allowed: true }
  | { allowed: false; retryAfterSeconds: number; reason: "too_fast" | "too_many" };

export function checkRate(
  voterId: string,
  now: number = Date.now(),
  config: RateLimitConfig = DEFAULT_VOTE_RATE_LIMIT
): RateLimitDecision {
  const s = store();
  const bucket = s.buckets.get(voterId) ?? { timestamps: [] };

  // Drop anything outside the window.
  const windowStart = now - config.windowMs;
  const recent = bucket.timestamps.filter((t) => t >= windowStart);

  // Min-interval check.
  const last = recent.length > 0 ? recent[recent.length - 1] : 0;
  const gap = now - last;
  if (last > 0 && gap < config.minIntervalMs) {
    // Don't record — the attempt is rejected.
    s.buckets.set(voterId, { timestamps: recent });
    return {
      allowed: false,
      retryAfterSeconds: Math.ceil((config.minIntervalMs - gap) / 1000),
      reason: "too_fast",
    };
  }

  // Window cap.
  if (recent.length >= config.maxInWindow) {
    const oldest = recent[0];
    const waitMs = oldest + config.windowMs - now;
    s.buckets.set(voterId, { timestamps: recent });
    return {
      allowed: false,
      retryAfterSeconds: Math.max(1, Math.ceil(waitMs / 1000)),
      reason: "too_many",
    };
  }

  recent.push(now);
  s.buckets.set(voterId, { timestamps: recent });
  return { allowed: true };
}
