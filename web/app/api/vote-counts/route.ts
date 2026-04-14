import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

const VOTES_FILE = path.join(process.cwd(), "data", "votes.jsonl");

export async function GET() {
  try {
    const raw = await fs.readFile(VOTES_FILE, "utf-8");
    const counts: Record<string, number> = {};
    for (const line of raw.split("\n")) {
      if (!line.trim()) continue;
      try {
        const vote = JSON.parse(line);
        if (vote.mode !== "arena") continue;
        const id = vote.scenario_id;
        if (!id) continue;
        counts[id] = (counts[id] ?? 0) + 1;
      } catch {
        // skip malformed line
      }
    }
    return NextResponse.json({ counts });
  } catch (error: any) {
    if (error.code === "ENOENT") {
      return NextResponse.json({ counts: {} });
    }
    return NextResponse.json({ error: "Failed to read vote counts" }, { status: 500 });
  }
}
