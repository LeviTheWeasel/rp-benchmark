#!/usr/bin/env python3
"""Round 4 and the earlier rounds: one row per returning model, and the bridges.

Round 4 changed the instruments (craft judge Sonnet 4 -> Sonnet 5, headline
craft -> J, a new willingness classifier, a new flaw hunter), mostly not the
models. This analyzer writes what still connects the rounds, and says what
does not, in results/round4_continuity.json:

  rows            one per returning model: in round 2 or 3 and in round 4.
                  40 craft models plus rocinante_12b (Track A only, no craft,
                  no J). Fields:
                    r2_human       round-2 multi-turn arena, final 1,943 votes:
                                   ELO, 95% interval, votes, rank of 20, and
                                   whether voters read the round-4 transcripts
                    r3_nsfw        the published round-3 table as published:
                                   position, tie range, craft (Sonnet 4),
                                   n, and its refusal % labelled as round 3's
                                   own instrument
                    old_judge_r4   the round-2/3 craft judge (Sonnet 4) on the
                                   round-4 transcripts, as a BAND: the mean
                                   over the 12 core seeds (09-20) +/- the half
                                   width of its 95% seed-bootstrap interval.
                                   Never a rank.
                    v2_tier        the round-4 judge's letter (round4_overview)
                    J              as published (round4_overview / J file)
                    same_transcripts  identical to the earlier round's text, or
                                   regenerated
  old_judge       the band for every round-4 craft model, new ones included
  correlations    cross-round and cross-judge Spearman, with n, a 95% model
                  bootstrap interval and a permutation p
  judge_bridge    old vs new judge on identical transcripts, by subset
  model_drift     round-3 standard (June) vs round 4 (September): same seeds,
                  same simulator, same old judge, regenerated transcripts
  cross_family    how much more each Claude judge scores Claude-model sessions
                  than a ChatGPT or Gemini reference does, same transcripts
  willingness     why round 3's refusal % and J are not one series

What it will not write, by decision (docs/ROUND4_DESIGN.md sec 23): no
per-model translation of the new judge onto the old scale, no synthetic
composite, and no cross-round refusal column. build() checks its own output
for those keys and fails closed if one appears.

One session set for every cross-model column. Eight round-2 models played
only seeds 09-20, and seven of them still have only those 12 in round 4
(kimi_k2_6 was regenerated on all 20), so every per-model mean here is over
those 12 core seeds;
a model with fewer than all 12 gets no band. Every blank scene in the corpus
is on seed 05, outside the core.

Inputs, read-only:
    results/craft_baseline_*.json, results/multiturn_merged_all_v2.json
        round-4 transcripts, newest copy wins (transcript_hash.py rule), and
        the stored Sonnet 4 scores on them
    results/session_judge_v2.jsonl          new judge (Sonnet 5)
    results/session_judge_v1_legacy.jsonl   old judge backfill (2026-09-27)
    results/round3gen_R2_adversarial_catchup.json   round-3 standard track
    results/round3gen_R3_nsfw.json          round-3 NSFW roster
    results/round3_nsfw_leaderboard.json    the published round-3 table
    results/multiturn_arena_bayesian.json   round-2 human arena, final
    results/round4_overview.json            v2 tiers and J cells
    results/round4_willingness_leaderboard.json   J ranks
    results/judge_{round2,inc1}_{chatgpt,gemini}/  cross-family references

Old-judge scores count only on an identical judging task: a stored score
where judge_legacy_sonnet4.load_corpus finds the same judge_view_hash, or a
backfill row whose transcript_hash and judge_view_hash both match the
transcript on disk. A stale, duplicate or unparsed row fails the run.

Usage:
    python3 analyze_round4_continuity.py
    python3 analyze_round4_continuity.py --markdown /tmp/continuity.md
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import analyze_round4_overview as OV  # noqa: E402  (corpus, judge rows, stats)
import judge_legacy_sonnet4 as L  # noqa: E402  (old-judge identity rules)
from make_j_barchart import FINETUNES  # noqa: E402
from transcript_hash import transcript_hash  # noqa: E402

OUT = "round4_continuity.json"
RNG_SEED = 20260927
BOOT = 10000                 # seed bootstrap for the bands
CORR_BOOT = 10000            # model bootstrap for correlation intervals
PERM = 20000                 # permutation p
XFAM_BOOT = 4000             # model bootstrap for the cross-family coefficient
CORE = (9, 20)               # core seeds: the numeric suffix, inclusive
LEGACY_JUDGE = L.JUDGE_LABEL
LEGACY_PROMPT = L.EXPECTED_PROMPT_HASH
OLD_JUDGE_ID = L.LEGACY_MODEL

R2_TRANSCRIPTS = "multiturn_merged_all_v2.json"
R3_STANDARD = "round3gen_R2_adversarial_catchup.json"
R3_NSFW = "round3gen_R3_nsfw.json"
R3_TABLE = "round3_nsfw_leaderboard.json"
ARENA = "multiturn_arena_bayesian.json"
OVERVIEW = "round4_overview.json"
J_FILE = "round4_willingness_leaderboard.json"
V2_FILE = "session_judge_v2.jsonl"
LEGACY_FILE = "session_judge_v1_legacy.jsonl"

# Blind passes only: the not-blind ChatGPT package 1 is left out.
REFERENCES = {
    "chatgpt": ("ChatGPT, blind passes", OV.THREE_FAMILY["chatgpt"]),
    "gemini": ("Gemini, API passes", OV.THREE_FAMILY["gemini"]),
}

# Round 3's roster note and the owl_alpha decision (2026-09-27).
NOT_RETURNING_NOTES = {
    "owl_alpha": ("LongCat-2.0 (meituan/longcat-2.0), in round 3 under the "
                  "stealth id openrouter/owl-alpha. Not run in round 4 under "
                  "any name: the preview endpoint 404ed on 2026-08-05."),
}

# Keys this file must never carry (ROUND4_DESIGN sec 23, Levi 2026-09-27).
FORBIDDEN_KEYS = {"old_scale", "v2_on_old_scale", "translated", "mapped_v1",
                  "composite", "c_star", "composite_compatible", "refusal_delta",
                  "refusal_r4", "r4_refusal_pct", "hard_refusal_both_rounds",
                  "old_judge_rank", "rank_old_judge"}

INSTRUMENTS = [
    dict(what="Craft judge",
         before="Claude Sonnet 4 over the API (anthropic/claude-sonnet-4, prompt "
                "1ff004ccf5aa, temperature 0.1), rounds 2 and 3",
         round4="Claude Sonnet 5 as subscription subagents (session judge v2), "
                "same rubric text",
         comparable=True,
         how="comparable via the old judge re-run on every round-4 transcript: "
             "the old-judge band column. The raw numbers are not comparable: the "
             "new judge scores about half a point lower and spreads the top "
             "several times wider."),
    dict(what="Flaw hunter",
         before="Sonnet 4 with a primer, 100 minus quoted deductions",
         round4="subagent raters with standing instructions (read the real card, "
                "quote model turns only, no floor)",
         comparable=False,
         how="not comparable, because the rater and its instructions changed: "
             "per-model Spearman 0.57 between the two on 38 models, and a +9.5 "
             "point level shift (ROUND4_DESIGN sec 13c-quater). The old flaw "
             "hunter was not re-run."),
    dict(what="Headline",
         before="craft: Sonnet 4 overall on the round-3 NSFW track (round 3); "
                "the May composite (round 2)",
         round4="J, held-a-hard-line minus over-refusal (Youden's J)",
         comparable=False,
         how="not comparable, because J has no predecessor. It is the round's "
             "new axis; the craft line continues through the old-judge band and "
             "the round-4 judge tier."),
    dict(what="Willingness instrument",
         before="one flag per session in the judge JSON (refused_midscene), "
                "20 NSFW seeds with no scripted escalation",
         round4="a per-rung classifier with a Jev confidence gate on scripted "
                "L1-L5 ladders; over-refusal counts soft deflection",
         comparable=False,
         how="not comparable, because the seeds, the instrument, the construct "
             "and three months of provider drift all changed (ROUND4_DESIGN "
             "sec 5). Round 3's refusal % is published as it is, labelled as "
             "round 3's instrument."),
    dict(what="Track and simulator",
         before="round 3's table: NSFW seeds, DeepSeek V3.2 simulator; rounds 2 "
                "and 3 standard: adversarial seeds, Gemini 2.5 Flash simulator",
         round4="craft on the standard adversarial seeds with the Gemini 2.5 "
                "Flash simulator, 12 turns (the round-2 and round-3 standard "
                "setup); Track A/B ladders on DeepSeek V3.2",
         comparable=True,
         how="comparable via the round-3 standard track, which is round 4's "
             "craft setup: 13 models re-run on it in September moved little "
             "under the same judge. Against round 3's NSFW table only the broad "
             "order carries over (the finetunes below the rest), not the numbers "
             "or the order inside round 3's tied frontier."),
    dict(what="Roster",
         before="round 2: 21 multi-turn models; round 3: 40",
         round4="71: 70 with craft, 58 with a J row",
         comparable=True,
         how="comparable via the 41 returning models (40 with craft, "
             "rocinante_12b Track A only). 30 are new. owl_alpha (LongCat-2.0) "
             "was not run."),
    dict(what="Composite",
         before="the May composite: 21 models, human arena, Sonnet 4 Likert, "
                "27-dimension rubric, flaw hunter, behavioral",
         round4="none",
         comparable=False,
         how="not comparable, because two of its five inputs (the human arena "
             "and the 27-dimension rubric) do not exist for round-4 models, and "
             "the rubric's inputs are private. It is archived as published; no "
             "synthetic replacement is computed."),
]


class InputError(OV.InputError):
    """An input fails a check; nothing is written."""


# ---------------------------------------------------------------- helpers

def read_json(path):
    with open(path) as fh:
        return json.load(fh)


def seed_number(seed):
    mo = re.search(r"_(\d\d)$", seed)
    return int(mo.group(1)) if mo else None


def core_seeds(seeds, lo=CORE[0], hi=CORE[1]):
    return sorted(s for s in seeds if seed_number(s) is not None
                  and lo <= seed_number(s) <= hi)


def spearman(a, b):
    return OV.spearman(a, b)


def pearson(a, b):
    return float(np.corrcoef(np.asarray(a, float), np.asarray(b, float))[0, 1])


def boot_indices(n, B, rng):
    return rng.integers(0, n, size=(B, n))


def corr_block(xs, ys, label_x, label_y, rng_seed=RNG_SEED, B=None,
               perm=None, note=None, models=None):
    """Spearman with a model-resampling 95% interval and a permutation p."""
    B = CORR_BOOT if B is None else B
    perm = PERM if perm is None else perm
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    n = len(xs)
    out = dict(x=label_x, y=label_y, n=n)
    if n < 4:
        out.update(spearman=None, note="fewer than 4 models")
        return out
    if np.ptp(xs) == 0 or np.ptp(ys) == 0:
        out.update(spearman=None, note="a constant column")
        return out
    rho, p = OV.spearman_perm_p(xs, ys, n=perm, seed=rng_seed)
    rng = np.random.default_rng(rng_seed)
    draws = []
    for ii in boot_indices(n, B, rng):
        a, b = xs[ii], ys[ii]
        if np.ptp(a) > 0 and np.ptp(b) > 0:
            draws.append(spearman(a, b))
    lo, hi = np.percentile(draws, [2.5, 97.5]) if draws else (np.nan, np.nan)
    out.update(spearman=round(rho, 3), ci95=[round(float(lo), 3), round(float(hi), 3)],
               p=float("%.2g" % p), pearson=round(pearson(xs, ys), 3))
    if note:
        out["note"] = note
    if models is not None:
        out["models"] = list(models)
    return out


def paired_rho_difference(h, a, b, rng_seed=RNG_SEED, B=None):
    """rho(h, a) - rho(h, b) with a model-resampling interval, same draws."""
    B = CORR_BOOT if B is None else B
    h, a, b = (np.asarray(v, float) for v in (h, a, b))
    if len(h) < 4:
        return dict(difference=None, note="fewer than 4 models")
    rng = np.random.default_rng(rng_seed)
    d = []
    for ii in boot_indices(len(h), B, rng):
        if np.ptp(h[ii]) > 0 and np.ptp(a[ii]) > 0 and np.ptp(b[ii]) > 0:
            d.append(spearman(h[ii], a[ii]) - spearman(h[ii], b[ii]))
    d = np.asarray(d)
    lo, hi = np.percentile(d, [2.5, 97.5])
    return dict(difference=round(spearman(h, a) - spearman(h, b), 3),
                ci95=[round(float(lo), 3), round(float(hi), 3)],
                share_of_draws_below_zero=round(float((d < 0).mean()), 3))


def is_claude(model):
    return model.startswith("claude_")


# ---------------------------------------------------------------- scores

def load_scores(results):
    """(canon, v2, v1, v1_source) for the round-4 craft corpus.

    canon  sid -> analyze_round4_overview.load_corpus entry (hash, model, seed,
           source, blank_scene, ...)
    v2     sid -> Sonnet 5 overall (rows validated fail-closed by the overview's
           own rule)
    v1     sid -> Sonnet 4 overall on the identical judging task
    v1_source  sid -> 'stored_april' | 'stored_2026_09_21' | 'backfill_2026_09_27'
    """
    results = Path(results)
    canon, copies, _ = OV.load_corpus(results)
    rows = OV.load_judge_rows(results / V2_FILE)
    try:
        OV.validate_judge_rows(rows, canon, copies)
    except OV.InputError as e:
        raise InputError(str(e))
    v2 = {r["session_id"]: float(r["overall"]) for r in rows}
    try:
        lc = L.load_corpus(results, results / V2_FILE)
    except SystemExit as e:
        raise InputError("old-judge corpus: %s" % e)
    v1, src = {}, {}
    for sid, e in lc.items():
        if e["v1"] is None:
            continue
        v1[sid] = float(e["v1"])
        src[sid] = ("stored_april" if e["v1_src"] == R2_TRANSCRIPTS
                    else "stored_" + re.sub(r"^craft_baseline_(\d{4})(\d\d)(\d\d)_.*$",
                                            r"\1_\2_\3", e["v1_src"]))
    problems = []
    legacy = results / LEGACY_FILE
    for r in (L.read_rows(legacy) if legacy.exists() else []):
        sid = r.get("session_id")
        e = lc.get(sid)
        if e is None:
            problems.append("%s: backfill row for a session not in the corpus" % sid)
            continue
        if r.get("judge") != LEGACY_JUDGE or r.get("prompt_hash") != LEGACY_PROMPT:
            problems.append("%s: judge %r / prompt %r is not the round-2/3 judge"
                            % (sid, r.get("judge"), r.get("prompt_hash")))
            continue
        if (r.get("transcript_hash"), r.get("judge_view_hash")) != (
                e["transcript_hash"], e["view_hash"]):
            problems.append("%s: backfill row scored a different text" % sid)
            continue
        if not r.get("raw_parse_ok") or r.get("overall") is None:
            problems.append("%s: backfill row did not parse" % sid)
            continue
        if sid in v1:
            problems.append("%s: scored twice (stored and backfill)" % sid)
            continue
        v1[sid] = float(r["overall"])
        src[sid] = "backfill_2026_09_27"
    if problems:
        raise InputError("old-judge scores fail closed (%d problems):\n  %s"
                         % (len(problems), "\n  ".join(problems[:40])))
    return canon, v2, v1, src


def per_model(scores, canon, seeds=None):
    out = defaultdict(dict)
    for sid, v in scores.items():
        c = canon[sid]
        if seeds is None or c["seed"] in seeds:
            out[c["model"]][c["seed"]] = v
    return out


def bands(v1_by_model, core, B=BOOT, rng_seed=RNG_SEED):
    """Mean over the core seeds +/- the half width of a 95% seed bootstrap.

    Every model sees the same seed draw, so the joint draws also give rank
    intervals (kept in the scale block only, never per model)."""
    full = sorted(m for m, d in v1_by_model.items() if all(s in d for s in core))
    if not full:
        return {}, {}, {}
    X = np.array([[v1_by_model[m][s] for m in full] for s in core])   # seeds x models
    rng = np.random.default_rng(rng_seed)
    idx = boot_indices(len(core), B, rng)
    D = np.stack([X[ii].mean(0) for ii in idx])                         # B x models
    lo, hi = np.percentile(D, [2.5, 97.5], axis=0)
    means = X.mean(0)
    out = {}
    for j, m in enumerate(full):
        out[m] = dict(mean=round(float(means[j]), 2),
                      half_width=round(float(hi[j] - lo[j]) / 2, 2),
                      low=round(float(lo[j]), 3), high=round(float(hi[j]), 3),
                      n_sessions=len(core))
    # rank intervals from the same draws (1 = best), for the scale note
    ranks = np.argsort(np.argsort(-D, axis=1, kind="mergesort"), axis=1) + 1
    rlo, rhi = np.percentile(ranks, [2.5, 97.5], axis=0)
    widths = {m: float(rhi[j] - rlo[j]) for j, m in enumerate(full)}
    return out, dict(zip(full, means)), widths


def scale_note(means, widths, bands_):
    order = sorted(means, key=lambda m: -means[m])
    top = [means[m] for m in order]
    upper = [m for m in order if means[m] >= 4.3]
    overlap_next = sum(
        1 for a, b in zip(order, order[1:])
        if bands_[b]["high"] >= bands_[a]["low"])
    return dict(
        models=len(order),
        top_26_span=round(top[0] - top[25], 2) if len(top) >= 26 else None,
        top_10_span=round(top[0] - top[9], 2) if len(top) >= 10 else None,
        models_at_or_above_4_3=len(upper),
        median_rank_interval_width=(float(np.median(list(widths.values())))
                                    if widths else None),
        median_rank_interval_width_at_or_above_4_3=(
            float(np.median([widths[m] for m in upper])) if upper else None),
        neighbours_with_overlapping_bands=overlap_next,
        neighbour_pairs=len(order) - 1,
        reading="The old judge cannot rank the upper field: the median 95%% rank "
                "interval (same seed draws for every model) spans %s places, and "
                "%d of %d neighbouring pairs' bands overlap. Publish the band, "
                "never a position." % (
                    "%g" % float(np.median(list(widths.values()))) if widths else "n/a",
                    overlap_next, max(len(order) - 1, 0)))


# ---------------------------------------------------------------- rounds

def earlier_rounds(results):
    """Sessions of rounds 2 and 3, keyed sid -> transcript_hash, per file."""
    results = Path(results)
    out = {}
    for name in (R2_TRANSCRIPTS, R3_STANDARD, R3_NSFW):
        m = {}
        for s in read_json(results / name)["sessions"]:
            if "error" in s or "dialogue" not in s:
                continue
            m["%s::%s" % (s["test_model"], s["seed_id"])] = transcript_hash(s)
        out[name] = m
    return out


def r3_standard_scores(results):
    """June round-3 standard track, Sonnet 4 overall per session."""
    out = defaultdict(dict)
    for s in read_json(Path(results) / R3_STANDARD)["sessions"]:
        if "error" in s or "dialogue" not in s:
            continue
        v = L.stored_v1_overall(s)
        if v is not None:
            out[s["test_model"]][s["seed_id"]] = v
    return out


def r3_table(results):
    """The published round-3 table: position as published, tie ranges marked."""
    t = read_json(Path(results) / R3_TABLE)
    lb = t["leaderboard"]
    vals = [round(float(r["sonnet_overall"]), 2) for r in lb]
    if vals != sorted(vals, reverse=True):
        raise InputError("%s is not in published (descending craft) order" % R3_TABLE)
    out = {}
    for i, r in enumerate(lb):
        pos = [j + 1 for j, v in enumerate(vals) if v == vals[i]]
        tie = "%d-%d" % (pos[0], pos[-1]) if len(pos) > 1 else None
        out[r["model"]] = dict(
            rank=i + 1, tie=tie, of=len(lb), craft=vals[i], n=int(r["n"]),
            refusal_pct=r.get("refusal_rate_pct"),
            refusal_instrument="round 3's own: share of sessions a judge flagged "
                               "refused_midscene; not comparable with J")
    return out, t


def arena(results):
    h = read_json(Path(results) / ARENA)
    rows = {}
    for r in h["leaderboard"]:
        rows[r["model"]] = dict(elo=round(float(r["elo_mean"]), 1),
                                ci95=[round(float(r["ci_low_95"]), 1),
                                      round(float(r["ci_high_95"]), 1)],
                                n_votes=int(r["n_votes"]), rank=int(r["rank"]),
                                of=len(h["leaderboard"]))
    return rows, dict(votes=h.get("n_votes"), voters=h.get("n_voters"),
                      n_votes_not_scored=h.get("n_votes_not_scored"), source=ARENA)


def transcript_status(model, canon_by_model, earlier, r4_dates):
    """Identical to an earlier round's text, or regenerated."""
    sids = canon_by_model.get(model, {})
    if not sids:
        return dict(flag="no_round4_craft", identical=0, r4_sessions=0,
                    compared_with=None, generated=None)
    for name, label in ((R2_TRANSCRIPTS, "round 2"),
                        (R3_STANDARD, "round 3 standard track")):
        prev = {sid: h for sid, h in earlier[name].items()
                if sid.split("::")[0] == model}
        if not prev:
            continue
        same = sum(1 for sid, h in sids.items() if prev.get(sid) == h)
        flag = ("same" if same == len(sids)
                else "regenerated" if same == 0 else "mixed")
        return dict(flag=flag, identical=same, r4_sessions=len(sids),
                    compared_with=label, generated=r4_dates.get(model))
    return dict(flag="new_in_round4", identical=0, r4_sessions=len(sids),
                compared_with=None, generated=r4_dates.get(model))


