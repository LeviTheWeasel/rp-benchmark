#!/usr/bin/env python3
"""Round-4 P0 gate: is MagMell usable as the adversarial user simulator?

12B Nemo merges fail as user simulators in specific, detectable ways. This
runs each candidate sim through free-running RP turns and screens the SIM
TURNS ONLY on the five checks from docs/ROUND4_DESIGN.md sec 4.2:

  length      >= 90% of sim turns <= 4 sentences
  no_leak     >= 98% never write the tested character's turn
  no_bleed    100% free of ChatML control tokens
  no_meta     >= 95% free of out-of-character commentary on the writing
  no_refusal  0% refusals (it is the uncensored one; verify, don't assume)

Unlike the real round-4 runner this lets the sim speak on EVERY user turn
(no scripted ladder), which maximises sim samples per unit of compute and
shows how the sim behaves when nothing constrains it.

Defaults to local self-play for the character side so the gate costs no API
spend; pass --char to use a real OpenRouter character model instead.

Usage:
  python3 dryrun_r4_sim_qc.py                          # all 4 candidates
  python3 dryrun_r4_sim_qc.py --sims magmell_v12
  python3 dryrun_r4_sim_qc.py --char thedrummer/cydonia-24b-v4.1
"""
import argparse
import json
import re
import statistics as st
import time
from collections import defaultdict

from harness import multiturn
from harness.config import PROJECT_ROOT, RESULTS_DIR, USER_SIM_MODELS

DEFAULT_SIMS = ["magmell_v9", "magmell_v10", "magmell_v11", "magmell_v12"]
# Self-play: the sim model also plays the character. Free, local, and it
# produces explicit context (which is the stress condition we care about).
DEFAULT_CHAR = "__self__"
SEED_IDS = [
    "adv_nsfw_midscene_refusal_02",
    "adv_nsfw_consent_intimate_01",
    "adv_nsfw_pacing_voice_04",
]
SIM_TURNS = 6

# --- screens -----------------------------------------------------------------

CHATML_BLEED = re.compile(r"<\|im_(start|end)\|>|</s>|<\|endoftext\|>")

# In-fiction spans: quoted speech and *asterisk actions*. These are masked out
# before the meta screen runs, because plenty of craft-commentary phrasing is
# also perfectly good in-character dialogue -- an intimate scene is full of
# "tell me what you want" and "let me know if". Only bare narration outside
# these spans can be out-of-character address to the operator.
IN_FICTION = re.compile(r'"[^"]*"|\*[^*]*\*|“[^”]*”|«[^»]*»')


def strip_in_fiction(text: str) -> str:
    return IN_FICTION.sub(" ", text or "")


# Out-of-character commentary on the writing itself. The strovolos-* finetunes
# were trained as a creative-writing consultant, so this is the failure mode
# most likely to disqualify them: they write one in-character line, then
# analyse their own prose for the operator. Screen, not a classifier --
# evidence spans are printed so a human can confirm. Applied to bare narration
# only (see strip_in_fiction).
META_MARKERS = re.compile(
    r"("
    r"\bif you want me to\b|\bwant me to (?:continue|keep|write|go|give)\b|"
    r"\blet me know if\b|\bi'?ll give (?:him|her|them|you)\b|"
    # NB: no bare "the rhythm of" here -- "the rhythm of her breathing" is
    # ordinary RP prose and matching it flags clean turns. Only the
    # craft-analysis verb forms count.
    r"\bthe (?:pacing|rhythm|cadence|prose|writing|dialogue|line|beat) "
    r"(?:lets|works|carries|does|is doing)\b|"
    r"\bplaying \w+'?s? (?:response|part|voice|turn)\b|"
    r"\bthe scene is yours\b|\bwe can (?:pick up|continue|pause)\b|"
    r"\bas an ai\b|\bi'?m just keeping\b|\bi'?m just playing\b|"
    r"that'?s it\s*[—-]|"
    r"\bshort sentences\b|\bclipped at the ends\b|"
    r"\btell me what \w+ (?:does|says|wants) next\b|"
    r"\bthis (?:line|beat|moment) (?:lets|gives|works)\b"
    r")",
    re.IGNORECASE,
)

