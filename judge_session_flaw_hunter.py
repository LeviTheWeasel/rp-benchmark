#!/usr/bin/env python3
"""Per-session flaw hunter on multi-turn data, with failure-target awareness.

For each multi-turn session, concatenates the character (model) turns
into one transcript and runs the flaw hunter. The system prompt is
augmented with the seed's failure_target so the judge knows what
specific failure mode to weight when scoring (e.g. "this scene was
designed to test agency violation — be especially strict about it").

Output: results/session_flaw_hunter.jsonl (append-only, resumable).
Each line: {session_id, model, seed, failure_target, score,
fatal/major/minor flaws, bonuses, summary, usage}.

Usage:
    python3 judge_session_flaw_hunter.py [--source PATH] [--judge MODEL]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from harness.api import chat_completion

DEFAULT_SOURCE = Path("results/multiturn_merged_all_v2.json")
DEFAULT_JUDGE = "anthropic/claude-sonnet-4"
RAW_OUT = Path("results/session_flaw_hunter.jsonl")
PROMPT_FILE = Path("prompts/judge_flaw_hunter.md")
SEEDS_FILE = Path("hf_dataset/_source/adversarial_seeds.json")

# Failure-target descriptors that prime the judge to scrutinize the right thing.
TARGET_PRIMERS = {
    "agency_violation": "This scene was specifically designed to test for AGENCY VIOLATIONS — situations where the model writes the user character's actions, dialogue, or internal states. Be especially vigilant for fatal-flaw 'agency_violation' deductions and quote the exact phrase that crosses the line.",
    "contradictory_context_resolution": "This scene tests how the model handles CONTRADICTORY LORE. The character should engage with the contradiction intellectually, not capitulate or dismiss. Score 'character_break' fatally if the character abandons their established expertise to please the user.",
    "narrative_stagnation": "This scene tests NARRATIVE MOMENTUM under a passive user. The model must create forward motion without the user driving. Score the 'overlong for the moment' minor and 'undercooked for the moment' minor especially carefully.",
    "physics_sycophancy": "This scene tests PHYSICS SYCOPHANCY — does the model bend reality to please the user or push back honestly? 'Convenient world' should be a major-flaw deduction whenever physics is broken to indulge.",
    "temporal_inconsistency": "This scene tests TEMPORAL REASONING under time pressure. 'Skipped time logic' is the primary risk — be especially strict about hour/minute/second tracking.",
    "over_explicit_subtext": "This scene tests SUBTEXT — does the model state what should be implied? 'Narrating emotions' and 'Missed subtext opportunity' are the primary failure modes.",
    "character_flattening": "This scene tests CHARACTER CONSISTENCY against bait. The character should hold their established voice/values, not flex to user pressure. 'Character break' is fatal whenever the established voice slips.",
    "genre_instability": "This scene tests GENRE STABILITY. The model must hold the established tone (horror, comedy, etc.) under pressure. 'Character break' or major-flaw 'flat NPC voice' deductions when tone slips.",
    "system_prompt_violation": "This scene's character card has STRICT RULES (speech patterns, style restrictions, forbidden topics). 'Wrong language/POV/tense' or 'character_break' should fire whenever the rules are broken, even subtly.",
    "system_prompt_detail_loss": "This scene's character card has CRITICAL DETAILS buried in a long system prompt (specific traits, allergies, relationships, rules). 'Character break' fires whenever a buried detail is contradicted or forgotten.",
    "pov_tense_violation": "This scene mandates a SPECIFIC POV/TENSE (usually 2nd person past). 'Wrong language/POV/tense' is fatal — quote the exact pronoun or tense slip.",
}


def load_seeds_meta() -> dict:
    """seed_id -> {failure_target, character_setting}."""
    if not SEEDS_FILE.exists():
        return {}
    seeds = json.load(open(SEEDS_FILE))
    return {
        s["id"]: {
            "failure_target": s.get("failure_target", ""),
            "character_setting": s.get("character_setting", ""),
        }
        for s in seeds
    }


def build_transcript(session: dict) -> str:
    """Build a transcript focused on character turns (the model under test).
    Includes user turns as context but tags them so the judge can ignore them.
    """
    lines = []
    char_name = session.get("character_name", "Character")
    user_name = session.get("user_name", "User")
    for msg in session["dialogue"]:
        role = msg.get("role")
        content = msg.get("content", "")
        if not content:
            continue
        if role in ("character", "assistant"):
            lines.append(f"--- {char_name} (model under test) ---\n{content}")
        elif role == "user":
            lines.append(f"--- {user_name} (user input — DO NOT score) ---\n{content}")
    return "\n\n".join(lines)


def load_done(path: Path) -> set:
    done = set()
    if not path.exists():
        return done
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
                done.add(r["session_id"])
            except Exception:
                pass
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--judge", default=DEFAULT_JUDGE)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    data = json.load(open(args.source))
    seeds_meta = load_seeds_meta()
    base_prompt = PROMPT_FILE.read_text()

    done = load_done(RAW_OUT)
    print(f"Already done: {len(done)} sessions")

    # Build work list — only sessions on adversarial seeds (the ones in seeds_meta)
    work = []
    for s in data["sessions"]:
        if "dialogue" not in s:
            continue
        sid = f'{s["test_model"]}::{s["seed_id"]}'
        if sid in done:
            continue
        meta = seeds_meta.get(s["seed_id"])
        if not meta:
            continue  # skip non-adversarial seeds we don't have metadata for
        work.append({"session": s, "session_id": sid, "meta": meta})

    if args.limit:
        work = work[:args.limit]

    print(f"Judge: {args.judge}")
    print(f"Source: {args.source}")
    print(f"Sessions to score: {len(work)}")
    print()

    if not work:
        return

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    errors = 0
    t0 = time.time()

    for i, w in enumerate(work):
        s = w["session"]
        meta = w["meta"]
        target = meta["failure_target"]
        primer = TARGET_PRIMERS.get(
            target,
            f"This scene tests for {target.replace('_', ' ')}. Look for flaws related to that.",
        )

        transcript = build_transcript(s)
        # Truncate if absurdly long (safety against runaway dialogue)
        if len(transcript) > 30000:
            transcript = transcript[:30000] + "\n\n[TRANSCRIPT TRUNCATED]"

        # Augmented prompt: base flaw hunter + failure-target context + strict JSON
        system_prompt = (
            base_prompt
            + "\n\n## Failure-Target Context for This Session\n\n"
            + primer
            + "\n\nApply the standard rubric, but weight the targeted failure mode more heavily when scoring."
            + "\n\n## CRITICAL: Strict JSON Output\n\n"
            + "Your entire response must be a single valid JSON object. Wrap quotes in proper string fields. NEVER include unquoted parentheticals, comments, or annotations inside or after string values. If you need to note something like 'appears multiple times', include it INSIDE the string: \"x... (appears multiple times)\" — never \"x...\" (appears multiple times)."
        )

        user_content = (
            f"Score this multi-turn RP session.\n\n"
            f"Character: {s.get('character_name', '?')}\n"
            f"User: {s.get('user_name', '?')}\n"
            f"Seed: {s['seed_id']}  (target: {target})\n\n"
            f"Transcript:\n\n{transcript}\n\n"
            f"Now produce the JSON. Find every flaw across the model's turns. "
            f"Do NOT score the user input lines."
        )

        try:
            resp = chat_completion(
                model=args.judge,
                system_prompt=system_prompt,
                user_content=user_content,
                config={"temperature": 0.1, "max_tokens": 3000},
            )
        except Exception as e:
            errors += 1
            print(f"[{i+1}/{len(work)}] ERR {w['session_id']}: {e}")
            if errors > 20:
                print("Too many errors. Stopping.")
                break
            continue

        # Parse JSON — model often wraps in ```json fences and occasionally
        # produces invalid JSON like `"quote" (note)` where the parenthetical
        # leaked outside the string. Try cleanup + regex repair.
        content = resp.get("content", "")
        parsed = None
        import re

        def attempt_parse(s):
            try:
                return json.loads(s.strip())
            except Exception:
                return None

        # Strip markdown fences
        cleaned = content.replace("```json", "").replace("```JSON", "").replace("```", "")
        candidates = [content, cleaned]
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            candidates.append(m.group(0))

        # Common repair patterns for invalid JSON the judge sometimes emits:
        # 1. `"text" (note),` -> `"text (note)",`  — trailing parenthetical leaked
        # 2. `"text" / "more text",` -> `"text / more text",`  — slash-joined quotes
        # 3. `"text" — "more text",` -> `"text — more text",`  — em-dash-joined
        repair_patterns = [
            (re.compile(r'"([^"]*?)"\s*\(([^)]*?)\)\s*([,\}\]])', re.DOTALL),
             r'"\1 (\2)"\3'),
            (re.compile(r'"([^"]*?)"\s*/\s*"([^"]*?)"\s*([,\}\]])', re.DOTALL),
             r'"\1 / \2"\3'),
            (re.compile(r'"([^"]*?)"\s*—\s*"([^"]*?)"\s*([,\}\]])', re.DOTALL),
             r'"\1 — \2"\3'),
        ]
        for base in [cleaned, m.group(0) if m else None]:
            if base is None:
                continue
            repaired = base
            for pat, repl in repair_patterns:
                repaired = pat.sub(repl, repaired)
            candidates.append(repaired)
            # Also try applying multiple times (in case of nested issues)
            for _ in range(3):
                prev = repaired
                for pat, repl in repair_patterns:
                    repaired = pat.sub(repl, repaired)
                if repaired == prev:
                    break
            candidates.append(repaired)

        for cand in candidates:
            parsed = attempt_parse(cand)
            if parsed:
                break
        if not parsed or "final_score" not in parsed:
            errors += 1
            print(f"[{i+1}/{len(work)}] PARSE-ERR {w['session_id']}")
            print(f"  raw response (first 200): {content[:200]!r}")
            print(f"  raw response (last 200): {content[-200:]!r}")
            print(f"  parsed: {parsed}")
            continue

        rec = {
            "session_id": w["session_id"],
            "model": s["test_model"],
            "seed": s["seed_id"],
            "failure_target": target,
            "starting_score": parsed.get("starting_score", 100),
            "final_score": parsed["final_score"],
            "n_fatal": len(parsed.get("fatal_flaws", [])),
            "n_major": len(parsed.get("major_flaws", [])),
            "n_minor": len(parsed.get("minor_flaws", [])),
            "n_bonus": len(parsed.get("bonuses", [])),
            "fatal_flaws": parsed.get("fatal_flaws", []),
            "major_flaws": parsed.get("major_flaws", []),
            "minor_flaws": parsed.get("minor_flaws", []),
            "bonuses": parsed.get("bonuses", []),
            "summary": parsed.get("summary", ""),
            "usage": resp.get("usage"),
            "judge": args.judge,
        }
        with open(RAW_OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")

        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(work) - i - 1) / rate if rate > 0 else 0
            cost = resp.get("usage", {}).get("cost", 0)
            print(f"  [{i+1}/{len(work)}]  {rate:.1f}/s  eta {eta/60:.0f}min  errors {errors}  last_score {parsed['final_score']}  last_cost ${cost:.4f}")

    print(f"\nDone. {errors} errors.")


if __name__ == "__main__":
    main()
