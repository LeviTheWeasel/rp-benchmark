#!/usr/bin/env python3
"""Rule-based craft proxy for every round-4 model, from transcripts already on disk.

Round 4 measures willingness and judgment. It says nothing about whether a model
WRITES well -- and round 3 showed those axes are orthogonal (the RP finetunes led
on willingness and came last on craft). So a leaderboard with J alone cannot
answer "which model should ship".

Only 7 of 33 round-4 models have the rounds 1/2 composite baseline; the 13 wave-2
and 4 wave-3 models have none, and most are not even in round 3. Running the full
composite for them is a separate, paid round. This is the part that costs nothing:
the objective metrics take no judge, so they run over the 654 transcripts already
generated.

WHAT THIS IS: cliche density, slop-pattern weight, vocabulary diversity, sentence
rhythm, and self-repetition -- the "can't be gamed by judge mood" quarter of the
benchmark's four scoring modes.

WHAT THIS IS NOT: the composite. No rubric, no flaw hunter, no pairwise ELO, no
human engagement. A model can score well here and still write badly; these
detectors catch mechanical tells, not whether a scene works. Treat it as a floor
check, not a craft ranking.

One deliberate control: only the TEST MODEL's turns are scored, never the
simulator's or the scripted rungs, and rungs are identical across models anyway.

Usage: python3 analyze_r4_craft_proxy.py
"""
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

import re
from collections import Counter

from harness.objective_metrics import compute_all, objective_score


# Both of these replace a length-dependent statistic with a length-stable one.
# objective_metrics.py is deliberately NOT touched: it computes the published
# rounds 1/2 numbers and has to keep reproducing them.