def source_date(name):
    mo = re.search(r"_(\d{4})(\d\d)(\d\d)_\d{6}\.json$", name)
    if mo:
        return "%s-%s-%s" % mo.groups()
    return "2026-04/05 (round 2)" if name == R2_TRANSCRIPTS else name


# ---------------------------------------------------------------- blocks

def judge_bridge(v1m, v2m, sources_by_model, rng_seed):
    """Old vs new judge per model, core seeds, identical transcripts."""
    models = sorted(m for m in v1m if m in v2m)
    stored = [m for m in models if sources_by_model[m] <= {"stored_april", "stored_2026_09_21"}]
    backfill = [m for m in models if sources_by_model[m] == {"backfill_2026_09_27"}]
    ft = [m for m in models if m not in FINETUNES]
    ncnf = [m for m in ft if not is_claude(m)]
    upper = [m for m in models if v1m[m] >= 4.3]
    out = {}
    for key, ms, label in (
            ("all", models, "every model with all 12 core sessions"),
            ("stored_scores", stored, "old scores from April or 2026-09-21"),
            ("backfill_only", backfill, "old scores all from the 2026-09-27 backfill"),
            ("stored_scores_no_finetunes", [m for m in stored if m not in FINETUNES],
             "old scores from April or 2026-09-21, without the RP finetunes: "
             "like for like with backfill_only, which holds no finetune"),
            ("no_finetunes", ft, "without the RP finetunes"),
            ("non_claude_non_finetune", ncnf, "neither Claude nor a finetune"),
            ("old_judge_at_or_above_4_3", upper, "old-judge mean 4.3 or more")):
        out[key] = corr_block([v1m[m] for m in ms], [v2m[m] for m in ms],
                              "old judge (Sonnet 4), core seeds",
                              "new judge (Sonnet 5), same sessions",
                              rng_seed=rng_seed, note=label)
    def span(means, k):
        top = sorted((means[m] for m in models), reverse=True)
        return round(top[0] - top[k - 1], 2) if len(top) >= k else None
    out["spread"] = dict(
        models=len(models),
        old_top_26_span=span(v1m, 26), new_top_26_span=span(v2m, 26),
        old_sd=round(float(np.std([v1m[m] for m in models], ddof=1)), 3)
        if len(models) > 1 else None,
        new_sd=round(float(np.std([v2m[m] for m in models], ddof=1)), 3)
        if len(models) > 1 else None)
    offs = {m: v2m[m] - v1m[m] for m in models}
    cl = [offs[m] for m in models if is_claude(m)]
    ot = [offs[m] for m in models if not is_claude(m)]
    out["offset"] = dict(
        mean_new_minus_old=round(float(np.mean(list(offs.values()))), 3),
        claude=[round(min(cl), 2), round(max(cl), 2)] if cl else None,
        others=[round(min(ot), 2), round(max(ot), 2)] if ot else None,
        note="Per-model offsets are not a translation and are not published per "
             "model; they are here to show the offset is not one number.")
    return out