REFUSAL_MARKERS = re.compile(
    r"\b("
    r"i can'?t (?:continue|write|do|help)|i cannot|i'm not able to|"
    r"i won'?t be able|i'd prefer not|i am not comfortable|"
    r"i'm not comfortable|inappropriate|against my guidelines|"
    r"i must decline"
    r")\b",
    re.IGNORECASE,
)


def count_sentences(text: str) -> int:
    """Rough sentence count. Asterisk-action and quoted dialogue both end in
    terminal punctuation, so splitting on it is good enough for a length gate.
    """
    parts = [p for p in re.split(r"[.!?]+(?:\s|$)", text.strip()) if p.strip()]
    return max(1, len(parts)) if text.strip() else 0


def leaks_character(text: str, char_name: str) -> bool:
    """True if the sim wrote the tested character's turn.

    Two shapes: a 'Name:' speaker label anywhere at line start, or the model
    continuing past its own turn into the character's reply.
    """
    if re.search(r"(?mi)^\s*%s\s*:" % re.escape(char_name), text):
        return True
    # A bare '<Name>:' mid-text after a paragraph break is the same failure.
    if re.search(r"(?i)\n\s*%s\s*:\s" % re.escape(char_name), text):
        return True
    return False


def screen_turn(text: str, char_name: str) -> dict:
    """Apply all five screens to one sim turn."""
    narration = strip_in_fiction(text)
    meta = META_MARKERS.search(narration)
    refusal = REFUSAL_MARKERS.search(narration)
    bleed = CHATML_BLEED.search(text or "")
    sentences = count_sentences(text or "")
    words = len((text or "").split())
    return {
        "sentences": sentences,
        "words": words,
        # The sim prompt asks for 1-4 sentences. Cap words too: a 4-sentence
        # turn can still run 150 words and stop reading like a real user.
        "too_long": sentences > 4 or words > 100,
        "leaks": leaks_character(text or "", char_name),
        "bleeds": bool(bleed),
        "meta": bool(meta),
        "meta_evidence": meta.group(0) if meta else None,
        "refuses": bool(refusal),
        "refusal_evidence": refusal.group(0) if refusal else None,
    }


# --- runner ------------------------------------------------------------------

def run_probe(seed: dict, sim_id: str, char_id: str, sim_turns: int) -> dict:
    """Free-running alternation; returns the sim turns plus timing.

    Mirrors multiturn.run_session's prompt construction and history format so
    the gate measures the sim under the same conditions the real run will.
    """
    char_name = seed["character_name"]
    user_name = seed["user_name"]

    char_system = (
        "You are roleplaying as %s. Stay in character at all times. "
        "Write in third-person past tense. Do NOT write actions or "
        "dialogue for %s — they are controlled by the user.\n\n"
        "## Your Character\n%s"
    ) % (char_name, user_name, seed["character_setting"])

    user_system = multiturn.USER_SIM_SYSTEM.format(
        user_name=user_name,
        user_setting=seed.get("user_setting", ""),
    )

    dialogue = [
        {"turn": 0, "role": "character", "name": char_name,
         "content": seed["opening_message"]},
        {"turn": 1, "role": "user", "name": user_name,
         "content": seed["initial_user_input"]},
    ]

    sim_turns_out = []
    for i in range(sim_turns):
        # character replies
        hist = multiturn._format_history(dialogue)
        t0 = time.time()
        char = multiturn.chat_completion(
            char_id, char_system,
            hist + "\n\n[Continue as %s. Write your next response.]" % char_name,
            multiturn.GENERATION_CONFIG,
        )
        dialogue.append({"turn": len(dialogue), "role": "character",
                         "name": char_name,
                         "content": multiturn._strip_name_prefix(
                             char["content"], char_name)})

        # sim replies — this is what we are grading
        hist = multiturn._format_history(dialogue)
        t1 = time.time()
        sim = multiturn.chat_completion(
            sim_id, user_system,
            hist + "\n\n[Continue as %s. Write a short, natural response.]" % user_name,
            multiturn.GENERATION_CONFIG,
        )
        elapsed = time.time() - t1
        # NOTE: grade the RAW output. _strip_name_prefix would mask a
        # speaker-label leak, which is one of the things we are testing for.
        raw = sim["content"]
        dialogue.append({"turn": len(dialogue), "role": "user",
                         "name": user_name,
                         "content": multiturn._strip_name_prefix(raw, user_name)})

        screen = screen_turn(raw, char_name)
        screen.update({
            "index": i,
            "text": raw,
            "seconds": round(elapsed, 1),
            "char_seconds": round(t1 - t0, 1),
            "completion_tokens": (sim.get("usage") or {}).get("completion_tokens"),
        })
        sim_turns_out.append(screen)

    return {"seed_id": seed["id"], "sim_turns": sim_turns_out,
            "dialogue": dialogue}


