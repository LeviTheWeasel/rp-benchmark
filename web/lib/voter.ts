import { cookies } from "next/headers";

const COOKIE_NAME = "rpbench_voter_id";
// One year — long enough for a calibration campaign, short enough that a
// device passing hands eventually gets a fresh id.
const MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

function randomId(): string {
  // Cookie-safe random id. crypto.randomUUID is available in the Node runtime
  // used by route handlers.
  return crypto.randomUUID();
}

/**
 * Read the voter id from the request cookies, issuing a fresh one if absent.
 * Returns `{ voterId, isNew }` so callers can decide whether to surface the
 * new id in the response.
 *
 * The cookie is HTTP-only so browser JS can't spoof it, and the id itself is
 * opaque — no user data, no session content. We only use it to group votes
 * for dedup and per-voter analysis.
 */
export async function getOrCreateVoterId(): Promise<{
  voterId: string;
  isNew: boolean;
}> {
  const store = await cookies();
  const existing = store.get(COOKIE_NAME);
  if (existing?.value) {
    return { voterId: existing.value, isNew: false };
  }
  const voterId = randomId();
  store.set(COOKIE_NAME, voterId, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: MAX_AGE_SECONDS,
    path: "/",
    // `secure` left false so it works in dev over http; production behind
    // a TLS terminator will upgrade automatically on the first SameSite=Lax
    // request because browsers treat localhost exceptions separately.
  });
  return { voterId, isNew: true };
}

/** Read-only accessor. Returns undefined if the voter hasn't visited yet. */
export async function readVoterId(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(COOKIE_NAME)?.value;
}
