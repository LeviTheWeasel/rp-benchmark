import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import { getOrCreateVoterId } from "@/lib/voter";

const VOTES_FILE = path.join(process.cwd(), "data", "votes.jsonl");

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

    await fs.mkdir(path.join(process.cwd(), "data"), { recursive: true });
    await fs.appendFile(VOTES_FILE, JSON.stringify(vote) + "\n");

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("Vote save error:", error);
    return NextResponse.json({ error: "Failed to save vote" }, { status: 500 });
  }
}
