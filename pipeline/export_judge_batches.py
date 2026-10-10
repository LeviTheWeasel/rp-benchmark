#!/usr/bin/env python3
"""Export per-turn judging work as self-contained batches for subagent raters.

OpenRouter credit ran out mid-run, so the remainder has to be judged by a
different rater. That is a methodological change, not a plumbing one: 4233
checks already carry labels from claude-sonnet-4 at temperature 0, every one
of the 25 models is partially judged, and a second rater on the remainder
would leave each model's failure rate built from two different instruments.

So the first thing this exports is not work -- it is a CALIBRATION batch of
items that already have Sonnet labels, so agreement can be measured before any
new label is trusted. Round 4 has been through this twice (Jev, Laya) and both
times the number decided the question.

Usage:
  python3 pipeline/export_judge_batches.py --calibration 160
  python3 pipeline/export_judge_batches.py --remaining --batch-size 40
"""
import argparse, json, random
from pathlib import Path

from pipeline import judge_per_turn_failures as J
from lib.failure_modes_r5 import MODES as R5_MODES, build as r5_build


def _session_sources():
    """Every generation run on disk, newest last.

    Hardcoding dated filenames meant a new craft-baseline or round-4 run
    silently never reached the judges: the file exists, the models are in it,
    and every downstream script keeps reporting the old roster as complete.
    Globbing makes a new run visible the moment it lands.
    """
    import glob as _g
    from pathlib import Path as _P
    # NEWEST FIRST, and that ordering is load-bearing.
    #
    # Every consumer dedupes by session_id with "first wins". With files in
    # ascending date order, re-running a model to repair a broken run would
    # write a newer file whose sessions were then silently discarded in favour
    # of the broken ones -- the re-run costs money and changes nothing, and
    # the coverage number it was meant to fix stays exactly where it was.
    #
    # Round-4 ladder files are deliberately excluded: the flaw hunter and the
    # eleven per-turn modes are defined over the adversarial seeds, not the
    # willingness rungs, and pulling r4 in here would silently change the
    # 876-session denominator they are all reported against.
    out = sorted(_g.glob("results/craft_baseline_*.json"), reverse=True)
    out.append("results/multiturn_merged_all_v2.json")
    return [p for p in out if _P(p).exists()]

OUT = Path("/tmp/claude-1000/-home-levi-ST-VAUDEVILLE/0e0eeb99-f00a-4b4d-87ff-9f01392fa806/scratchpad/judge_batches")
# All three, because the cards show all 46 models on one page and a single
# rater has to cover the lot. The rounds 1/2 transcripts are read here, not
# rewritten -- the old rounds' own published numbers are untouched.
SOURCES = _session_sources()
HISTORY_CHARS = 1800


def load_seeds():
    seeds = {}
    for f in ("adversarial_seeds.json", "adversarial_seeds_v2.json",
              "adversarial_seeds_v3_bigcard.json"):
        p = Path("hf_dataset/_source") / f
        if p.exists():
            for s in json.load(open(p)):
                seeds[s["id"]] = s
    return seeds