def repeat_fraction(text: str, window: int = 100) -> float:
    """Repeated-n-gram share measured inside a FIXED 100-word window.

    Three normalisations were tried and rejected before this one:
      raw count        rho +0.78 with reply length
      per 1k chars     rho +0.70
      token fraction   rho +0.75  (worse than per-1k)

    The differentiating test: WITHIN a single model, longer turns repeat more
    at rho +0.72 (median over 29 models) -- essentially the same as the +0.75
    seen BETWEEN models. So length drives the measure regardless of who wrote
    the text; it is an artifact, not a model property, and no scalar divisor
    fixes it because the growth is super-linear.

    Measuring inside a fixed window makes texts of different lengths
    comparable, the same fix MATTR applies to type-token ratio.
    """
    w = re.findall(r"\b[a-zA-Z']+\b", text.lower())
    if len(w) < 20:
        return 0.0

    def frac(ws):
        tot = rep = 0
        for n in (2, 3):
            grams = [" ".join(ws[i:i + n]) for i in range(len(ws) - n + 1)]
            if not grams:
                continue
            c = Counter(grams)
            tot += len(grams)
            rep += sum(v for v in c.values() if v >= 2)
        return rep / tot if tot else 0.0

    if len(w) <= window:
        return frac(w)
    step = max(1, window // 4)
    vals = [frac(w[i:i + window]) for i in range(0, len(w) - window + 1, step)]
    return sum(vals) / len(vals)


def mattr(text: str, window: int = 100) -> float:
    """Moving-average type-token ratio.

    Plain TTR falls mechanically as a text grows (the denominator outruns the
    numerator), so it ranked verbose models as having poorer vocabulary purely
    for being verbose -- correlation -0.53 with reply length. MATTR averages
    TTR over a fixed window, so texts of different lengths are comparable.
    """
    w = re.findall(r"\b[a-zA-Z']+\b", text.lower())
    if len(w) < window:
        return len(set(w)) / len(w) if w else 0.0
    vals = [len(set(w[i:i + window])) / window
            for i in range(0, len(w) - window + 1, max(1, window // 4))]
    return sum(vals) / len(vals)
from harness.slop_detectors import detect_all_slop
from harness.config import RESULTS_DIR
from harness.r4_private import load_r4

SRC = RESULTS_DIR / "r4_full_20260806_095625.json"


def main():
    # Track B replies are scored here too, and they are private text
    # (ROUND4_DESIGN sec 9). need_text: without the private companion the
    # proxy would silently become Track A only, so it refuses instead.
    d = load_r4(SRC, need_text=True)
    acc = defaultdict(lambda: {"obj": [], "slop": [], "cliche": [], "ttr": [],
                               "rhythm": [], "rep": [], "words": [], "n": 0})

    for s in d["sessions"]:
        if "error" in s:
            continue
        m = acc[s["test_model"]]
        for msg in s["dialogue"]:
            # test-model turns only: turn 0 is the seed opening, odd turns are
            # the simulator or a scripted rung.
            if msg.get("role") != "character" or msg.get("turn", 0) == 0:
                continue
            txt = msg.get("content") or ""
            if len(txt) < 40:
                continue
            met = compute_all(txt)
            m["obj"].append(objective_score(met)["objective_score"])
            m["cliche"].append(met["cliches"]["total_weight"] /
                               max(1, met["length"]) * 1000)
            m["ttr"].append(mattr(txt))
            # sentence_length_variance() omits rhythm_score entirely when a
            # reply has fewer than 3 sentences -- rhythm is undefined there, so
            # skip it rather than substituting a zero that would read as
            # "maximally monotonous".
            rh = met["sentence_rhythm"].get("rhythm_score")
            if rh is not None:
                m["rhythm"].append(rh)
            # Density, not the raw counter. objective_score() already
            # normalises repetition internally (bigram/trigram density); the
            # raw "score" field is an absolute count that grows with length,
            # so reporting it beside per-1k cliche and slop made a long reply
            # look repetitive purely for being long (rho +0.78 with length).
            # objective_metrics.py itself is NOT changed -- it computes the
            # published rounds 1/2 numbers and must keep reproducing them.
            m["rep"].append(repeat_fraction(txt))
            m["words"].append(met["word_count"])
            m["slop"].append(detect_all_slop(txt)["weight_per_1k_chars"])
            m["n"] += 1

    rows = []
    for model, m in acc.items():
        if m["n"] < 30:
            continue
        rows.append({
            "model": model, "n_turns": m["n"],
            "objective_score": round(st.mean(m["obj"]), 1),
            "cliche_per_1k": round(st.mean(m["cliche"]), 2),
            "slop_per_1k": round(st.mean(m["slop"]), 2),
            "vocab_mattr": round(st.mean(m["ttr"]), 3),
            "rhythm": (round(st.mean(m["rhythm"]), 3) if m["rhythm"] else None),
            "rhythm_n": len(m["rhythm"]),
            "repeat_fraction": round(st.mean(m["rep"]), 4),
            "median_words": round(st.median(m["words"])),
        })
    rows.sort(key=lambda r: -r["objective_score"])

    print("=" * 96)
    print("  ROUND 4 -- RULE-BASED CRAFT PROXY (no judge; from existing transcripts)")
    print("  NOT the rounds 1/2 composite. Mechanical tells only -- a floor check.")
    print("=" * 96)
    print(f"  {'#':>2s} {'model':22s} {'obj':>6s} {'cliche':>7s} {'slop':>6s} "
          f"{'vocab':>6s} {'rhythm':>7s} {'rep':>5s} {'words':>6s} {'turns':>6s}")
    print("  " + "-" * 92)
    for i, r in enumerate(rows, 1):
        print(f"  {i:2d} {r['model']:22s} {r['objective_score']:6.1f} "
              f"{r['cliche_per_1k']:7.2f} {r['slop_per_1k']:6.2f} "
              f"{r['vocab_mattr']:6.3f} "
              f"{(f'{r["rhythm"]:7.3f}' if r["rhythm"] is not None else '    n/a')} "
              f"{r['repeat_fraction']*100:5.1f} {r['median_words']:6d} {r['n_turns']:6d}")
    print("\n  obj = objective_score (100 minus deductions); higher is better")
    print("  cliche / slop = weighted hits per 1k chars; LOWER is better")
    print("  vocab = MATTR (window 100), length-stable; higher is better")
    print("  rep = % of bigram+trigram tokens that are repeats; LOWER is better")

    # Does craft relate to willingness at all, or is it orthogonal?
    try:
        lb = {r["model"]: r for r in json.load(
            open(RESULTS_DIR / "round4_willingness_leaderboard.json"))["leaderboard"]}
        pairs = [(r["objective_score"], lb[r["model"]]["J"])
                 for r in rows
                 if r["model"] in lb and lb[r["model"]]["J"] is not None]
        if len(pairs) >= 8:
            xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
            rx = {v: i for i, v in enumerate(sorted(set(xs)))}
            ry = {v: i for i, v in enumerate(sorted(set(ys)))}
            n = len(pairs)
            dsq = sum((rx[x] - ry[y]) ** 2 for x, y in pairs)
            rho = 1 - 6 * dsq / (n * (n * n - 1))
            print("\n" + "=" * 96)
            print(f"  CRAFT vs JUDGMENT: Spearman rho = {rho:+.3f} over {n} models")
            print("  Near zero means the two axes are independent -- a model cannot")
            print("  be chosen on either one alone, which is the whole argument for")
            print("  reporting them side by side rather than merging them.")
    except (OSError, KeyError):
        pass

    out = RESULTS_DIR / "round4_craft_proxy.json"
    json.dump({"round": 4, "source": SRC.name, "n_models": len(rows),
               "note": "Rule-based objective metrics only. NOT the rounds 1/2 "
                       "composite: no rubric, no flaw hunter, no pairwise ELO, "
                       "no human engagement. Mechanical tells, not scene quality.",
               "leaderboard": rows}, open(out, "w"), indent=2, ensure_ascii=False)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