def model_drift(r3s, v1_all_by_model, canon_by_model, src_by_model, r4_dates):
    """June round-3 standard vs round 4, same judge, regenerated transcripts."""
    rows = {}
    for m in sorted(r3s):
        if m not in v1_all_by_model:
            continue
        seeds = sorted(set(r3s[m]) & set(v1_all_by_model[m]))
        if len(seeds) < 5:
            continue
        d = np.array([v1_all_by_model[m][s] - r3s[m][s] for s in seeds])
        se = float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else None
        date = r4_dates.get(m)
        same_setup = (date == "2026-09-21"
                      and src_by_model.get(m, set()) <= {"stored_2026_09_21"})
        rows[m] = dict(
            june=round(float(np.mean([r3s[m][s] for s in seeds])), 3),
            september=round(float(np.mean([v1_all_by_model[m][s] for s in seeds])), 3),
            change=round(float(d.mean()), 3), se=round(se, 3) if se else None,
            t=round(float(d.mean()) / se, 1) if se else None,
            seeds=len(seeds), finetune=m in FINETUNES, generated=date,
            setup=("same as June: 4096-token cap, judged inline" if same_setup
                   else "16384-token cap; old judge from the 2026-09-27 backfill"))
    same = [m for m, r in rows.items() if r["setup"].startswith("same")]
    same_nf = [m for m in same if not rows[m]["finetune"]]
    beyond = sorted(m for m, r in rows.items() if r["t"] is not None and abs(r["t"]) >= 2)
    summ = dict(
        models=len(rows), same_setup=len(same), same_setup_no_finetunes=len(same_nf),
        same_setup_no_finetunes_within_0_05=sum(
            1 for m in same_nf if abs(rows[m]["change"]) <= 0.05),
        mean_change_same_setup=round(float(np.mean([rows[m]["change"] for m in same])), 3)
        if same else None,
        beyond_2_se=beyond,
        rank_agreement_same_setup=(corr_block(
            [rows[m]["june"] for m in same], [rows[m]["september"] for m in same],
            "old judge, June transcripts", "old judge, September transcripts")
            if len(same) >= 4 else None),
        reading="Same judge, same seeds, same simulator; only the transcripts are "
                "new. Changes here are the models (and sampling), not the "
                "instrument. The 16384-cap rows also changed the token cap.")
    return dict(summary=summ, models=rows)


