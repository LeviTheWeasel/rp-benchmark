import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import { getOrCreateVoterId } from "@/lib/voter";
import { CATCH_EXPECTED_WINNER, isCatchScenario } from "@/lib/catch-pairs";

const VOTES_FILE = path.join(process.cwd(), "data", "votes.jsonl");

/**
 * Given a vote on a catch scenario, return whether the voter picked the
 * pre-declared good response. Returns undefined if the vote doesn't have
 * enough info (e.g. rubric mode, or missing model fields).
 */
function scoreCatchVote(vote: {
  scenario_id: string;
  model_a?: string;
  model_b?: string;
  winner?: string;
}): boolean | undefined {
  const expected = CATCH_EXPECTED_WINNER[vote.scenario_id];
  if (!expected) return undefined;
  if (!vote.model_a || !vote.model_b) return undefined;
  if (vote.winner === "tie") return false;
  if (vote.winner === "A") return vote.model_a === expected;
  if (vote.winner === "B") return vote.model_b === expected;
  return undefined;
}

async function hasVotedArena(voterId: string, scenarioId: string): Promise<boolean> {
  try {
    const raw = await fs.readFile(VOTES_FILE, "utf-8");
    for (const line of raw.split("\n")) {
      if (!line.trim()) continue;
      try {
        const v = JSON.parse(line);
        if (
          v.mode === "arena" &&
          v.voter_id === voterId &&
          v.scenario_id === scenarioId
        ) {
          return true;
        }
      } catch {
        // skip malformed line
      }
    }
  } catch (err: any) {
    if (err.code !== "ENOENT") throw err;
  }
  return false;
}

export async function POST(req: NextRequest) {
  try {
    const vote = await req.json();

    if (!vote.id || !vote.mode || !vote.scenario_id) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    const { voterId } = await getOrCreateVoterId();

    // Enforce one arena vote per (voter, scenario). Rubric votes are allowed
    // to repeat since a single user may re-score the same response.
    if (vote.mode === "arena" && (await hasVotedArena(voterId, vote.scenario_id))) {
      return NextResponse.json(
        { error: "already voted on this matchup", already_voted: true },
        { status: 409 }
      );
    }

    vote.voter_id = voterId;
    vote.server_timestamp = new Date().toISOString();
    if (vote.mode === "arena" && isCatchScenario(vote.scenario_id)) {
      vote.is_catch = true;
      const correct = scoreCatchVote(vote);
      if (correct !== undefined) vote.catch_correct = correct;
    }

    await fs.mkdir(path.join(process.cwd(), "data"), { recursive: true });
    await fs.appendFile(VOTES_FILE, JSON.stringify(vote) + "\n");

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("Vote save error:", error);
    return NextResponse.json({ error: "Failed to save vote" }, { status: 500 });
  }
}
