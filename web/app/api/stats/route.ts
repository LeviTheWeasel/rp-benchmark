import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

const VOTES_FILE = path.join(process.cwd(), "data", "votes.jsonl");

/**
 * Lightweight summary stats for the README badge and any external
 * dashboards. Returns just numbers — no raw vote payloads — so it can
 * be hit cheaply by shields.io and similar services.
 */
export async function GET() {
  let total = 0;
  let arena = 0;
  let rubric = 0;
  let multiturnArena = 0;
  const voterIds = new Set<string>();
  const pairs = new Set<string>();
  const multiturnPairs = new Set<string>();
  let catchTotal = 0;
  let catchCorrect = 0;

  try {
    const raw = await fs.readFile(VOTES_FILE, "utf-8");
    for (const line of raw.split("\n")) {
      if (!line.trim()) continue;
      try {
        const v = JSON.parse(line);
        total += 1;
        if (v.mode === "arena") {
          arena += 1;
          if (!v.is_catch && v.scenario_id) pairs.add(v.scenario_id);
          if (v.is_catch) {
            catchTotal += 1;
            if (v.catch_correct) catchCorrect += 1;
          }
        } else if (v.mode === "multiturn_arena") {
          multiturnArena += 1;
          if (v.scenario_id) multiturnPairs.add(v.scenario_id);
        } else if (v.mode === "rubric") {
          rubric += 1;
        }
        if (v.voter_id) voterIds.add(v.voter_id);
      } catch {
        // skip malformed line
      }
    }
  } catch (err: any) {
    if (err.code !== "ENOENT") {
      return NextResponse.json({ error: "Failed to read stats" }, { status: 500 });
    }
  }

  return NextResponse.json(
    {
      total,
      arena,
      rubric,
      multiturn_arena: multiturnArena,
      voters: voterIds.size,
      pairs_covered: pairs.size,
      multiturn_pairs_covered: multiturnPairs.size,
      catch_pass_rate:
        catchTotal > 0 ? Math.round((catchCorrect / catchTotal) * 100) : null,
    },
    {
      headers: {
        // shields.io respects this; keep the badge fresh-ish without
        // hammering us on every page view of every README.
        "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
      },
    }
  );
}