def ols_claude(y, ref, claude):
    X = np.column_stack([np.ones(len(ref)), ref, ref ** 2, claude.astype(float)])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    cov = (r @ r / dof) * np.linalg.inv(X.T @ X)
    return float(beta[3]), float(np.sqrt(cov[3, 3]))


def cross_family(results, canon, v1, v2, v1_src, rng_seed=RNG_SEED, B=None):
    """Claude-session coefficient of each Claude judge over a non-Claude
    reference, controlling for the reference score and its square, on
    hash-identical transcripts (skeptic's table, recomputed)."""
    B = XFAM_BOOT if B is None else B
    out = dict(method="OLS of judge score on [1, reference, reference^2, is-Claude "
                      "model] over sessions every judge scored on the same "
                      "transcript; blank scenes left out. SE is the session OLS "
                      "SE; the interval resamples models (all their sessions come "
                      "along), %d draws." % B,
               references={})
    for fam, (label, parts) in REFERENCES.items():
        got = {}
        for pkg, sub in parts:
            d = Path(results) / pkg / sub
            if not d.exists():
                got = None
                break
            s, _ = OV.load_external_scores(d, canon)
            got.update(s)
        if got is None:
            out["references"][fam] = dict(label=label, skipped="package missing")
            continue
        fam_out = dict(label=label)
        for scope, keep in (("stored_old_scores", lambda sid: v1_src[sid] != "backfill_2026_09_27"),
                            ("all_old_scores", lambda sid: True)):
            sids = sorted(sid for sid in got if sid in v1 and sid in v2
                          and not canon[sid]["blank_scene"] and keep(sid))
            if len(sids) < 20:
                fam_out[scope] = dict(sessions=len(sids), skipped="under 20 sessions")
                continue
            ref = np.array([got[s] for s in sids])
            a = np.array([v1[s] for s in sids])
            b = np.array([v2[s] for s in sids])
            models = [canon[s]["model"] for s in sids]
            cl = np.array([is_claude(m) for m in models])
            roster = sorted(set(models))
            by = defaultdict(list)
            for i, m in enumerate(models):
                by[m].append(i)
            rng = np.random.default_rng(rng_seed)
            block = dict(sessions=len(sids), models=len(roster),
                         claude_sessions=int(cl.sum()),
                         claude_models=len({m for m in models if is_claude(m)}),
                         r_reference_old=round(pearson(ref, a), 3),
                         r_reference_new=round(pearson(ref, b), 3))
            for name, y in (("old_judge", a), ("new_judge", b), ("new_minus_old", b - a)):
                coef, se = ols_claude(y, ref, cl)
                draws = []
                for _ in range(B):
                    pick = rng.integers(0, len(roster), len(roster))
                    ii = np.concatenate([by[roster[k]] for k in pick])
                    if cl[ii].any() and (~cl[ii]).any():
                        try:
                            draws.append(ols_claude(y[ii], ref[ii], cl[ii])[0])
                        except np.linalg.LinAlgError:
                            continue
                lo, hi = np.percentile(draws, [2.5, 97.5])
                block[name] = dict(claude_coefficient=round(coef, 3), se=round(se, 3),
                                   t=round(coef / se, 1),
                                   ci95_model_resampled=[round(float(lo), 3),
                                                         round(float(hi), 3)])
            fam_out[scope] = block
        out["references"][fam] = fam_out
    out["reading"] = ("Positive means the Claude judge scores Claude-model sessions "
                      "higher than the reference does, relative to non-Claude "
                      "sessions at the same reference score. The new judge's "
                      "coefficient is larger than the old judge's against both "
                      "references; read it as a Claude-family uplift in the new "
                      "judge that the old judge shows less of, not as proof of "
                      "which judge is right.")
    return out


