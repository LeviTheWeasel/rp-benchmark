import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

const VOTES_FILE = path.join(process.cwd(), "data", "votes.jsonl");

export async function GET() {
  try {
    const raw = await fs.readFile(VOTES_FILE, "utf-8");
    const votes = raw
      .trim()
      .split("\n")
      .filter(Boolean)
      .map((line) => JSON.parse(line));

    return NextResponse.json({ votes, count: votes.length });
  } catch (error: any) {
    if (error.code === "ENOENT") {
      return NextResponse.json({ votes: [], count: 0 });
    }
    return NextResponse.json({ error: "Failed to read votes" }, { status: 500 });
  }
}
