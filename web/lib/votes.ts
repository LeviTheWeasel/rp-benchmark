import { Vote } from "./types";

const STORAGE_KEY = "rpbench_votes";

export async function saveVote(vote: Vote): Promise<void> {
  // Save to localStorage (offline backup)
  const votes = getLocalVotes();
  votes.push(vote);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(votes));

  // Save to server
  try {
    await fetch("/api/vote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(vote),
    });
  } catch (e) {
    console.warn("Failed to save vote to server, saved locally:", e);
  }
}

export function getLocalVotes(): Vote[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw ? JSON.parse(raw) : [];
}

export async function getServerVotes(): Promise<Vote[]> {
  try {
    const resp = await fetch("/api/votes");
    const data = await resp.json();
    return data.votes || [];
  } catch {
    return [];
  }
}

export function exportVotes(): string {
  return JSON.stringify(getLocalVotes(), null, 2);
}

export function getVoteStats() {
  const votes = getLocalVotes();
  const arena = votes.filter((v) => v.mode === "arena");
  const rubric = votes.filter((v) => v.mode === "rubric");
  return { total: votes.length, arena: arena.length, rubric: rubric.length };
}