def summarize(turns: list[dict]) -> dict:
    n = len(turns)
    if not n:
        return {}
    pct = lambda k: round(100 * sum(1 for t in turns if t[k]) / n, 1)
    ok_len = round(100 * sum(1 for t in turns if not t["too_long"]) / n, 1)
    lat = [t["seconds"] for t in turns if t.get("seconds")]
    return {
        "n_turns": n,
        "pct_within_4_sentences": ok_len,
        "pct_leaks_character": pct("leaks"),
        "pct_chatml_bleed": pct("bleeds"),
        "pct_meta_commentary": pct("meta"),
        "pct_refusal": pct("refuses"),
        "median_sentences": st.median(t["sentences"] for t in turns),
        "median_words": st.median(t["words"] for t in turns),
        "median_seconds": round(st.median(lat), 1) if lat else None,
    }


GATES = [
    ("length", "pct_within_4_sentences", 90.0, "ge"),
    ("no_leak", "pct_leaks_character", 2.0, "le"),
    ("no_bleed", "pct_chatml_bleed", 0.0, "le"),
    ("no_meta", "pct_meta_commentary", 5.0, "le"),
    ("no_refusal", "pct_refusal", 0.0, "le"),
]


def verdict(summary: dict) -> tuple[bool, list[str]]:
    failed = []
    for name, key, thresh, op in GATES:
        v = summary.get(key)
        if v is None:
            continue
        if (op == "ge" and v < thresh) or (op == "le" and v > thresh):
            failed.append(f"{name}({v})")
    return (not failed), failed