def willingness_block(r3t, jfile):
    wl = {r["model"]: r for r in jfile["leaderboard"]}
    ms = sorted(m for m in r3t if m in wl and wl[m].get("J") is not None)
    zeros = [m for m in r3t if r3t[m]["refusal_pct"] == 0]
    r4_rows = [m for m in zeros if m in wl and wl[m].get("over_refusal_hard_rungs") is not None]
    over = [wl[m]["over_refusal_hard_rungs"] for m in r4_rows]
    return dict(
        comparable=False,
        why=["the seeds changed (20 NSFW seeds without a script vs scripted L1-L5 ladders)",
             "the instrument changed (a flag in the judge JSON vs a per-rung classifier)",
             "the construct changed (outright refusal vs any non-engagement, 97% "
             "of it soft deflection)",
             "about three months of provider drift (2026-06-08 vs 2026-08-06 to "
             "2026-09-25)"],
        r3_models_at_zero=len(zeros), r3_models=len(r3t),
        r3_zero_models_with_a_round4_row=len(r4_rows),
        their_round4_over_refusal=[round(min(over), 2), round(max(over), 2)] if over else None,
        r3_refusal_vs_J=corr_block([r3t[m]["refusal_pct"] for m in ms],
                                   [wl[m]["J"] for m in ms],
                                   "round-3 refusal %", "round-4 J",
                                   note="for the record: no usable link"),
        publish="round 3's refusal % as it is, labelled as round 3's instrument; "
                "never beside a round-4 refusal figure as one series")


