#!/usr/bin/env python3
"""Production defects the craft rubric has no label for, measured mechanically.

Several flaw-hunter raters reported these independently and could not deduct for
them: the rubric's categories are all about craft, and these are generation and
harness faults. They are also the two defects on the unscoreable list that are
reliably detectable without a judge, so they are measured here instead of being
left as prose in the design doc.

  LEAK      harness scaffolding, chat-template tokens, or reasoning-block tags
            appearing inside the roleplay reply. The harness's own turn prompt
            ("[Continue as Noor. Write your next response.]") echoed back into
            the scene, or a bare </think>.
  SELFPLAY  the model writing the USER's character's turn under a speaker
            label, i.e. taking both sides of the conversation. This is an
            agency violation of a different order from writing one action, and
            a single -15 does not express it.
  LOOP      degenerate verbatim repetition -- the same sentence emitted many
            times in one turn. This was the most-reported unscoreable defect of
            the run: `recycled_description` is scoped to a phrase at -8, so a
            session where one block repeats 183 times costs about the same as
            one reusing an image twice. Measured as the share of a turn taken
            up by its single most repeated sentence.

Writes results/production_defects.json and prints a table.

Usage:
    python3 analyze_production_defects.py
"""
import json
import re
from collections import defaultdict
from pathlib import Path


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

SOURCES = _session_sources()

# Turns shorter than this are dropouts, not replies; counting them would
# deflate every rate by the same amount a model happened to time out.
MIN_CHARS = 50

LEAK = re.compile(
    r"\[\s*(continue|write your next|respond as|stay in character|do not write)"
    r"[^\]]{0,120}\]"                          # the harness turn prompt
    r"|<\|[a-z_]+\|>"                          # <|im_start|>, <|eot_id|>
    r"|</?think>|</?reasoning>|</?analysis>"   # reasoning-block tags
    r"|\[/?INST\]|<s>|</s>"                    # llama chat template
    r"|###\s*(Instruction|Response)\b", re.I)


# A turn is "looping" when one sentence, repeated, accounts for this much of
# it. Deliberate refrain (a horror beat returning three times in 4k chars) sits
# far below; a stuck decoder sits far above.
LOOP_SHARE = 0.25
SENT = re.compile(r"[^.!?\n]{25,400}[.!?]")


NGRAM = 8          # words
LOOP_SHARE = 0.35  # duplicate share of a turn's 8-grams


def loop_share(body):
    """Share of a turn's 8-grams that are repeats of one seen earlier.

    Three earlier versions of this were wrong, and the sequence is worth
    recording because each failure looked plausible:

      1. a sentence's share of the turn, with no repetition required -- lit up
         36 of 46 models, nearly every hit a count of one. It was measuring
         sentence length.
      2. exact SENTENCE repetition -- caught almost nothing, because what
         raters reported is a phrase recurring inside sentences whose
         surrounding words vary.
      3. the single most repeated 8-gram's coverage -- still near zero, because
         a 500-character block repeated sixty times contributes only ONE
         top-ranked n-gram; the other sixty-odd n-grams inside that block are
         each counted separately and none of them dominates.

    The property is total repeated MASS, so: what fraction of this turn's
    8-grams have been seen before in the same turn.
    """
    w = re.findall(r"[a-z']+", body.lower())
    if len(w) < 120:
        return 0.0
    grams = [tuple(w[i:i + NGRAM]) for i in range(len(w) - NGRAM + 1)]
    return 1.0 - (len(set(grams)) / len(grams))


