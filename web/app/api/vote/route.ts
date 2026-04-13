import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

const VOTES_FILE = path.join(process.cwd(), "data", "votes.jsonl");

export async function POST(req: NextRequest) {
  try {
    const vote = await req.json();

    // Basic validation
    if (!vote.id || !vote.mode || !vote.scenario_id) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    // Add server timestamp and IP hash for dedup
    vote.server_timestamp = new Date().toISOString();

    // Ensure data directory exists
    await fs.mkdir(path.join(process.cwd(), "data"), { recursive: true });

    // Append as JSONL (one JSON object per line)
    await fs.appendFile(VOTES_FILE, JSON.stringify(vote) + "\n");

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("Vote save error:", error);
    return NextResponse.json({ error: "Failed to save vote" }, { status: 500 });
  }
}