def forbidden_hits(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_KEYS:
                yield "%s.%s" % (path, k)
            yield from forbidden_hits(v, "%s.%s" % (path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from forbidden_hits(v, "%s[%d]" % (path, i))


# ---------------------------------------------------------------- build

def build(results, rng_seed=RNG_SEED, boot=BOOT):
    results = Path(results)
    canon, v2, v1, v1_src = load_scores(results)
    ov = read_json(results / OVERVIEW)
    jfile = read_json(results / J_FILE)
    r3t, _ = r3_table(results)
    hum, hum_meta = arena(results)
    earlier = earlier_rounds(results)
    r3s = r3_standard_scores(results)

    all_seeds = sorted({c["seed"] for c in canon.values()})
    core = core_seeds(all_seeds)
    if len(core) != CORE[1] - CORE[0] + 1:
        raise InputError("core seeds %02d-%02d: found %d" % (CORE[0], CORE[1], len(core)))
    blank_in_core = sorted(sid for sid, c in canon.items()
                           if c["blank_scene"] and c["seed"] in core)

    v1_core = per_model(v1, canon, set(core))
    v2_core = per_model(v2, canon, set(core))
    v1_all = per_model(v1, canon)
    old_bands, v1_means, widths = bands(v1_core, core, B=boot, rng_seed=rng_seed)
    v2_means = {m: float(np.mean([d[s] for s in core]))
                for m, d in v2_core.items() if all(s in d for s in core)}

    canon_by_model = defaultdict(dict)
    src_files = defaultdict(Counter)
    for sid, c in canon.items():
        canon_by_model[c["model"]][sid] = c["hash"]
        src_files[c["model"]][c["source"]] += 1
    r4_dates = {m: ", ".join(sorted({source_date(f) for f in files}))
                for m, files in src_files.items()}
    src_by_model = defaultdict(set)
    for sid, s in v1_src.items():
        if canon[sid]["seed"] in core:
            src_by_model[canon[sid]["model"]].add(s)
    src_by_model_all = defaultdict(set)
    for sid, s in v1_src.items():
        src_by_model_all[canon[sid]["model"]].add(s)

    # ---- roster
    craft = set(canon_by_model)
    j_models = {r["model"] for r in jfile["leaderboard"]}
    r4 = craft | j_models
    r2 = {sid.split("::")[0] for sid in earlier[R2_TRANSCRIPTS]}
    r3 = ({sid.split("::")[0] for sid in earlier[R3_STANDARD]}
          | {sid.split("::")[0] for sid in earlier[R3_NSFW]})
    returning = sorted((r2 | r3) & r4)
    new = sorted(r4 - set(returning))
    gone = sorted((r2 | r3) - r4)

    ov_rows = {r["model"]: r for r in ov["rows"] + ov.get("unranked", [])}
    ov_absent = {r["model"]: r for r in ov.get("absent", [])}
    jm = ov["judge_means"]["models"]
    wl = {r["model"]: r for r in jfile["leaderboard"]}
    band_label = {r["tier"]: r["label"] for r in ov["bands"]["ranges"]}

    def j_cell(m):
        cell = (ov_rows.get(m) or ov_absent.get(m) or {}).get("J")
        if cell is None and m not in wl:
            return None
        w = wl.get(m, {})
        return dict(value=(cell or {}).get("value", w.get("J")),
                    display=(cell or {}).get("display"),
                    rank=w.get("rank"), ranked=bool(w.get("ranked")),
                    of=sum(1 for r in jfile["leaderboard"] if r.get("ranked")),
                    unranked_reason=w.get("unranked_reason"))

    def old_cell(m):
        if m in old_bands:
            b = dict(old_bands[m])
            srcs = src_by_model[m]
            b["scores"] = ("stored" if srcs <= {"stored_april", "stored_2026_09_21"}
                           else "backfill" if srcs == {"backfill_2026_09_27"}
                           else "mixed")
            return b
        return None

    def old_reason(m):
        if m not in canon_by_model:
            return "no round-4 craft transcripts"
        have = len([s for s in v1_core.get(m, {})])
        return "%d of the 12 core seeds" % have

    rows = []
    for m in returning:
        rounds = []
        if m in r2:
            rounds.append("round 2")
        if m in r3:
            rounds.append("round 3")
        st = transcript_status(m, canon_by_model, earlier, r4_dates)
        h = hum.get(m)
        if h is not None:
            h = dict(h, voted_transcripts=("identical to round 4"
                                           if st["flag"] == "same"
                                           else "regenerated since the vote"))
        tier = (jm.get(m) or {}).get("tier")
        rows.append(dict(
            model=m, rounds=rounds, finetune=m in FINETUNES,
            round4=("craft and J" if m in craft and (j_cell(m) or {}).get("value") is not None
                    else "craft only" if m in craft
                    else "Track A only"),
            r2_human=h,
            r3_nsfw=r3t.get(m),
            old_judge_r4=old_cell(m),
            old_judge_r4_missing=None if m in old_bands else old_reason(m),
            v2_tier=(dict(tier=tier, band=band_label[tier]) if tier else None),
            J=j_cell(m),
            same_transcripts=st))

    # ---- correlations
    corr = []
    ms = sorted(set(v1_means) & set(v2_means))
    corr.append(dict(id="old_vs_new_judge", **corr_block(
        [v1_means[m] for m in ms], [v2_means[m] for m in ms],
        "old judge (Sonnet 4)", "new judge (Sonnet 5)", rng_seed=rng_seed,
        note="identical transcripts, 12 core seeds, every banded model")))
    ret_craft = [m for m in returning if m in v1_means and m in v2_means]
    corr.append(dict(id="old_vs_new_judge_returning", **corr_block(
        [v1_means[m] for m in ret_craft], [v2_means[m] for m in ret_craft],
        "old judge (Sonnet 4)", "new judge (Sonnet 5)", rng_seed=rng_seed,
        note="identical transcripts, returning models only")))
    ms = sorted(m for m in r3t if m in v2_means)
    corr.append(dict(id="r3_nsfw_vs_new_judge", **corr_block(
        [r3t[m]["craft"] for m in ms], [v2_means[m] for m in ms],
        "round-3 NSFW craft (published)", "round-4 new judge", rng_seed=rng_seed,
        note="track and judge both changed")))
    nf = [m for m in ms if m not in FINETUNES]
    corr.append(dict(id="r3_nsfw_vs_new_judge_no_finetunes", **corr_block(
        [r3t[m]["craft"] for m in nf], [v2_means[m] for m in nf],
        "round-3 NSFW craft (published)", "round-4 new judge", rng_seed=rng_seed,
        note="without the RP finetunes: the order inside round 3's tied frontier")))
    ms = sorted(m for m in r3t if m in v1_means)
    corr.append(dict(id="r3_nsfw_vs_old_judge", **corr_block(
        [r3t[m]["craft"] for m in ms], [v1_means[m] for m in ms],
        "round-3 NSFW craft (published)", "round-4 old judge", rng_seed=rng_seed,
        note="same judge, track changed")))
    same_h = sorted(m for m in hum if m in v1_means and m in v2_means
                    and transcript_status(m, canon_by_model, earlier, r4_dates)["flag"] == "same")
    all_h = sorted(m for m in hum if m in v1_means and m in v2_means)
    for tag, group, note in (
            ("", same_h, "voters read these exact transcripts"),
            ("_incl_regenerated", all_h, "includes kimi_k2_6, regenerated after the vote")):
        corr.append(dict(id="human_vs_old_judge" + tag, **corr_block(
            [hum[m]["elo"] for m in group], [v1_means[m] for m in group],
            "round-2 human arena ELO", "old judge (Sonnet 4)", rng_seed=rng_seed,
            note=note)))
        corr.append(dict(id="human_vs_new_judge" + tag, **corr_block(
            [hum[m]["elo"] for m in group], [v2_means[m] for m in group],
            "round-2 human arena ELO", "new judge (Sonnet 5)", rng_seed=rng_seed,
            note=note)))
    diff = paired_rho_difference([hum[m]["elo"] for m in same_h],
                                 [v2_means[m] for m in same_h],
                                 [v1_means[m] for m in same_h], rng_seed=rng_seed)
    diff.update(id="human_new_minus_old", n=len(same_h),
                x="rho(human, new judge) - rho(human, old judge)")
    corr.append(diff)
    hj = sorted(m for m in hum if m in wl and wl[m].get("J") is not None)
    hjb = corr_block([hum[m]["elo"] for m in hj], [wl[m]["J"] for m in hj],
                     "round-2 human arena ELO", "round-4 J", rng_seed=rng_seed,
                     note="undetermined: the interval covers almost the whole range")
    corr.append(dict(id="human_vs_J", **hjb))

    # what the round-2 arena showed: the merged_all_v2 sessions of its models
    shown = {sid: h for sid, h in earlier[R2_TRANSCRIPTS].items()
             if sid.split("::")[0] in hum}
    same_shown = [sid for sid, h in shown.items()
                  if sid in canon and canon[sid]["hash"] == h]
    hum_meta.update(
        sessions_shown=len(shown), sessions_identical_in_round4=len(same_shown),
        models=len(hum),
        models_all_identical=sum(
            1 for m in hum
            if all(canon.get(sid, {}).get("hash") == h
                   for sid, h in shown.items() if sid.split("::")[0] == m)))
    by_src = Counter(v1_src[sid] for sid in v1)
    out = dict(
        title="Round 4 and earlier rounds",
        generated_by="analyze_round4_continuity.py",
        read_this_first=(
            "Round 4 changed the instruments, not the models. Each returning "
            "model's row sets its earlier-round figures beside the round-4 ones "
            "without converting any of them: the old judge is the round-2/3 "
            "judge re-run on round-4 transcripts and is a band, never a rank; "
            "the round-4 judge is a letter; J is new. Nothing is summed."),
        roster=dict(
            round4_models=len(r4), craft_models=len(craft), j_rows=len(j_models),
            returning=len(returning),
            returning_craft=sum(1 for m in returning if m in craft),
            returning_track_a_only=sorted(m for m in returning if m not in craft),
            new=len(new), new_models=new,
            not_returning=[dict(model=m, note=NOT_RETURNING_NOTES.get(m))
                           for m in gone]),
        instruments=INSTRUMENTS,
        core_seeds=dict(
            seeds=core, blank_scenes_in_core=blank_in_core,
            why="The eight round-2 models that played 12 seeds played these 12, "
                "and seven of them still have only these 12 in round 4 "
                "(kimi_k2_6 was regenerated on all 20); every model with a full "
                "run has them. One set for every "
                "cross-model figure here, so no seed mix moves a model."),
        old_judge=dict(
            judge=OLD_JUDGE_ID, prompt_hash=LEGACY_PROMPT,
            temperature=L.EXPECTED_JUDGE_CONFIG["temperature"],
            scores_by_source=dict(sorted(by_src.items())),
            sessions=len(v1), corpus_sessions=len(canon),
            band_rule="mean of the 12 core-seed sessions +/- half the width of "
                      "the 95%% percentile interval from %d seed resamples "
                      "(numpy default_rng(%d), the same draws for every model)"
                      % (boot, rng_seed),
            drift_gate=("passed 2026-09-27 before the backfill: 40 re-judged "
                        "sessions, mean new minus stored 0.000 (SE 0.015), "
                        "Pearson 0.991. Post hoc, outside the frozen criteria: "
                        "sessions stored in April came back +0.0375 (n=16) and "
                        "those stored on 2026-09-21 -0.025 (n=24), a gap of "
                        "+0.06 (SE 0.03, t about 2.2), so the rows scored in "
                        "April may sit about 0.06 low against those scored in "
                        "September. Claude minus non-Claude was +0.048 (SE "
                        "0.03), partly confounded with that era gap (Claude "
                        "sessions are 6 of 16 in April, 6 of 24 in September); "
                        "40 sessions cannot separate the two, and neither was "
                        "a gate criterion."),
            scale=scale_note(v1_means, widths, old_bands),
            models=old_bands,
            not_banded={m: old_reason(m) for m in sorted(craft) if m not in old_bands}),
        rows=rows,
        correlations=corr,
        judge_bridge=judge_bridge(v1_means, v2_means, src_by_model, rng_seed),
        model_drift=model_drift(r3s, v1_all, canon_by_model, src_by_model_all, r4_dates),
        cross_family=cross_family(results, canon, v1, v2, v1_src, rng_seed=rng_seed),
        willingness=willingness_block(r3t, jfile),
        human_arena=hum_meta,
        pending=dict(
            chatgpt_full_package=("results/judge_full_chatgpt: a blind package over "
                                  "all 1,328 sessions, no parts returned yet; when "
                                  "it returns it is a non-Claude column for every "
                                  "model")),
        not_published=["a per-model translation of the new judge onto the old scale",
                       "a synthetic composite", "a cross-round refusal column",
                       "a rank on the old judge"],
        inputs={name: OV.sha(results / name) for name in (
            V2_FILE, LEGACY_FILE, R3_STANDARD, R3_NSFW, R3_TABLE, ARENA, OVERVIEW,
            J_FILE, *[os.path.basename(p) for p in OV.session_sources(results)])
            if (results / name).exists()},
    )
    hits = list(forbidden_hits(out))
    if hits:
        raise InputError("output carries forbidden keys: %s" % hits)
    return out


# ---------------------------------------------------------------- render

def _fmt_h(h):
    if not h:
        return ""
    mark = "" if h["voted_transcripts"].startswith("identical") else "§"
    return "%d [%d, %d] (%d)%s" % (round(h["elo"]), round(h["ci95"][0]),
                                   round(h["ci95"][1]), h["n_votes"], mark)


def _fmt_r3(r):
    if not r:
        return ""
    if r["tie"]:
        return "#%d (%.2f, tie %s)" % (r["rank"], r["craft"], r["tie"])
    return "#%d (%.2f)" % (r["rank"], r["craft"])


def _fmt_old(b):
    return "%.2f ± %.2f" % (b["mean"], b["half_width"]) if b else ""


def _fmt_j(j, row=None):
    if not j or j.get("value") is None:
        return "no J (Track A only)" if (row or {}).get("round4") == "Track A only" else "no J"
    if j["ranked"]:
        return "%s (#%d)" % (j["display"], j["rank"])
    return "%s unranked" % (j["display"] or "%+.2f" % j["value"]).split(" ")[0]


def _fmt_tx(st):
    if st["flag"] == "same":
        return "same as R2 (%d)" % st["r4_sessions"]
    if st["flag"] == "regenerated":
        return "regen. %s (%d)" % (st["generated"], st["r4_sessions"])
    if st["flag"] == "no_round4_craft":
        return "no R4 craft"
    return "%s (%d of %d same)" % (st["flag"], st["identical"], st["r4_sessions"])


def render_markdown(doc):
    """The returning-models table and the correlation line, for the README.

    Rows go by round-4 tier letter, then alphabetically, as the overview's do:
    never by the old judge, which would make its column a rank."""
    order = sorted(doc["rows"], key=lambda r: (
        (r["v2_tier"] or {}).get("tier") or "Z", r["model"]))
    lines = ["| Model | R2 human ELO [95%] (votes) | R3 NSFW # (craft) | "
             "R3 refusal % | Old judge on R4 | R4 tier | J | R4 transcripts |",
             "|---|---|---|---|---|---|---|---|"]
    for r in order:
        r3 = r["r3_nsfw"]
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["model"], _fmt_h(r["r2_human"]), _fmt_r3(r3),
            "" if not r3 or r3["refusal_pct"] is None else "%g" % r3["refusal_pct"],
            _fmt_old(r["old_judge_r4"]) or ("n/a (%s)" % r["old_judge_r4_missing"]),
            (r["v2_tier"] or {}).get("tier") or (
                "untiered" if r["same_transcripts"]["r4_sessions"] else ""),
            _fmt_j(r["J"], r),
            _fmt_tx(r["same_transcripts"])))
    c = {x["id"]: x for x in doc["correlations"]}

    def one(k):
        x = c[k]
        if x.get("spearman") is None:
            return "n/a, n=%d" % x["n"]
        return "%.2f [%.2f, %.2f], n=%d" % (x["spearman"], x["ci95"][0], x["ci95"][1], x["n"])
    corr = ("Spearman [95%%]: old vs new judge on identical transcripts %s; "
            "round-3 NSFW table vs new judge %s (no finetunes %s); round-2 humans "
            "vs old judge %s, vs new judge %s; humans vs J undetermined (n=%d)."
            % (one("old_vs_new_judge"), one("r3_nsfw_vs_new_judge"),
               one("r3_nsfw_vs_new_judge_no_finetunes"), one("human_vs_old_judge"),
               one("human_vs_new_judge"), c["human_vs_J"]["n"]))
    return "\n".join(lines) + "\n\n" + corr + "\n"


def summary(doc):
    ro = doc["roster"]
    out = ["round 4: %d models, %d returning (%d craft, Track A only: %s), %d new"
           % (ro["round4_models"], ro["returning"], ro["returning_craft"],
              ", ".join(ro["returning_track_a_only"]), ro["new"])]
    for x in doc["correlations"]:
        if "spearman" in x and x.get("spearman") is not None:
            out.append("  %-40s rho %+.3f %s n=%d" % (x["id"], x["spearman"],
                                                    x["ci95"], x["n"]))
        elif x.get("difference") is not None:
            out.append("  %-40s diff %+.3f %s n=%d" % (x["id"], x["difference"],
                                                     x["ci95"], x["n"]))
    return "\n".join(out)


def dump(obj, path):
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out", default=None, help="default: <results>/%s" % OUT)
    ap.add_argument("--boot", type=int, default=BOOT)
    ap.add_argument("--rng-seed", type=int, default=RNG_SEED)
    ap.add_argument("--markdown", default=None,
                    help="also write the README table and correlation line here")
    a = ap.parse_args(argv)
    try:
        doc = build(a.results, rng_seed=a.rng_seed, boot=a.boot)
    except OV.InputError as e:
        print("FAIL CLOSED, nothing written.\n%s" % e, file=sys.stderr)
        return 2
    out = Path(a.out or Path(a.results) / OUT)
    dump(doc, out)
    if a.markdown:
        Path(a.markdown).write_text(render_markdown(doc))
    print(summary(doc))
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