def main():
    per = defaultdict(lambda: defaultdict(int))
    turns = defaultdict(int)
    billed = defaultdict(int)
    visible = defaultdict(int)
    examples = defaultdict(dict)
    worst = {}
    seen = set()

    for src in SOURCES:
        if not Path(src).exists():
            continue
        for s in json.load(open(src))["sessions"]:
            if "error" in s or "dialogue" not in s:
                continue
            sid = "%s::%s" % (s["test_model"], s["seed_id"])
            if sid in seen:
                continue
            seen.add(sid)
            model = s["test_model"]

            # The user character's own name is the label to look for. Taking it
            # from the seed rather than a fixed list keeps this working when
            # seeds are added.
            uname = (s.get("user_name") or "").strip().split()
            sp = (re.compile(r"(?m)^\s*%s\s*:" % re.escape(uname[0]))
                  if uname else None)

            for t in s["dialogue"]:
                if t.get("role") != "character" or not t.get("turn"):
                    continue
                body = t.get("content") or ""
                if len(body.strip()) < MIN_CHARS:
                    continue
                turns[model] += 1
                tk = t.get("tokens") or 0
                if tk:
                    billed[model] += tk
                    visible[model] += len(body.strip())
                g = LEAK.search(body)
                if g:
                    per[model]["leak"] += 1
                    examples[model].setdefault(
                        "leak", body[max(0, g.start() - 18):g.end() + 8]
                        .replace("\n", " ").strip())
                sh = loop_share(body)
                worst[model] = max(worst.get(model, 0.0), sh)
                if sh >= LOOP_SHARE:
                    per[model]["loop"] += 1
                    examples[model].setdefault(
                        "loop", "%.0f%% of one turn was a single sentence "
                        "on repeat" % (100 * sh))
                if sp:
                    h = sp.search(body)
                    if h:
                        per[model]["selfplay"] += 1
                        examples[model].setdefault(
                            "selfplay", body[max(0, h.start() - 10):h.end() + 40]
                            .replace("\n", " ").strip())

    # Billed output tokens per visible character. The baseline is taken from
    # the data rather than assumed: five models from five vendors cluster at
    # 0.219-0.221, which is the tokenizer floor for English prose, and
    # everything above it is output that is paid for and never read. An
    # earlier version assumed "4 chars per token" and produced negative
    # overheads for models whose tokenizer beats that guess.
    ratio = {m: (billed[m] / visible[m])
             for m in visible if visible[m] > 0 and turns[m] >= 50}
    base = sorted(ratio.values())[max(0, len(ratio) // 20)] if ratio else 1.0

    out = {"min_chars": MIN_CHARS, "token_baseline": round(base, 4),
           "per_model": {}}
    for m, n in turns.items():
        if n < 50:
            continue
        lk, sp_ = per[m]["leak"], per[m]["selfplay"]
        out["per_model"][m] = {
            "turns": n,
            "leak_turns": lk, "leak_rate": round(lk / n, 4),
            "selfplay_turns": sp_, "selfplay_rate": round(sp_ / n, 4),
            "loop_turns": per[m]["loop"],
            "loop_rate": round(per[m]["loop"] / n, 4),
            # One catastrophic turn is a worse user experience than a low rate
            # of mild ones, so the peak is reported alongside the rate.
            "loop_worst_turn": round(worst.get(m, 0.0), 4),
            "examples": examples[m],
            "tokens_per_char": round(ratio.get(m, 0), 4),
            "token_overhead_x": round(ratio.get(m, base) / base, 2),
        }

    rows = sorted(out["per_model"].items(),
                  key=lambda kv: -(kv[1]["leak_rate"] + kv[1]["selfplay_rate"]
                                   + kv[1]["loop_rate"]))
    print("PRODUCTION DEFECTS WITH NO RUBRIC LABEL")
    print("  %d turns over %d models\n" % (sum(turns.values()), len(rows)))
    print("  %-24s %8s %10s %7s %9s %7s"
          % ("model", "leak", "self-play", "loop", "worst turn", "turns"))
    dirty = 0
    for m, d in rows:
        if d["leak_turns"] + d["selfplay_turns"] + d["loop_turns"] == 0:
            continue
        dirty += 1
        print("  %-24s %7.1f%% %9.1f%% %6.1f%% %8.0f%% %7d"
              % (m, 100 * d["leak_rate"], 100 * d["selfplay_rate"],
                 100 * d["loop_rate"], 100 * d["loop_worst_turn"], d["turns"]))
    print("\n  clean on all three: %d of %d models" % (len(rows) - dirty, len(rows)))
    ov = sorted(((d["token_overhead_x"], m) for m, d in out["per_model"].items()),
                reverse=True)
    if ov:
        print("\n  BILLED-BUT-UNREAD OUTPUT  (baseline %.3f tok/char = the "
              "tokenizer floor)" % base)
        for x, m in ov[:6]:
            print("    %-24s %5.1fx" % (m, x))
        print("    median across the roster: %.1fx"
              % sorted(x for x, _ in ov)[len(ov) // 2])

    p = Path("results/production_defects.json")
    json.dump(out, open(p, "w"), indent=2)
    print("\nSaved: %s" % p)


if __name__ == "__main__":
    main()
