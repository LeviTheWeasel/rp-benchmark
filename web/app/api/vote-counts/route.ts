import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import { getOrCreateVoterId } from "@/lib/voter";

const VOTES_FILE = path.join(process.cwd(), "data", "votes.jsonl");

export async function GET() {
  const { voterId } = await getOrCreateVoterId();
  const counts: Record<string, number> = {};
  const votedByMe: string[] = [];

  try {
    const raw = await fs.readFile(VOTES_FILE, "utf-8");
    for (const line of raw.split("\n")) {
      if (!line.trim()) continue;
      try {
        const vote = JSON.parse(line);
        if (vote.mode !== "arena") continue;
        const id = vote.scenario_id;
        if (!id) continue;
        counts[id] = (counts[id] ?? 0) + 1;
        if (vote.voter_id === voterId) {
          votedByMe.push(id);
        }
      } catch {
        // skip malformed line
      }
    }
  } catch (error: any) {
    if (error.code !== "ENOENT") {
      return NextResponse.json(
        { error: "Failed to read vote counts" },
        { status: 500 }
      );
    }
  }

  return NextResponse.json({ counts, voted_by_me: votedByMe });
}