def build_items(seeds, done_keys, want_done):
    """Every (session, turn, mode) triple, with its prompt already rendered.

    want_done=True yields items that ALREADY have a Sonnet label (calibration);
    False yields the unjudged remainder.
    """
    items = []
    for src in SOURCES:
        if not Path(src).exists():
            continue
        for s in json.load(open(src))["sessions"]:
            # "dialogue" only. The old guard also required a "judges" block,
            # which was a proxy for "a finished session" back when every run
            # judged inline. Since judging moved to subscription subagents the
            # runners write no judges key at all, so that guard silently
            # excluded every session generated after the change -- 23 models
            # had flaw and session scores but no per-turn data, and their
            # cards could not be built.
            if "dialogue" not in s:
                continue
            seed_obj = seeds.get(s["seed_id"])
            by_turn = {c["turn"]: c for c in (seed_obj or {}).get("challenge_turns", [])}
            sid = "%s::%s" % (s["test_model"], s["seed_id"])
            dlg = s["dialogue"]
            for i, msg in enumerate(dlg):
                if msg.get("role") not in ("character", "assistant"):
                    continue
                turn = msg.get("turn")
                content = msg.get("content")
                if not turn or not content or len(content) < 50:
                    continue
                for mode, sids in J.MODE_SEEDS.items():
                    if s["seed_id"] not in sids:
                        continue
                    if ((sid, turn, mode) in done_keys) != want_done:
                        continue
                    char = s.get("character_name", "Character")
                    user = s.get("user_name", "User")
                    if mode in R5_MODES:
                        prev = dlg[i - 1] if i else None
                        if not prev or not prev.get("is_challenge"):
                            continue
                        spec = by_turn.get((prev["turn"] // 2) + 1)
                        if not spec or not spec.get("trap"):
                            continue
                        needs = R5_MODES[mode]["needs"]
                        prompt = r5_build(
                            mode, R5_MODES[mode], char, user, spec["trap"],
                            prev["content"], content,
                            card=(seed_obj or {}).get("character_setting")
                            if "card" in needs else None,
                            history="\n\n".join(
                                "%s: %s" % (x["name"], (x["content"] or "")[:300])
                                for x in dlg[:i])[-HISTORY_CHARS:]
                            if "history" in needs else None)
                    else:
                        kw = dict(char=char, user=user, response=content)
                        if mode == "F2_pov_tense":
                            kw["card"] = (seed_obj or {}).get("character_setting") or "(not supplied)"
                        prompt = J.PROMPTS[mode].format(**kw)
                    items.append({"session_id": sid, "model": s["test_model"],
                                  "seed": s["seed_id"], "turn": turn,
                                  "mode": mode, "prompt": prompt})
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibration", type=int)
    ap.add_argument("--modes", nargs="+", help="restrict to these modes")
    ap.add_argument("--remaining", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="every check in the corpus, for a single-rater re-judge")
    ap.add_argument("--batch-size", type=int, default=40)
    ap.add_argument("--redo-scored", action="store_true",
                    help="re-export checks the v2 file already has")
    args = ap.parse_args()

    seeds = load_seeds()
    done = {}
    for line in open("results/per_turn_failures.jsonl"):
        r = json.loads(line)
        done[(r["session_id"], r["turn"], r["mode"])] = r["is_failure"]

    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.json"):
        f.unlink()

    if args.calibration:
        items = build_items(seeds, set(done), want_done=True)
        random.seed(11)
        random.shuffle(items)
        # Stratify by mode: F1 and F2 alone are 70% of the corpus, and a random
        # draw would measure agreement on those two and little else.
        if args.modes:
            items = [it for it in items if it["mode"] in args.modes]
        by_mode = {}
        for it in items:
            by_mode.setdefault(it["mode"], []).append(it)
        per = max(1, args.calibration // len(by_mode))
        picked = []
        for mode, group in by_mode.items():
            picked += group[:per]
        # The reference label goes to a SEPARATE file the rater never opens.
        # Writing it into the batch would have handed the answer to the judge
        # being tested -- an agreement number measured that way says nothing.
        answers = {"%s|%s|%s" % (it["session_id"], it["turn"], it["mode"]):
                   done[(it["session_id"], it["turn"], it["mode"])] for it in picked}
        (OUT.parent / "cal_answers.json").write_text(json.dumps(answers, indent=1))
        items = picked
        tag = "cal"
    elif args.all:
        # The whole corpus under one rater. Sonnet's labels are kept in the
        # original file rather than overwritten: they stay usable as a second
        # rater for agreement, and nothing already paid for is thrown away.
        items = (build_items(seeds, set(done), want_done=False)
                 + build_items(seeds, set(done), want_done=True))
        # Drop checks the single-rater file already carries. Without this the
        # whole corpus re-exports every run, and after the roster grew the
        # 4746 settled checks would have shipped again alongside the new ones.
        # Same skip the flaw and session exporters needed; this one is third.
        v2 = Path("results/per_turn_failures_v2.jsonl")
        if v2.exists() and not args.redo_scored:
            scored = set()
            for line in open(v2):
                if line.strip():
                    r = json.loads(line)
                    scored.add((r["session_id"], r["turn"], r["mode"]))
            before = len(items)
            items = [it for it in items
                     if (it["session_id"], it["turn"], it["mode"]) not in scored]
            print("  skipped %d check(s) already scored by the single rater"
                  % (before - len(items)))
        tag = "work"
    else:
        items = build_items(seeds, set(done), want_done=False)
        tag = "work"

    n = 0
    for i in range(0, len(items), args.batch_size):
        batch = items[i:i + args.batch_size]
        (OUT / ("%s_%03d.json" % (tag, n))).write_text(json.dumps(batch, indent=1))
        n += 1
    print("wrote %d %s items in %d batches -> %s" % (len(items), tag, n, OUT))
    if tag == "cal":
        from collections import Counter
        print("  modes:", dict(Counter(it["mode"] for it in items)))
        print("  reference labels held back in cal_answers.json (not in the batches)")


if __name__ == "__main__":
    main()