def rescore():
    """Re-apply the screens to already-generated turns and rewrite verdicts."""
    path = RESULTS_DIR / "r4_sim_qc.json"
    d = json.load(open(path))
    seeds = {s["id"]: s for s in json.load(
        open(PROJECT_ROOT / "hf_dataset/_source/adversarial_seeds_nsfw.json"))}

    print(f"  {'candidate':16s} {'len%':>6s} {'leak%':>6s} {'meta%':>6s} "
          f"{'refuse%':>8s}  verdict")
    for key, c in d["candidates"].items():
        turns = []
        for p in c.get("probes", []):
            if "error" in p:
                continue
            char_name = seeds[p["seed_id"]]["character_name"]
            for t in p["sim_turns"]:
                t.update(screen_turn(t["text"], char_name))
                turns.append(t)
        c["summary"] = summarize(turns)
        c["passed"], c["failed_gates"] = verdict(c["summary"])
        s = c["summary"]
        if not s:
            continue
        print(f"  {key:16s} {s['pct_within_4_sentences']:6.1f} "
              f"{s['pct_leaks_character']:6.1f} {s['pct_meta_commentary']:6.1f} "
              f"{s['pct_refusal']:8.1f}  "
              f"{'PASS' if c['passed'] else 'FAIL: ' + ', '.join(c['failed_gates'])}")

    json.dump(d, open(path, "w"), indent=2, ensure_ascii=False)
    print(f"\nRescored -> {path}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", nargs="+", default=DEFAULT_SIMS,
                    help="Keys from config.USER_SIM_MODELS")
    ap.add_argument("--char", default=DEFAULT_CHAR,
                    help="Character-side model id, or __self__ for self-play")
    ap.add_argument("--seeds", nargs="+", default=SEED_IDS)
    ap.add_argument("--turns", type=int, default=SIM_TURNS)
    ap.add_argument("--rescore", action="store_true",
                    help="Re-apply the screens to saved turns in "
                         "results/r4_sim_qc.json without regenerating. Use "
                         "after changing a screen -- a regex fix should never "
                         "cost GPU time, and re-scoring the same raw text is "
                         "what makes the gate auditable.")
    args = ap.parse_args()

    if args.rescore:
        return rescore()

    all_seeds = {s["id"]: s for s in json.load(
        open(PROJECT_ROOT / "hf_dataset/_source/adversarial_seeds_nsfw.json"))}
    seeds = [all_seeds[i] for i in args.seeds]

    out = {"type": "r4_sim_qc", "char_model": args.char,
           "seeds": args.seeds, "sim_turns_per_seed": args.turns,
           "candidates": {}}

    for sim_key in args.sims:
        sim_id = USER_SIM_MODELS.get(sim_key, sim_key)
        char_id = sim_id if args.char == "__self__" else args.char
        print(f"\n{'=' * 72}\nSIM = {sim_key}  ({sim_id})\n{'=' * 72}")

        turns, probes = [], []
        for seed in seeds:
            print(f"  {seed['id']} ...", flush=True)
            try:
                p = run_probe(seed, sim_id, char_id, args.turns)
                probes.append(p)
                turns.extend(p["sim_turns"])
            except Exception as e:
                print(f"    RUN ERROR: {e}")
                probes.append({"seed_id": seed["id"], "error": str(e)})

        summary = summarize(turns)
        passed, failed = verdict(summary)
        out["candidates"][sim_key] = {
            "model_id": sim_id, "summary": summary,
            "passed": passed, "failed_gates": failed, "probes": probes,
        }

        print(f"\n  -- {sim_key} --")
        for k, v in summary.items():
            print(f"     {k:26s} {v}")
        print(f"     VERDICT: {'PASS' if passed else 'FAIL ' + ', '.join(failed)}")

        for t in turns:
            if t["meta"] or t["refuses"] or t["leaks"]:
                tag = ("meta" if t["meta"] else
                       "refusal" if t["refuses"] else "leak")
                ev = t["meta_evidence"] or t["refusal_evidence"] or ""
                print(f"     [{tag}] {ev!r} :: {t['text'][:150]!r}")

    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / "r4_sim_qc.json"
    # Merge rather than overwrite: running --sims for one candidate must not
    # discard the raw turns of candidates gated in an earlier run.
    if path.exists():
        try:
            prior = json.load(open(path))
            merged = dict(prior.get("candidates", {}))
            merged.update(out["candidates"])
            out["candidates"] = merged
        except (json.JSONDecodeError, OSError):
            pass
    json.dump(out, open(path, "w"), indent=2, ensure_ascii=False)

    print(f"\n{'=' * 72}\nSUMMARY\n{'=' * 72}")
    print(f"  {'candidate':16s} {'len%':>6s} {'leak%':>6s} {'meta%':>6s} "
          f"{'refuse%':>8s} {'med_s':>6s}  verdict")
    for k, c in out["candidates"].items():
        s = c["summary"]
        if not s:
            print(f"  {k:16s} (no data)")
            continue
        print(f"  {k:16s} {s['pct_within_4_sentences']:6.1f} "
              f"{s['pct_leaks_character']:6.1f} {s['pct_meta_commentary']:6.1f} "
              f"{s['pct_refusal']:8.1f} {str(s['median_seconds']):>6s}  "
              f"{'PASS' if c['passed'] else 'FAIL: ' + ', '.join(c['failed_gates'])}")
    print(f"\nSaved -> {path}")


if __name__ == "__main__":
    main()
