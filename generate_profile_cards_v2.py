#!/usr/bin/env python3
"""Per-model profile cards, round-4 era: eleven failure modes plus willingness.

What changed from generate_profile_cards.py:

  * ELEVEN failure modes, not two. Round 3 shipped F1/F2 and showed the other
    nine as rubric means, which is why those cells read ~4.5 for every model.

  * Sample size is shown, not hidden. Nine of the eleven modes give a model
    2-9 observations, so a percentage there is a lie told in three significant
    figures: 2/2 is printed as "2/2", never as "100.0%". Only modes with
    n >= 25 get a rate, a CI and a bar.

  * A POOLED trap-mode rate carries the per-model craft signal instead. It is
    legitimate only because every model meets the identical mode mix -- verified
    in the audit (13 models, same per-mode counts). Models that miss any trap
    mode are excluded from it rather than silently compared on a smaller basket.

  * A WILLINGNESS block for models in the round-4 roster.

Usage: python3 generate_profile_cards_v2.py [--model KEY] [--limit N]
"""
import argparse, json, math, re, subprocess, sys, textwrap
from collections import defaultdict
from pathlib import Path

from generate_profile_cards import (wilson_ci, derive_strength_weakness,
                                    MODE_LABELS)

R = Path("results")
TRAP_MODES = ["F3_system_prompt_violation", "F4_detail_loss",
              "F5_contradictory_context", "F6_narrative_stagnation",
              "F7_physics_sycophancy", "F8_temporal_inconsistency",
              "F9_over_explicit_subtext", "F10_character_flattening",
              "F11_genre_instability"]
STANDING_MODES = ["F1_agency", "F2_pov_tense"]
LABELS = {
    "F1_agency": "Agency violations", "F2_pov_tense": "POV/tense breaks",
    "F3_system_prompt_violation": "System-prompt violations",
    "F4_detail_loss": "Detail loss", "F5_contradictory_context": "Contradiction mishandled",
    "F6_narrative_stagnation": "Narrative stagnation",
    "F7_physics_sycophancy": "Physics sycophancy",
    "F8_temporal_inconsistency": "Temporal inconsistency",
    "F9_over_explicit_subtext": "Subtext made explicit",
    "F10_character_flattening": "Character flattening",
    "F11_genre_instability": "Genre instability",
}
CONTINUUM = {"F5_contradictory_context", "F9_over_explicit_subtext"}
# The full craft-baseline roster: 10 seeds x 22 turns.
FULL_ROSTER_TURNS = 220
TURNS_PER_SEED = 22
MIN_N_FOR_RATE = 25


def load_verdicts(path=None):
    """Curated editorial copy; review it whenever benchmark evidence changes."""
    path = path if path is not None else R / "model_card_verdicts.json"
    verdicts = json.loads(Path(path).read_text(encoding="utf-8"))["models"]
    if not isinstance(verdicts, dict) or not verdicts:
        raise ValueError("Editorial verdicts must be a non-empty model mapping")
    for model, verdict in verdicts.items():
        if not isinstance(verdict, str) or not verdict.strip() or "\n" in verdict:
            raise ValueError(f"Invalid editorial verdict for {model}")
    return verdicts


def format_verdict(model, verdicts):
    if model not in verdicts:
        raise ValueError(f"Missing editorial verdict for {model}; review the new card")
    return textwrap.fill("Verdict: " + verdicts[model], width=78,
                         subsequent_indent="  ", break_long_words=False,
                         break_on_hyphens=False)


SUBJ_LO, SUBJ_HI, SUBJ_W = 1.0, 5.0, 30
SUBJ_PAD = 0.3


def subj_band(mean):
    """A +/-0.3 band on the rubric's own 1-5 axis, drawn like the flaw band.

    0.3 is the measured disagreement between judges at the MODEL level once
    their different use of the scale is removed: 0.24 across the top band,
    0.30 across the rest. It is not a sampling error -- averaging more
    sessions does not shrink it, because it is systematic per model.

    Per-session the two judge families differ by a median of 0.90 raw, but
    most of that is a compression (chatgpt = 0.52 + 0.61 x sonnet) rather than
    disagreement about which sessions are good, so the raw figure would
    overstate the band.
    """
    lo, hi = mean - SUBJ_PAD, mean + SUBJ_PAD
    span = SUBJ_HI - SUBJ_LO

    def col(v):
        return max(0, min(SUBJ_W - 1,
                          int(round((v - SUBJ_LO) / span * (SUBJ_W - 1)))))

    cells = ["░"] * SUBJ_W
    for i in range(col(lo), col(hi) + 1):
        cells[i] = "█"
    return "%.0f %s %.0f" % (SUBJ_LO, "".join(cells), SUBJ_HI)


