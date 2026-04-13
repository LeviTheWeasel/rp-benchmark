import { Vote } from "./types";

const STORAGE_KEY = "rpbench_votes";

export function saveVote(vote: Vote): void {
  const votes = getVotes();
  votes.push(vote);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(votes));
}

export function getVotes(): Vote[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw ? JSON.parse(raw) : [];
}

export function exportVotes(): string {
  return JSON.stringify(getVotes(), null, 2);
}

export function getVoteStats() {
  const votes = getVotes();
  const arena = votes.filter((v) => v.mode === "arena");
  const rubric = votes.filter((v) => v.mode === "rubric");
  return { total: votes.length, arena: arena.length, rubric: rubric.length };
}
