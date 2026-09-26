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

One card is built once, as data (build_card), and rendered twice: as the
markdown in results/profile_cards_v2.md (render_markdown) and as the public
JSON the PlotPoints site reads (card_json, via --json or
export_plotpoints_round4.py cards). The JSON is a projection of the same dict,
never a second implementation; tests/test_plotpoints_export.py holds the
markdown byte-identical to the committed file so the split cannot drift.

Usage: python3 generate_profile_cards_v2.py [--model KEY] [--limit N]
                                            [--json OUT] [--r4-json PATH]

  --r4-json PATH  read the round-4 rows from a committed
                  round4_willingness_leaderboard.json instead of re-running
                  analyze_round4_willingness.py (which rewrites that file).
  --json OUT      also write the cards as JSON: bands, never craft or
                  subjective figures, and no production-defect examples.
"""
import argparse, json, math, re, subprocess, sys, textwrap
from collections import defaultdict
from pathlib import Path

from generate_profile_cards import (wilson_ci, derive_strength_weakness,
                                    MODE_LABELS)
from make_j_barchart import silent

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
JSON_SCHEMA_VERSION = 1


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


def _col(v, lo, hi, width):
    """The cell a value falls in, on a fixed axis of `width` cells."""
    return max(0, min(width - 1, int(round((v - lo) / (hi - lo) * (width - 1)))))


SUBJ_LO, SUBJ_HI, SUBJ_W = 1.0, 5.0, 30
SUBJ_PAD = 0.3


def subj_cells(mean):
    """First and last filled cell of the subjective band; see subj_band."""
    return (_col(mean - SUBJ_PAD, SUBJ_LO, SUBJ_HI, SUBJ_W),
            _col(mean + SUBJ_PAD, SUBJ_LO, SUBJ_HI, SUBJ_W))


def draw_subj_band(a, b):
    cells = ["░"] * SUBJ_W
    for i in range(a, b + 1):
        cells[i] = "█"
    return "%.0f %s %.0f" % (SUBJ_LO, "".join(cells), SUBJ_HI)


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
    return draw_subj_band(*subj_cells(mean))


FLAW_LO, FLAW_HI, FLAW_W = -20, 100, 30
FLAW_PAD = 10


def flaw_cells(mean):
    """First and last filled cell of the craft band; see flaw_band."""
    return (_col(mean - FLAW_PAD, FLAW_LO, FLAW_HI, FLAW_W),
            _col(mean + FLAW_PAD, FLAW_LO, FLAW_HI, FLAW_W))


def draw_flaw_band(a, b):
    cells = ["░"] * FLAW_W
    for i in range(a, b + 1):
        cells[i] = "█"
    zero = _col(0, FLAW_LO, FLAW_HI, FLAW_W)
    if cells[zero] == "░":
        cells[zero] = "│"
    return "%d %s %d" % (FLAW_LO, "".join(cells), FLAW_HI)


def flaw_band(mean):
    """A +/-10 interval drawn on a fixed -20..100 axis, with no figure.

    The axis is fixed across every card so bands can be compared by eye; it
    starts below zero because the scale has no floor and six models sit there.
    """
    return draw_flaw_band(*flaw_cells(mean))


def bar(rate, width=12, full=0.5):
    f = int(min(rate / full, 1) * width)
    return "█" * f + "░" * (width - f)


def load_r4_json(path):
    """Round-4 willingness rows from a leaderboard JSON the analyzer wrote.

    Everything the card shows is in the JSON: rank, the n behind each rate,
    held_under_pressure with its note, and the empty-reply fields behind the
    "empty replies that climb with the ask" warning, which is re-tested here
    with make_j_barchart.silent, the analyzer's own thresholds.
    """
    return r4_rows(json.loads(Path(path).read_text(encoding="utf-8")))


def r4_rows(data):
    """{model: row} from a parsed leaderboard JSON, with n_ranked and
    tied_with added (what willingness_fields needs)."""
    res = {r["model"]: dict(r) for r in data["leaderboard"]}
    n_ranked = sum(1 for r in res.values() if r["ranked"])
    for r in res.values():
        r["n_ranked"] = n_ranked
    for t in data.get("j_ties", []):
        for m in t["models"]:
            res[m]["tied_with"] = [o for o in t["models"] if o != m]
    return res


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
    rate, and held_under_pressure with its note. The empty-reply warning was
    the last thing read from stdout; it is now rebuilt from the JSON fields
    (load_r4_json), with the same thresholds.

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
    return load_r4_json(wrote.group(1))


def kappa_from_note(note):
    """(kappa, bar) as the analyzer's held_under_pressure_note states them.

    Quoted from the note, not restated here: the analyzer re-checks that
    figure against the Jev files on every run and warns if it drifts.
    """
    mo = re.search(r"kappa at turn \d+ is ([\d.]+).*?below the ([\d.]+) bar",
                   note or "")
    return (mo.group(1), mo.group(2)) if mo else (None, None)


def willingness_fields(d):
    """One round-4 row as the card (and the site's J board) carries it.

    J is on the first ask only. The second push is its own field, marked as
    outside J, with the rater agreement that keeps it out. Counts are derived
    here once, so the markdown and the JSON cannot disagree about them.
    """
    n = d["held_first_n"]
    rate = d["held_line_rate"]
    # Shown as a count too: with 4 first asks one exchange is 0.25.
    k = round(rate * n) if n and rate is not None else None
    pn = d["held_under_pressure_n"]
    kappa, bar_ = kappa_from_note(d.get("held_under_pressure_note"))
    by = d.get("empty_rate_a_by_subtrack") or {}
    return {
        "J": d["J"],
        "rank": d["rank"],
        "ranked": d["ranked"],
        "of": d.get("n_ranked"),
        "unranked_reason": d["unranked_reason"],
        "tied_with": list(d.get("tied_with") or []),
        "usable_exchanges_a": d["usable_exchanges_a"],
        "held_first": {"rate": rate, "k": k, "n": n},
        "over_refusal_hard_rungs": d["over_refusal_hard_rungs"],
        "over_refusal_intimacy": d["over_refusal_intimacy"],
        "over_refusal_gore": d["over_refusal_gore"],
        "held_under_pressure": {
            "rate": d["held_under_pressure"],
            "kept": pn - d["folds_under_pressure"],
            "n": pn,
            # First-ask holds with no usable turn-4 reply.
            "no_turn4": max(0, k - pn) if pn and k is not None else 0,
            # Quoted only where there is a second push to qualify.
            "kappa": kappa if pn else None, "bar": bar_ if pn else None,
            "in_j": False},
        "policy_compliance_rate": d["policy_compliance_rate"],
        "overshoot_rate": d["overshoot_rate"],
        "empty": {
            "rate": d["empty_rate_a"],
            "by_subtrack": dict(by),
            "rung_slope": d["empty_rung_slope_a"],
            # The analyzer's own warning for empty replies that climb with the
            # rung (>= 20% empty and >= 25 points from rung 1 to rung 5).
            "silent_flag": bool(silent(d))},
    }


def willingness_block(w):
    """The round-4 lines of a card, from willingness_fields()."""
    f = lambda v: "n/a" if v is None else "%.2f" % v
    L = ["\nWILLINGNESS / JUDGMENT (round 4)"]
    L.append("  %-26s %s   (held at first ask − over-refusal)"
             % ("Youden's J", f(w["J"])))
    if w["ranked"]:
        L.append("  %-26s %d of %d" % ("Rank by J", w["rank"], w["of"]))
        if w["tied_with"]:
            L.append("    Tied on J with %s (order arbitrary)."
                     % ", ".join(w["tied_with"]))
    elif (w["unranked_reason"] or "").startswith("insufficient data"):
        L.append("  %-26s not ranked: insufficient Track A data (%d usable)"
                 % ("Rank by J", w["usable_exchanges_a"]))
    else:
        L.append("  %-26s not ranked: %s" % ("Rank by J", w["unranked_reason"]))
    hf = w["held_first"]
    n = hf["n"]
    if n:
        L.append("  %-26s %s   (%d of %d usable first asks)"
                 % ("Held at first ask", f(hf["rate"]), hf["k"], n))
    else:
        L.append("  %-26s n/a    (no B-hard run)" % "Held at first ask")
    L.append("  %-26s %s   (L3-L5, Jev-gated)"
             % ("Over-refusal", f(w["over_refusal_hard_rungs"])))
    # The subtrack split is over every rung and ungated, so it is labelled:
    # beside the L3-L5 line above, deepseek_v4_flash reads 0.54 overall
    # against 0.42 / 0.16, which looks like arithmetic gone wrong.
    L.append("  Over-refusal by subtrack   intimacy %s / gore %s   (L1-L5, ungated)"
             % (f(w["over_refusal_intimacy"]), f(w["over_refusal_gore"])))
    hp = w["held_under_pressure"]
    pn = hp["n"]
    if pn:
        L.append("  %-26s %s   (%d of %d first-ask holds kept at turn 4)"
                 % ("Held under pressure", f(hp["rate"]), hp["kept"], pn))
        gap = hp["no_turn4"]
        if gap > 0:
            L.append("    %d more first-ask hold%s no usable turn-4 reply."
                     % (gap, " has" if gap == 1 else "s have"))
    elif n:
        L.append("  %-26s n/a    (no first ask held, nothing to push on)"
                 % "Held under pressure")
    if pn:
        k, bar_ = hp["kappa"], hp["bar"]
        L.append("    Not in J: %s" % (
            "rater kappa %s on the second push, below the %s bar." % (k, bar_)
            if k else "raters agree less on the second push than the first."))
    L.append("  Policy compliance          %s        Overshoot %s"
             % (f(w["policy_compliance_rate"]), f(w["overshoot_rate"])))
    e = w["empty"]
    if e["silent_flag"]:
        L.append("  %-26s %s" % ("Empty replies",
                                 "%.0f%% of Track A, rung 1 -> 5 %+.0f points"
                                 % (100 * e["rate"], 100 * e["rung_slope"])))
        by = e["by_subtrack"]
        if len(by) > 1:
            L.append("  %-26s %s" % ("", " / ".join(
                "%s %.0f%%" % (k2, 100 * by[k2])
                for k2 in sorted(by, key=lambda k2: k2 != "intimacy"))))
        L.append("    They climb with the ask, so they read as refusals by silence.")
        L.append("    J drops them as no signal and is scored on the replies given.")
    return L


def _read_json(path):
    with open(path) as f:
        return json.load(f)


def load_inputs(results_dir=R, r4_json=None, r4=None):
    """Everything a card is built from, read once. `r4` wins over `r4_json`;
    with neither, the analyzer is re-run (load_r4)."""
    results_dir = Path(results_dir)
    verdict_path = results_dir / "model_card_verdicts.json"
    verdicts = load_verdicts(verdict_path)
    verdict_doc = json.loads(verdict_path.read_text(encoding="utf-8"))

    # v2 is the single-rater corpus: all 4746 checks by one instrument under
    # the corrected F3/F5 rubrics. The Sonnet pass stays in the original file
    # as a second rater -- it covered only part of the corpus and two of its
    # rubrics have since been rewritten, so mixing the two would build each
    # model's rate from two instruments. Measured cost of that mixing: pooled
    # kappa 0.565, with F3 and F5 diverging in opposite directions.
    src = results_dir / "per_turn_failures_v2.jsonl"
    if not src.exists():
        src = results_dir / "per_turn_failures.jsonl"
    with open(src) as fh_:
        fails = [json.loads(l) for l in fh_]
    beh = _read_json(results_dir / "behavioral_metrics.json")
    # Prefer the single-judge re-score, same rule as the flaw summary above.
    prof_path = results_dir / "model_profiles_v2.json"
    if not prof_path.exists():
        prof_path = results_dir / "model_profiles.json"
    prof = _read_json(prof_path)
    bay = _read_json(results_dir / "community_arena_bayesian.json")
    # Prefer the single-rater re-score, same as per_turn_failures_v2 above.
    # The Sonnet summary stays on disk as the second rater.
    fh_path = results_dir / "flaw_hunter_session_summary_v2.json"
    if not fh_path.exists():
        fh_path = results_dir / "flaw_hunter_session_summary.json"
    fh = _read_json(fh_path)
    if r4 is None:
        r4 = load_r4_json(r4_json) if r4_json else load_r4()
    # Coverage gates the whole card. Every other metric silently drops the
    # turns a model never answered, so a model that mostly stays silent scores
    # like a good one on a tiny denominator -- tencent_hy4 answered 9 of 220
    # turns and read as ordinary. See compute_coverage.py.
    # Generation/harness faults the craft rubric has no label for. Several
    # raters reported these and could deduct nothing for them.
    pd_path = results_dir / "production_defects.json"
    pdef = _read_json(pd_path)["per_model"] if pd_path.exists() else {}
    cov_path = results_dir / "model_coverage.json"
    cov = _read_json(cov_path)["per_model"] if cov_path.exists() else {}

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

    return {
        "verdicts": verdicts,
        "verdict_meta": {k: verdict_doc.get(k)
                         for k in ("reviewed_on", "scope", "sources")},
        "inputs": {"failures": src.name, "profiles": prof_path.name,
                   "flaw_hunter": fh_path.name},
        "rates": rates, "pooled": pooled, "pool_rank": pool_rank,
        "bay_by": bay_by, "pop": pop, "mode_pool": mode_pool,
        "beh": beh, "prof": prof, "prof_v2": prof_path.name.endswith("_v2.json"),
        "fh": fh, "fh_v2": fh_path.name.endswith("_v2.json"),
        "r4": r4, "pdef": pdef, "cov": cov,
        # The per-(model, mode) (n, k) view derive_strength_weakness takes.
        "rates_nk": {mm: {k3: (v[0], v[1]) for k3, v in md.items()}
                     for mm, md in rates.items()},
    }


def ordered_models(ctx):
    """Card order: Round 01 community ELO, best first, then by id."""
    bay_by = ctx["bay_by"]
    return sorted(ctx["rates"],
                  key=lambda m: (-(bay_by.get(m, {}).get("elo_mean") or 0), m))


def build_card(m, ctx):
    """One model's card as data. Keys starting with "_" are markdown-only
    (craft and subjective figures, defect examples) and never reach JSON."""
    verdicts, rates = ctx["verdicts"], ctx["rates"]
    format_verdict(m, verdicts)  # a model with no reviewed verdict fails here
    card = {"id": m, "verdict": verdicts[m]}

    c = ctx["cov"].get(m)
    card["coverage"] = ({"answered": c["answered"], "turns": c["turns"],
                         "coverage": c["coverage"], "excluded": c["excluded"],
                         "roster_turns": FULL_ROSTER_TURNS} if c else None)

    card["standing_modes"] = []
    for mo in STANDING_MODES:
        if mo not in rates[m]: continue
        n, k, _ = rates[m][mo]
        if n < MIN_N_FOR_RATE: continue
        lo, hi = wilson_ci(k, n)
        card["standing_modes"].append({"mode": mo, "label": LABELS[mo], "k": k,
                                       "n": n, "rate": k / n, "ci": [lo, hi]})

    pooled = ctx["pooled"]
    if m in pooled:
        k, n = pooled[m]
        lo, hi = wilson_ci(k, n)
        card["trap_pooled"] = {"k": k, "n": n, "rate": k / n, "ci": [lo, hi],
                               "rank": ctx["pool_rank"].index(m) + 1,
                               "of": len(pooled)}
    else:
        card["trap_pooled"] = None

    card["trap_modes"] = []
    for mo in TRAP_MODES:
        if mo not in rates[m]:
            card["trap_modes"].append({"mode": mo, "label": LABELS[mo], "run": False})
            continue
        n, k, b = rates[m][mo]
        card["trap_modes"].append({"mode": mo, "label": LABELS[mo], "k": k, "n": n,
                                   "borderline": b if mo in CONTINUUM else None})

    r4 = ctx["r4"]
    card["willingness"] = willingness_fields(r4[m]) if m in r4 else None

    b = ctx["beh"]["per_model"].get(m, {})
    if b:
        card["behavioral"] = []
        for met, lab in (("word_count", "Avg words"),
                         ("unique_word_ratio", "Unique-word ratio"),
                         ("bigram_repetition", "Phrase repetition")):
            if met not in b: continue
            v = b[met]["mean"]; pv = ctx["pop"].get(met, 0)
            flag = None
            if met == "bigram_repetition": flag = "high" if v > pv * 1.2 else None
            elif met == "unique_word_ratio": flag = "low" if v < pv * 0.9 else None
            card["behavioral"].append({"metric": met, "label": lab, "value": v,
                                       "population": pv, "flag": flag})
    else:
        card["behavioral"] = None

    fh = ctx["fh"]
    if m in fh.get("per_model", {}):
        d = fh["per_model"][m]
        # Shown as an interval, never a figure. Two raters on the same
        # rubric and the same session differ by a median of 14 points
        # (cross-rater r = +0.20), and per-rater calibration has sd 7.8
        # after model and seed effects are removed. A printed mean invites
        # a comparison the instrument cannot support, so the card renders
        # the band and lets overlapping bands read as "not separable".
        card["craft"] = {
            "axis": [FLAW_LO, FLAW_HI], "cells": FLAW_W,
            "filled": list(flaw_cells(d["mean"])),
            "sessions": d.get("n", 0),
            "top_flaws": [f["flaw"].split(":")[-1]
                          for f in d.get("top_flaws", [])[:3]],
            "_rater": "single-rater v2" if ctx["fh_v2"] else "claude_sonnet",
        }
    else:
        card["craft"] = None

    d = ctx["pdef"].get(m)
    if d:
        ex = d.get("examples") or {}
        card["production_defects"] = {
            "turns": d["turns"], "leak_turns": d["leak_turns"],
            "leak_rate": d["leak_rate"], "selfplay_turns": d["selfplay_turns"],
            "selfplay_rate": d["selfplay_rate"], "loop_turns": d.get("loop_turns"),
            "loop_rate": d.get("loop_rate", 0),
            "loop_worst_turn": d.get("loop_worst_turn", 0),
            "token_overhead_x": d.get("token_overhead_x"),
            # Quoted model output: kept for the markdown, never published.
            "_examples": {k: ex[k][:72] for k in ("leak", "selfplay") if ex.get(k)},
        }
    else:
        card["production_defects"] = None

    s = ctx["prof"].get(m, {}).get("subjective_dimensions", {})
    if s:
        vals = [v["mean"] for v in s.values()]
        comp = sum(vals) / len(vals)
        card["subjective"] = {
            "judge": ("single-judge sonnet 5" if ctx["prof_v2"]
                      else "claude_sonnet_4"),
            "axis": [SUBJ_LO, SUBJ_HI], "cells": SUBJ_W,
            "filled": list(subj_cells(comp)),
            "axes": [{"key": k2, "label": k2.replace("_", " ").capitalize(),
                      "filled": list(subj_cells(v["mean"]))}
                     for k2, v in sorted(s.items())],
            "_v2": ctx["prof_v2"],
            "_axis_means": [(k2, v["mean"]) for k2, v in sorted(s.items())],
        }
    else:
        card["subjective"] = None

    bb = ctx["bay_by"].get(m)
    card["community_r1"] = ({"rank": bb["rank"], "of": len(ctx["bay_by"]),
                             "elo_mean": bb["elo_mean"],
                             "elo_std": bb.get("elo_std", 0)} if bb else None)

    prof = ctx["prof"]
    st, wk = derive_strength_weakness(m, prof, ctx["beh"], ctx["rates_nk"],
                                      ctx["bay_by"], len(ctx["bay_by"]),
                                      ctx["mode_pool"], fh)
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
    card["strength"], card["weakness"] = st, wk
    card["elo"], card["composite"] = None, None
    return card


def render_markdown(card):
    """The text card in results/profile_cards_v2.md, from build_card()."""
    m = card["id"]
    L = [f"Model: {m}", "─" * 78, "\n" + format_verdict(m, {m: card["verdict"]})]
    c = card["coverage"]
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
        if c["turns"] < c["roster_turns"]:
            L.append("  Sample: %d of the roster's %d turns (~%d of %d seeds)."
                     % (c["turns"], c["roster_turns"],
                        round(c["turns"] / TURNS_PER_SEED),
                        round(c["roster_turns"] / TURNS_PER_SEED)))
            L.append("  A high coverage here means it answered what it was")
            L.append("  asked, not that it was asked much.")

    L.append("\nFAILURE MODES — measured per model (n ≥ %d)" % MIN_N_FOR_RATE)
    for s in card["standing_modes"]:
        k, n = s["k"], s["n"]
        lo, hi = s["ci"]
        L.append("  %-26s %5.1f%%  [%4.1f–%4.1f]  %s  %d probes"
                 % (s["label"], 100 * k / n, 100 * lo, 100 * hi,
                    bar(k / n, full=0.25), n))

    tp = card["trap_pooled"]
    if tp:
        k, n = tp["k"], tp["n"]
        lo, hi = tp["ci"]
        L.append("\nTRAP-MODE FAILURE RATE (pooled over 9 modes)")
        L.append("  %-26s %5.1f%%  [%4.1f–%4.1f]  %s  %d/%d"
                 % ("Pooled", 100 * k / n, 100 * lo, 100 * hi, bar(k / n), k, n))
        L.append("  rank %d of %d models carrying all nine modes" % (tp["rank"], tp["of"]))

    L.append("\n  per-mode detail — counts, not rates: 2-9 probes each, so a")
    L.append("  percentage here would not survive one probe changing")
    for t in card["trap_modes"]:
        if t.get("run") is False:
            L.append("  %-26s  not run" % t["label"]); continue
        extra = "  (+%d borderline)" % t["borderline"] if t["borderline"] else ""
        L.append("  %-26s  %d/%d failed%s" % (t["label"], t["k"], t["n"], extra))

    if card["willingness"] is not None:
        L.extend(willingness_block(card["willingness"]))

    if card["behavioral"] is not None:
        L.append("\nBEHAVIORAL")
        for b in card["behavioral"]:
            mark = {"high": " ↑", "low": " ↓"}.get(b["flag"], "")
            L.append("  %-26s %8.3f   (population %.3f)%s"
                     % (b["label"], b["value"], b["population"], mark))

    cr = card["craft"]
    if cr:
        L.append("\nFLAW HUNTER  [%s]" % cr["_rater"])
        top = ", ".join(cr["top_flaws"])
        L.append("  %-26s %s" % ("Craft band", draw_flaw_band(*cr["filled"])))
        L.append("  %-26s %s" % ("", "±10 is the rater noise floor, "
                                      "not a sampling error"))
        L.append("  %-26s %d" % ("Sessions", cr["sessions"]))
        if top:
            L.append("  %-26s %s" % ("Top flaws", top))

    d = card["production_defects"]
    if d:
        L.append("\nPRODUCTION DEFECTS  [mechanical, not judged]")
        dirty = d["leak_turns"] or d["selfplay_turns"] or d["loop_turns"]
        if dirty:
            L.append("  %-26s %7.1f%%   (%d of %d turns)"
                     % ("Scaffolding/token leak", 100 * d["leak_rate"],
                        d["leak_turns"], d["turns"]))
            L.append("  %-26s %7.1f%%   (%d of %d turns)"
                     % ("Wrote the user's turn", 100 * d["selfplay_rate"],
                        d["selfplay_turns"], d["turns"]))
            L.append("  %-26s %7.1f%%   worst turn %.0f%% repeated"
                     % ("Degenerate repetition",
                        100 * d["loop_rate"], 100 * d["loop_worst_turn"]))
            if d["token_overhead_x"]:
                L.append("  %-26s %6.1fx    billed per visible char, "
                         "vs the prose floor" % ("Token overhead",
                                                 d["token_overhead_x"]))
            for k in ("leak", "selfplay"):
                if d["_examples"].get(k):
                    L.append("    %s: %s" % (k, d["_examples"][k]))
        else:
            L.append("  %-26s %s" % ("None detected",
                                     "%d turns clean" % d["turns"]))
        if d["token_overhead_x"] and not dirty:
            L.append("  %-26s %6.1fx    billed per visible char, "
                     "vs the prose floor" % ("Token overhead",
                                             d["token_overhead_x"]))

    s = card["subjective"]
    if s:
        L.append("\nSUBJECTIVE  [%s]" % s["judge"])
        if s["_v2"]:
            L.append("  %-26s %s" % ("Composite band", draw_subj_band(*s["filled"])))
            L.append("  %-26s %s" % ("", "+/-0.3 spans where three judge "
                                         "families put this model"))
            L.append("  %-26s %s" % ("", "the AXIS is sonnet 5's; another "
                                         "judge shifts everyone by ~1.0"))
            L.append("  %-26s %s" % ("  axes (less reliable)",
                     "  ".join("%s %.1f" % (k2[:4], v)
                               for k2, v in s["_axis_means"])))
        else:
            for k2, v in s["_axis_means"]:
                L.append("  %-26s %8.2f/5"
                         % (k2.replace("_", " ").capitalize(), v))

    bb = card["community_r1"]
    L.append("─" * 78)
    if bb:
        L.append("COMMUNITY RANK: #%d of %d   [ELO %.0f ± %.0f]"
                 % (bb["rank"], bb["of"], bb["elo_mean"], bb["elo_std"]))
    else:
        L.append("COMMUNITY RANK: no arena data for this model")
    L.append("Strength: %s" % card["strength"])
    L.append("Weakness: %s" % card["weakness"])
    return "\n".join(L)


def render_markdown_file(cards):
    """The whole results/profile_cards_v2.md, byte for byte."""
    return "\n\n".join("### %s\n\n```\n%s\n```" % (c["id"], render_markdown(c))
                       for c in cards)


# Summary lines quote judge scores ("(4.58/5)", "(74.9/100)", "lowest session:
# 3.1"). The public card shows craft and subjective only as bands, so those
# figures are cut from the JSON copy; the markdown keeps its wording.
_SCORE_PAREN = re.compile(r" \(\d+(?:\.\d+)?/(?:5|100)\)")
_SCORE_LEAD = re.compile(r" \(\d+(?:\.\d+)?/(?:5|100); ")
_FLOOR = re.compile(r" \(lowest session: \d+(?:\.\d+)?\)")
_LEFTOVER_SCORE = re.compile(r"\d\.\d+/(?:5|100)\b|\d+/100\b|lowest session")


def public_summary(text):
    out = _SCORE_PAREN.sub("", text)
    out = _SCORE_LEAD.sub(" (", out)
    out = _FLOOR.sub("", out)
    out = out.replace(" -- ", "; ")
    if _LEFTOVER_SCORE.search(out):
        raise ValueError("summary still quotes a judge score: %r" % out)
    return out


def _r(v, nd=4):
    return None if v is None else round(v, nd)


def card_json(card):
    """The public projection of a card: allowlisted keys only, craft and
    subjective as bands (cell indexes, no figure), no quoted model output."""
    c = card["coverage"]
    tp = card["trap_pooled"]
    d = card["production_defects"]
    cr = card["craft"]
    s = card["subjective"]
    bb = card["community_r1"]
    return {
        "id": card["id"],
        "verdict": card["verdict"],
        "coverage": ({"answered": c["answered"], "turns": c["turns"],
                      "coverage": _r(c["coverage"]), "excluded": bool(c["excluded"]),
                      "roster_turns": c["roster_turns"]} if c else None),
        "standing_modes": [{"mode": x["mode"], "label": x["label"], "k": x["k"],
                            "n": x["n"], "rate": _r(x["rate"]),
                            "ci": [_r(x["ci"][0]), _r(x["ci"][1])]}
                           for x in card["standing_modes"]],
        "trap_pooled": ({"k": tp["k"], "n": tp["n"], "rate": _r(tp["rate"]),
                         "ci": [_r(tp["ci"][0]), _r(tp["ci"][1])],
                         "rank": tp["rank"], "of": tp["of"]} if tp else None),
        "trap_modes": [dict(t) for t in card["trap_modes"]],
        "willingness": (json.loads(json.dumps(card["willingness"]))
                        if card["willingness"] is not None else None),
        "behavioral": ([{"metric": b["metric"], "label": b["label"],
                         "value": _r(b["value"], 3), "population": _r(b["population"], 3),
                         "flag": b["flag"]} for b in card["behavioral"]]
                       if card["behavioral"] is not None else None),
        "craft": ({"axis": list(cr["axis"]), "cells": cr["cells"],
                   "filled": list(cr["filled"]), "sessions": cr["sessions"],
                   "top_flaws": list(cr["top_flaws"])} if cr else None),
        "production_defects": ({k: (_r(d[k]) if isinstance(d[k], float) else d[k])
                                for k in ("turns", "leak_rate", "leak_turns",
                                          "selfplay_rate", "selfplay_turns",
                                          "loop_turns", "loop_rate",
                                          "loop_worst_turn", "token_overhead_x")}
                               if d else None),
        "subjective": ({"judge": s["judge"],
                        "axis": [int(s["axis"][0]), int(s["axis"][1])],
                        "cells": s["cells"], "filled": list(s["filled"]),
                        "axes": [dict(a, filled=list(a["filled"]),
                                      less_reliable=True) for a in s["axes"]]}
                       if s else None),
        "community_r1": ({"rank": bb["rank"], "of": bb["of"],
                          "elo_mean": int(round(bb["elo_mean"])),
                          "elo_std": int(round(bb["elo_std"] or 0))}
                         if bb else None),
        "strength": public_summary(card["strength"]),
        "weakness": public_summary(card["weakness"]),
        "elo": None, "composite": None,
    }


def cards_document(cards, ctx):
    """The --json file: every card's public projection, in card order."""
    meta = ctx["verdict_meta"]
    return {
        "schema_version": JSON_SCHEMA_VERSION,
        "reviewed_on": meta["reviewed_on"],
        "scope": meta["scope"],
        "sources": meta["sources"],
        "inputs": dict(ctx["inputs"]),
        "cards": {c["id"]: card_json(c) for c in cards},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model"); ap.add_argument("--limit", type=int)
    ap.add_argument("--json", metavar="OUT",
                    help="also write the cards as public JSON to OUT")
    ap.add_argument("--r4-json", metavar="PATH",
                    help="read round-4 rows from this leaderboard JSON instead "
                         "of re-running analyze_round4_willingness.py")
    args = ap.parse_args()
    ctx = load_inputs(r4_json=args.r4_json)

    models = ordered_models(ctx)
    if args.model: models = [m for m in models if m == args.model]
    if args.limit: models = models[:args.limit]

    cards = [build_card(m, ctx) for m in models]
    out = [render_markdown(c) for c in cards]

    txt = ("\n\n" + "=" * 78 + "\n\n").join(out)
    print(txt)
    if not args.model and not args.limit:
        (R / "profile_cards_v2.md").write_text(render_markdown_file(cards))
        print("\n\nwrote results/profile_cards_v2.md (%d cards)" % len(out))
    if args.json:
        Path(args.json).write_text(
            json.dumps(cards_document(cards, ctx), indent=2, ensure_ascii=False)
            + "\n", encoding="utf-8")
        print("wrote %s (%d cards)" % (args.json, len(cards)))


if __name__ == "__main__":
    main()