FLAW_LO, FLAW_HI, FLAW_W = -20, 100, 30
FLAW_PAD = 10


def flaw_band(mean):
    """A +/-10 interval drawn on a fixed -20..100 axis, with no figure.

    The axis is fixed across every card so bands can be compared by eye; it
    starts below zero because the scale has no floor and six models sit there.
    """
    lo, hi = mean - FLAW_PAD, mean + FLAW_PAD
    span = FLAW_HI - FLAW_LO

    def col(v):
        return max(0, min(FLAW_W - 1,
                          int(round((v - FLAW_LO) / span * (FLAW_W - 1)))))

    a, b = col(lo), col(hi)
    cells = ["░"] * FLAW_W
    for i in range(a, b + 1):
        cells[i] = "█"
    zero = col(0)
    if cells[zero] == "░":
        cells[zero] = "│"
    return "%d %s %d" % (FLAW_LO, "".join(cells), FLAW_HI)


def bar(rate, width=12, full=0.5):
    f = int(min(rate / full, 1) * width)
    return "█" * f + "░" * (width - f)


def load_r4():
    """Round-4 willingness rows, read back from the analyzer's own run.

    The analyzer is re-run and the JSON it reports writing is read back, so
    there is one definition of J in the codebase. A second implementation
    here would drift from it silently, which is exactly how the round-3
    refusal axis came to read 0% for 33 models.

    This used to parse the stdout table, which broke twice: the reduced-sample
    "*" token shifted every later column one place, and since 2026-09-25 an
    unranked row prints "--" where its rank goes, which dropped the whole
    block from mistral_small_2603 and mercury_2_5 without a word. The JSON
    also carries what the table has no room for: rank, the n behind each
    rate, and held_under_pressure with its note.

    A failed run raises. Returning nothing would write every card without
    its willingness block, which reads as "not tested".
    """
    run = subprocess.run([sys.executable, "analyze_round4_willingness.py"],
                         capture_output=True, text=True, timeout=600)
    wrote = re.search(r"^wrote (.+round4_willingness_leaderboard\.json)$",
                      run.stdout, re.M)
    if run.returncode or not wrote:
        raise RuntimeError("analyze_round4_willingness.py failed (exit %d):\n%s"
                           % (run.returncode, run.stderr[-2000:]))
    data = json.loads(Path(wrote.group(1)).read_text(encoding="utf-8"))
    res = {r["model"]: dict(r) for r in data["leaderboard"]}
    n_ranked = sum(1 for r in res.values() if r["ranked"])
    for r in res.values():
        r["n_ranked"] = n_ranked
    for t in data.get("j_ties", []):
        for m in t["models"]:
            res[m]["tied_with"] = [o for o in t["models"] if o != m]
    flagged = None
    for line in run.stdout.splitlines():
        # The analyzer's own warning for empty replies that climb with the
        # rung (>= 20% empty and >= 25 points from rung 1 to rung 5). Read
        # back from its stdout rather than re-tested, so the threshold stays
        # in one place.
        mo = re.match(r"\s+(\S+)\s+(\d+)% empty, rung1 -> rung5 ([+-]\d+) points$",
                      line)
        if mo and mo.group(1) in res:
            flagged = res[mo.group(1)]
            flagged["empty"] = "%s%% of Track A, rung 1 -> 5 %s points" % (
                mo.group(2), mo.group(3))
            continue
        if flagged is not None and line.strip().startswith("by subtrack:"):
            t = line.split(":", 1)[1].split()
            by = dict(zip(t[::2], t[1::2]))
            flagged["empty_by"] = " / ".join(
                "%s %s" % (k, by[k]) for k in sorted(by, key=lambda k: k != "intimacy"))
            flagged = None
    return res


def kappa_from_note(note):
    """(kappa, bar) as the analyzer's held_under_pressure_note states them.

    Quoted from the note, not restated here: the analyzer re-checks that
    figure against the Jev files on every run and warns if it drifts.
    """
    mo = re.search(r"kappa at turn \d+ is ([\d.]+).*?below the ([\d.]+) bar",
                   note or "")
    return (mo.group(1), mo.group(2)) if mo else (None, None)


def willingness_block(d):
    """The round-4 lines of a card, from one row of the analyzer's JSON.

    J is on the first ask only. The second push is its own line, marked as
    outside J, with the rater agreement that keeps it out.
    """
    f = lambda v: "n/a" if v is None else "%.2f" % v
    L = ["\nWILLINGNESS / JUDGMENT (round 4)"]
    L.append("  %-26s %s   (held at first ask − over-refusal)"
             % ("Youden's J", f(d["J"])))
    if d["ranked"]:
        L.append("  %-26s %d of %d" % ("Rank by J", d["rank"], d["n_ranked"]))
        if d.get("tied_with"):
            L.append("    Tied on J with %s (order arbitrary)."
                     % ", ".join(d["tied_with"]))
    elif (d["unranked_reason"] or "").startswith("insufficient data"):
        L.append("  %-26s not ranked: insufficient Track A data (%d usable)"
                 % ("Rank by J", d["usable_exchanges_a"]))
    else:
        L.append("  %-26s not ranked: %s" % ("Rank by J", d["unranked_reason"]))
    n = d["held_first_n"]
    if n:
        # Shown as a count too: with 4 first asks one exchange is 0.25.
        L.append("  %-26s %s   (%d of %d usable first asks)"
                 % ("Held at first ask", f(d["held_line_rate"]),
                    round(d["held_line_rate"] * n), n))
    else:
        L.append("  %-26s n/a    (no B-hard run)" % "Held at first ask")
    L.append("  %-26s %s   (L3-L5, Jev-gated)"
             % ("Over-refusal", f(d["over_refusal_hard_rungs"])))
    # The subtrack split is over every rung and ungated, so it is labelled:
    # beside the L3-L5 line above, deepseek_v4_flash reads 0.54 overall
    # against 0.42 / 0.16, which looks like arithmetic gone wrong.
    L.append("  Over-refusal by subtrack   intimacy %s / gore %s   (L1-L5, ungated)"
             % (f(d["over_refusal_intimacy"]), f(d["over_refusal_gore"])))
    pn = d["held_under_pressure_n"]
    if pn:
        L.append("  %-26s %s   (%d of %d first-ask holds kept at turn 4)"
                 % ("Held under pressure", f(d["held_under_pressure"]),
                    pn - d["folds_under_pressure"], pn))
        gap = round(d["held_line_rate"] * n) - pn
        if gap > 0:
            L.append("    %d more first-ask hold%s no usable turn-4 reply."
                     % (gap, " has" if gap == 1 else "s have"))
    elif n:
        L.append("  %-26s n/a    (no first ask held, nothing to push on)"
                 % "Held under pressure")
    if pn:
        k, bar_ = kappa_from_note(d.get("held_under_pressure_note"))
        L.append("    Not in J: %s" % (
            "rater kappa %s on the second push, below the %s bar." % (k, bar_)
            if k else "raters agree less on the second push than the first."))
    L.append("  Policy compliance          %s        Overshoot %s"
             % (f(d["policy_compliance_rate"]), f(d["overshoot_rate"])))
    if d.get("empty"):
        L.append("  %-26s %s" % ("Empty replies", d["empty"]))
        if d.get("empty_by"):
            L.append("  %-26s %s" % ("", d["empty_by"]))
        L.append("    They climb with the ask, so they read as refusals by silence.")
        L.append("    J drops them as no signal and is scored on the replies given.")
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model"); ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    verdicts = load_verdicts()

    # v2 is the single-rater corpus: all 4746 checks by one instrument under
    # the corrected F3/F5 rubrics. The Sonnet pass stays in the original file
    # as a second rater -- it covered only part of the corpus and two of its
    # rubrics have since been rewritten, so mixing the two would build each
    # model's rate from two instruments. Measured cost of that mixing: pooled
    # kappa 0.565, with F3 and F5 diverging in opposite directions.
    src = R / "per_turn_failures_v2.jsonl"
    if not src.exists():
        src = R / "per_turn_failures.jsonl"
    fails = [json.loads(l) for l in open(src)]
    beh = json.load(open(R / "behavioral_metrics.json"))
    # Prefer the single-judge re-score, same rule as the flaw summary above.
    prof_path = R / "model_profiles_v2.json"
    if not prof_path.exists():
        prof_path = R / "model_profiles.json"
    prof = json.load(open(prof_path))
    bay = json.load(open(R / "community_arena_bayesian.json"))
    # Prefer the single-rater re-score, same as per_turn_failures_v2 above.
    # The Sonnet summary stays on disk as the second rater.
    fh_path = R / "flaw_hunter_session_summary_v2.json"
    if not fh_path.exists():
        fh_path = R / "flaw_hunter_session_summary.json"
    fh = json.load(open(fh_path))
    r4 = load_r4()
    # Coverage gates the whole card. Every other metric silently drops the
    # turns a model never answered, so a model that mostly stays silent scores
    # like a good one on a tiny denominator -- tencent_hy4 answered 9 of 220
    # turns and read as ordinary. See compute_coverage.py.
    # Generation/harness faults the craft rubric has no label for. Several
    # raters reported these and could deduct nothing for them.
    pd_path = R / "production_defects.json"
    pdef = json.load(open(pd_path))["per_model"] if pd_path.exists() else {}
    cov_path = R / "model_coverage.json"
    cov = json.load(open(cov_path))["per_model"] if cov_path.exists() else {}

    rates = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))  # n, k, borderline
    for r in fails:
        c = rates[r["model"]][r["mode"]]
        c[0] += 1
        c[1] += bool(r["is_failure"])
        c[2] += (r.get("verdict") == "borderline")

    # Pooled trap rate -- only for models carrying every trap mode.
    pooled = {}
    for m, modes in rates.items():
        if not all(mo in modes for mo in TRAP_MODES):
            continue
        n = sum(modes[mo][0] for mo in TRAP_MODES)
        k = sum(modes[mo][1] for mo in TRAP_MODES)
        pooled[m] = (k, n)
    pool_rank = sorted(pooled, key=lambda m: pooled[m][0] / pooled[m][1])

    bay_by = {e["model"]: e for e in bay["leaderboard"]}
    pop = {k: v["mean"] for k, v in beh["population"].items()}
    mode_pool = defaultdict(set)
    for mk, p in prof.items():
        for mo in p.get("failure_modes", {}): mode_pool[mo].add(mk)
    mode_pool = {k: len(v) for k, v in mode_pool.items()}

    models = sorted(rates, key=lambda m: (-(bay_by.get(m, {}).get("elo_mean") or 0), m))
    if args.model: models = [m for m in models if m == args.model]
    if args.limit: models = models[:args.limit]

    out = []
    for m in models:
        L = []
        c = cov.get(m)
        L.append(f"Model: {m}")
        L.append("─" * 78)
        L.append("\n" + format_verdict(m, verdicts))
        if c:
            note = ("   <-- EXCLUDED FROM RANKING: too few answered turns to compare"
                    if c["excluded"] else "")
            L.append("\nRESPONSE COVERAGE   %5.1f%%  (%d of %d turns answered)%s"
                     % (100 * c["coverage"], c["answered"], c["turns"], note))
            if c["excluded"]:
                L.append("  Every rate below is computed over the answered turns only,")
                L.append("  so it describes a small and non-random slice of this model.")
            # Coverage is an ANSWER RATE, not a sample size. A model asked two
            # seeds and answering both reads 100% and passes the exclusion
            # gate, sitting on the card beside models run over ten. The full
            # roster is 220 turns; say so when this model did not get it.
            if c["turns"] < FULL_ROSTER_TURNS:
                L.append("  Sample: %d of the roster's %d turns (~%d of %d seeds)."
                         % (c["turns"], FULL_ROSTER_TURNS,
                            round(c["turns"] / TURNS_PER_SEED),
                            round(FULL_ROSTER_TURNS / TURNS_PER_SEED)))
                L.append("  A high coverage here means it answered what it was")
                L.append("  asked, not that it was asked much.")

        L.append("\nFAILURE MODES — measured per model (n ≥ %d)" % MIN_N_FOR_RATE)
        for mo in STANDING_MODES:
            if mo not in rates[m]: continue
            n, k, _ = rates[m][mo]
            if n < MIN_N_FOR_RATE: continue
            lo, hi = wilson_ci(k, n)
            L.append("  %-26s %5.1f%%  [%4.1f–%4.1f]  %s  %d probes"
                     % (LABELS[mo], 100 * k / n, 100 * lo, 100 * hi, bar(k / n, full=0.25), n))

        if m in pooled:
            k, n = pooled[m]
            lo, hi = wilson_ci(k, n)
            rk = pool_rank.index(m) + 1
            L.append("\nTRAP-MODE FAILURE RATE (pooled over 9 modes)")
            L.append("  %-26s %5.1f%%  [%4.1f–%4.1f]  %s  %d/%d"
                     % ("Pooled", 100 * k / n, 100 * lo, 100 * hi, bar(k / n), k, n))
            L.append("  rank %d of %d models carrying all nine modes" % (rk, len(pooled)))

        L.append("\n  per-mode detail — counts, not rates: 2-9 probes each, so a")
        L.append("  percentage here would not survive one probe changing")
        for mo in TRAP_MODES:
            if mo not in rates[m]:
                L.append("  %-26s  not run" % LABELS[mo]); continue
            n, k, b = rates[m][mo]
            extra = "  (+%d borderline)" % b if mo in CONTINUUM and b else ""
            L.append("  %-26s  %d/%d failed%s" % (LABELS[mo], k, n, extra))

        if m in r4:
            L.extend(willingness_block(r4[m]))

        b = beh["per_model"].get(m, {})
        if b:
            L.append("\nBEHAVIORAL")
            for met, lab in (("word_count", "Avg words"),
                             ("unique_word_ratio", "Unique-word ratio"),
                             ("bigram_repetition", "Phrase repetition")):
                if met not in b: continue
                v = b[met]["mean"]; pv = pop.get(met, 0)
                mark = ""
                if met == "bigram_repetition": mark = " ↑" if v > pv * 1.2 else ""
                elif met == "unique_word_ratio": mark = " ↓" if v < pv * 0.9 else ""
                L.append("  %-26s %8.3f   (population %.3f)%s" % (lab, v, pv, mark))

        if m in fh.get("per_model", {}):
            d = fh["per_model"][m]
            L.append("\nFLAW HUNTER  [%s]" % ("single-rater v2"
                     if fh_path.name.endswith("_v2.json") else "claude_sonnet"))
            top = ", ".join(f["flaw"].split(":")[-1] for f in d.get("top_flaws", [])[:3])
            # Shown as an interval, never a figure. Two raters on the same
            # rubric and the same session differ by a median of 14 points
            # (cross-rater r = +0.20), and per-rater calibration has sd 7.8
            # after model and seed effects are removed. A printed mean invites
            # a comparison the instrument cannot support, so the card renders
            # the band and lets overlapping bands read as "not separable".
            L.append("  %-26s %s" % ("Craft band", flaw_band(d["mean"])))
            L.append("  %-26s %s" % ("", "±10 is the rater noise floor, "
                                          "not a sampling error"))
            L.append("  %-26s %d" % ("Sessions", d.get("n", 0)))
            if top:
                L.append("  %-26s %s" % ("Top flaws", top))

        d = pdef.get(m)
        if d:
            L.append("\nPRODUCTION DEFECTS  [mechanical, not judged]")
            if d["leak_turns"] or d["selfplay_turns"] or d.get("loop_turns"):
                L.append("  %-26s %7.1f%%   (%d of %d turns)"
                         % ("Scaffolding/token leak", 100 * d["leak_rate"],
                            d["leak_turns"], d["turns"]))
                L.append("  %-26s %7.1f%%   (%d of %d turns)"
                         % ("Wrote the user's turn", 100 * d["selfplay_rate"],
                            d["selfplay_turns"], d["turns"]))
                L.append("  %-26s %7.1f%%   worst turn %.0f%% repeated"
                         % ("Degenerate repetition",
                            100 * d.get("loop_rate", 0),
                            100 * d.get("loop_worst_turn", 0)))
                if d.get("token_overhead_x"):
                    L.append("  %-26s %6.1fx    billed per visible char, "
                             "vs the prose floor" % ("Token overhead",
                                                     d["token_overhead_x"]))
                ex = d.get("examples") or {}
                for k in ("leak", "selfplay"):
                    if ex.get(k):
                        L.append("    %s: %s" % (k, ex[k][:72]))
            else:
                L.append("  %-26s %s" % ("None detected",
                                         "%d turns clean" % d["turns"]))
            if d.get("token_overhead_x") and not (
                    d["leak_turns"] or d["selfplay_turns"] or d.get("loop_turns")):
                L.append("  %-26s %6.1fx    billed per visible char, "
                         "vs the prose floor" % ("Token overhead",
                                                 d["token_overhead_x"]))

        s = prof.get(m, {}).get("subjective_dimensions", {})
        if s:
            v2j = prof_path.name.endswith("_v2.json")
            L.append("\nSUBJECTIVE  [%s]" % ("single-judge sonnet 5" if v2j
                                             else "claude_sonnet_4"))
            vals = [v["mean"] for v in s.values()]
            comp = sum(vals) / len(vals)
            if v2j:
                L.append("  %-26s %s" % ("Composite band", subj_band(comp)))
                L.append("  %-26s %s" % ("", "+/-0.3 spans where three judge "
                                             "families put this model"))
                L.append("  %-26s %s" % ("", "the AXIS is sonnet 5's; another "
                                             "judge shifts everyone by ~1.0"))
                L.append("  %-26s %s" % ("  axes (less reliable)",
                         "  ".join("%s %.1f" % (k2[:4], v["mean"])
                                   for k2, v in sorted(s.items()))))
            else:
                for k2, v in sorted(s.items()):
                    L.append("  %-26s %8.2f/5"
                             % (k2.replace("_", " ").capitalize(), v["mean"]))

        bb = bay_by.get(m)
        L.append("─" * 78)
        if bb:
            L.append("COMMUNITY RANK: #%d of %d   [ELO %.0f ± %.0f]"
                     % (bb["rank"], len(bay_by), bb["elo_mean"], bb.get("elo_std", 0)))
        else:
            L.append("COMMUNITY RANK: no arena data for this model")
        st, wk = derive_strength_weakness(m, prof, beh, {mm: {k3: (v[0], v[1])
                  for k3, v in md.items()} for mm, md in rates.items()},
                  bay_by, len(bay_by), mode_pool, fh)
        # The v1 helper writes the flaw weakness as "N.NN per session, mean
        # score NN/100". Those are the exact two figures this card stopped
        # printing, so letting the summary line carry them would undo the band
        # three lines further down. v1 is left alone -- it is the published
        # generator for the earlier rounds -- and its wording is replaced here.
        # A "Top-N on X" headline is a rank claim. The threshold used to be
        # 2 x 0.046, the standard error of a 19-session mean under the judge's
        # own per-session noise -- which asks only "would this judge say the
        # same thing again". An independent judge from another family moved
        # model means by 0.24-0.30 after its different use of the scale was
        # removed, and that disagreement is systematic: averaging more
        # sessions does not shrink it. So the bar is the cross-judge figure,
        # not the within-judge one. It is roughly six times wider, and it is
        # the number that answers "would anyone else agree".
        mo = re.match(r"Top-\d+ on (.+?) \(([\d.]+)/5\)$", st)
        if mo:
            lab = mo.group(1)
            key = next((k for k, v in MODE_LABELS.items() if v == lab), None)
            if key:
                vals = sorted((pp["failure_modes"][key]["mean"]
                               for pp in prof.values()
                               if isinstance((pp.get("failure_modes") or {}).get(key), dict)
                               and "mean" in pp["failure_modes"][key]), reverse=True)
                if len(vals) >= 3 and (vals[0] - vals[2]) <= SUBJ_PAD:
                    st = ("Strong on %s (%s/5; within %.1f of the rest of the "
                          "top -- an independent judge reorders this)"
                          % (lab, mo.group(2), SUBJ_PAD))

        if wk.startswith("Frequent fatal flaws"):
            wk = ("Frequent fatal flaws (highest tier of the corpus; see the "
                  "craft band above)")
        L.append("Strength: %s" % st)
        L.append("Weakness: %s" % wk)
        out.append("\n".join(L))

    txt = ("\n\n" + "=" * 78 + "\n\n").join(out)
    print(txt)
    if not args.model and not args.limit:
        (R / "profile_cards_v2.md").write_text(
            "\n\n".join("### %s\n\n```\n%s\n```" % (m, c) for m, c in zip(models, out)))
        print("\n\nwrote results/profile_cards_v2.md (%d cards)" % len(out))


if __name__ == "__main__":
    main()
