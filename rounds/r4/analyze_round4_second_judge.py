#!/usr/bin/env python3
"""Round 4: a second judge family over the whole craft corpus.

The round-4 judge tier is one judge's letter (Claude Sonnet 5, session judge
v2). ChatGPT, run blind in Codex on a ChatGPT subscription, has now scored
every one of the 1,328 craft sessions against the same rubric
(results/judge_full_chatgpt/merged: 1,149 Codex rows plus 179 rows reused
from the earlier blind ChatGPT passes on byte-identical text). This writes
what the two families agree on, what they do not, and what that does to the
round-4 letters, in results/round4_second_judge.json:

  session_agreement   per session, overall and S.1 / S.3 / S.5: Pearson and
                      Spearman with n and a model-resampled 95% interval, mean
                      and median difference
  model_agreement     per model, on the overview's own basis (the model + seed
                      fit, so the 12-seed models are set on all 20 seeds the
                      way their tier is), the same statistics across models,
                      and inside and outside Sonnet's A letter (15b re-measured)
  scale               ChatGPT's global scale offset: how it is estimated, its
                      intervals, and the difference in spread it does not undo
  models              one row per model: both judges' means with their seed-
                      bootstrap intervals, ChatGPT's letter raw and after the
                      offset, the difference after the offset with its
                      interval, and whether the letter depends on the judge
  tiers               how many models keep their letter, which move and by how
                      much (raw, after the offset, and after a mean-and-spread
                      rescale as a sensitivity)
  vendor_premiums     Sonnet's Claude premium over ChatGPT and ChatGPT's OpenAI
                      premium over Sonnet: the skeptic's regression (score on
                      the other judge's score and its square plus a vendor
                      term), the same regression the other way round, and the
                      direction-free rescaled difference, each with a model-
                      resampled interval; and what removing each does to the
                      letters
  bridge              the 24 sessions scored in two ChatGPT runs: the Codex
                      pass and the earlier blind passes, each with its own
                      raters (the keys keep their old names: `app` is the
                      Codex pass, `agent` the earlier passes)
  sensitivity         the headline figures without the 179 reused rows,
                      without the 24 bridge sessions, both, and with the bridge
                      sessions on their rows from the earlier passes
  reading             what the full corpus can and cannot establish

Nothing here sets a letter. The published tier stays Sonnet's; the overview
carries ChatGPT's per-model mean, its raw letter and `tier_depends_on_judge`
(rounds/r4/analyze_round4_overview.py, whose functions this file uses so the two cannot
drift). Which judge is right is not a question this data can answer (sec
"reading").

Deterministic: fixed seeds, sorted keys. The seed bootstrap replays the
overview's own draws (numpy default_rng(analyze_round4_overview.RNG_SEED), the
same B), so Sonnet's intervals and edge marks here are the overview's.

Inputs, read-only:
    results/craft_baseline_*.json, results/multiturn_merged_all_v2.json
                                     transcripts (newest copy wins)
    results/session_judge_v2.jsonl   Sonnet 5, validated fail-closed by the
                                     overview's own rule
    results/judge_full_chatgpt/merged/       ChatGPT on every session
    results/judge_full_chatgpt/_manifest.json  the package keymap: which
                                     sessions are bridge sessions, and where
                                     their rows from the earlier passes are
    results/judge_{round2,inc1}_chatgpt/external_blind_pass/  those rows

Fails closed on a ChatGPT row that fails the rubric schema, an id missing
from the keymap, or a session with two rows. A row judged on a transcript that
has since been replaced is dropped and counted, as the overview does.

Usage:
    python3 rounds/r4/analyze_round4_second_judge.py
    python3 rounds/r4/analyze_round4_second_judge.py --seed-boot 2000 --model-boot 1000
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rounds.r4 import analyze_round4_overview as OV  # noqa: E402  (corpus, fits, letters)
from lib.external_judge_schema import validate_row  # noqa: E402

OUT = "round4_second_judge.json"
PACKAGE = "judge_full_chatgpt"
MERGED = PACKAGE + "/merged"
KEYMAP = PACKAGE + "/_manifest.json"
APP_SOURCE = PACKAGE + "/app_pass"
NAME = "chatgpt"
LABEL = OV.CROSS_LABELS[NAME]
DIMS = OV.DIMENSIONS                       # overall, S.5, S.1, S.3
DIM_LABEL = {"overall": "overall", "S.5_agency_respect_session": "S.5 agency",
             "S.1_consistency_over_time": "S.1 consistency",
             "S.3_narrative_momentum": "S.3 momentum"}
RNG_SEED = 20260928                        # model resampling
SEED_BOOT = OV.BOOT_DEFAULT                # the overview's B, the overview's draws
MODEL_BOOT = 4000
FLOOR = 1.0                                # both judges at the floor: no text
BAND = OV.CROSS_FLAG                       # the card's 0.3

GROUPS = {
    "claude": ("Claude models (claude_*)", lambda m: m.startswith("claude_")),
    "openai": ("OpenAI models (gpt_*)", lambda m: m.startswith("gpt_")),
    "gpt_6": ("the GPT-6 family (gpt_6_*)", lambda m: m.startswith("gpt_6_")),
    "gpt_6_astra": ("gpt_6_astra alone", lambda m: m == "gpt_6_astra"),
}

# Earlier figures this file re-measures, as published (ROUND4_DESIGN 15, 17,
# 18; round4_overview.json checks; round4_continuity.json cross_family).
EARLIER = dict(
    session_r_overall=dict(value=0.716, n=117, source="ROUND4_DESIGN 17a: the blind "
                                                      "ChatGPT pass on the 120-session sample"),
    model_r_overall=dict(value=0.797, n=None, source="ROUND4_DESIGN 18: sonnet vs "
                                                     "chatgpt per model on that sample"),
    mean_gap=dict(value=0.77, source="ROUND4_DESIGN 17a/18: Sonnet minus ChatGPT, "
                                     "blind pass, 120-session sample"),
    claude_tilt=dict(value=0.200, ci95=[-0.013, 0.406], n=203,
                     source="round4_overview.json checks.self_preference: Sonnet over "
                            "ChatGPT, Claude minus non-Claude, rescaled"),
    claude_premium_change=dict(value=0.304, ci95=[0.138, 0.466], n=110,
                               source="round4_continuity.json (before this file): new "
                                      "judge minus old judge, Claude coefficient vs "
                                      "ChatGPT, stored old scores"),
    openai_gap=dict(value=0.57, n=7, source="ROUND4_DESIGN 17b: OpenAI against the "
                                            "rest, blind pass, 7 OpenAI sessions"),
)
REFERENCE = dict(
    sonnet_vs_sonnet=dict(r=0.908, median_abs_diff=0.20,
                          source="ROUND4_DESIGN 14/17c, 120 sessions"),
    chatgpt_vs_chatgpt_same_harness=dict(r=0.935, median_abs_diff=0.15,
                                         source="ROUND4_DESIGN 17c: the two earlier "
                                                "ChatGPT passes (labels visible, then "
                                                "blind), 120 sessions"),
    gemini_harness_shift=dict(mean_diff=-0.39, r=0.958,
                              source="ROUND4_DESIGN 18c: Gemini chat client vs API, "
                                     "same sessions"),
)


class InputError(OV.InputError):
    """An input fails a check; nothing is written."""


def read_json(path):
    with open(path) as fh:
        return json.load(fh)


def r3(v):
    return None if v is None else round(float(v), 3)


def r4(v):
    return None if v is None else round(float(v), 4)


def ci(draws, dp=3):
    d = np.asarray(draws, float)
    d = d[np.isfinite(d)]
    if not len(d):
        return None
    lo, hi = np.percentile(d, [2.5, 97.5])
    return [round(float(lo), dp), round(float(hi), dp)]


# ------------------------------------------------------------------ inputs

def row_scores(r):
    """overall and the three session dimensions of one ChatGPT row."""
    out = {"overall": float(r["overall"])}
    for d in DIMS[1:]:
        v = r["session_dimensions"][d]
        out[d] = float(v["score"] if isinstance(v, dict) else v)
    return out


def load_package(pkg_dir, canon):
    """({sid: scores}, {sid: source}, meta) from a merged package directory.

    Fails closed on a row that fails the rubric schema, an id not in the
    package keymap, or two rows for one session. A row judged on a transcript
    that has since been replaced is dropped and counted."""
    pkg_dir = Path(pkg_dir)
    man = read_json(pkg_dir / "_manifest.json")
    keymap = man.get("keymap") or {}
    hashes = man.get("transcript_hashes") or {}
    sources = man.get("sources") or {}
    out, src, problems = {}, {}, []
    stale = unmatched = 0
    files = sorted(pkg_dir.glob("external_part*.json"))
    if not files:
        raise InputError("%s: no external_part*.json" % pkg_dir)
    for f in files:
        for i, r in enumerate(read_json(f)):
            oid = r.get("session_id") if isinstance(r, dict) else None
            if oid not in keymap:
                problems.append("%s row %d: id %r not in the keymap" % (f.name, i, oid))
                continue
            errs = validate_row(r)
            if errs:
                problems.append("%s %s: %s" % (f.name, oid, "; ".join(errs[:2])))
                continue
            sid = keymap[oid]
            if sid in out:
                problems.append("%s: a second row for %s" % (f.name, sid))
                continue
            if sid not in canon:
                unmatched += 1
                continue
            if (r.get("transcript_hash") or hashes.get(sid)) != canon[sid]["hash"]:
                stale += 1
                continue
            out[sid] = row_scores(r)
            src[sid] = sources.get(oid, "unknown")
    if problems:
        raise InputError("%s fails closed (%d problems):\n  %s"
                         % (pkg_dir, len(problems), "\n  ".join(problems[:30])))
    return out, src, dict(files=[f.name for f in files], stale_dropped=stale,
                          unmatched_dropped=unmatched)


def load_bridge(results, canon):
    """{sid: earlier-pass scores} for the package's bridge sessions: the
    earlier blind ChatGPT rows on the same text, from the package keymap's
    `reused` references. Empty when the keymap is not here."""
    kp = Path(results) / KEYMAP
    if not kp.exists():
        return {}, []
    man = read_json(kp)
    bridge = sorted(man.get("bridge") or [])
    cache, out, problems = {}, {}, []
    for sid in bridge:
        ref = (man.get("reused") or {}).get(sid)
        if not ref:
            problems.append("%s: bridge session with no reused reference" % sid)
            continue
        f = Path(results).parent / ref["package"] / ref["subdir"] / ref["file"]
        if f not in cache:
            cache[f] = {r["session_id"]: r for r in read_json(f)}
        row = cache[f].get(ref["opaque"])
        if row is None or validate_row(row):
            problems.append("%s: earlier-pass row missing or invalid" % sid)
            continue
        if sid not in canon or ref.get("transcript_hash") != canon[sid]["hash"]:
            problems.append("%s: earlier-pass row scored another text" % sid)
            continue
        out[sid] = row_scores(row)
    if problems:
        raise InputError("bridge rows fail closed:\n  " + "\n  ".join(problems[:20]))
    files = sorted(str(p.relative_to(Path(results).parent)) for p in cache)
    return out, files


# ------------------------------------------------------------------ statistics

def avg_ranks(v):
    """0-based ranks, ties averaged."""
    u, inv, cnt = np.unique(np.asarray(v, float), return_inverse=True, return_counts=True)
    start = np.cumsum(cnt) - cnt
    return (start + (cnt - 1) / 2.0)[inv]


def pearson(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def spearman(a, b):
    return pearson(avg_ranks(a), avg_ranks(b))


def model_picks(n_models, B, rng_seed):
    """B draws of n_models model indexes, with replacement."""
    rng = np.random.default_rng(rng_seed)
    return rng.integers(0, n_models, size=(B, n_models))


def session_index_draws(models, B, rng_seed):
    """For each of B model resamples, the session indexes it carries (every
    session of a drawn model comes along, once per draw of it)."""
    roster = sorted(set(models))
    by = defaultdict(list)
    for i, m in enumerate(models):
        by[m].append(i)
    arr = [np.asarray(by[m], int) for m in roster]
    return [np.concatenate([arr[k] for k in pick])
            for pick in model_picks(len(roster), B, rng_seed)]


def agreement(a, b, draws=None):
    """Pearson and Spearman with their resampled intervals, and the
    differences (a minus b)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    out = dict(n=int(len(a)), pearson=r3(pearson(a, b)), spearman=r3(spearman(a, b)))
    if draws is not None:
        out["pearson_ci95"] = ci([pearson(a[ii], b[ii]) for ii in draws])
        out["spearman_ci95"] = ci([spearman(a[ii], b[ii]) for ii in draws])
    out.update(mean_diff=r3(d.mean()), median_abs_diff=r3(np.median(np.abs(d))),
               within_0_5=r3(np.mean(np.abs(d) <= 0.5 + 1e-9)))
    return out


def ols_group(y, ref, g):
    """The skeptic's regression: y on [1, ref, ref^2, g]; the g coefficient
    and its session OLS SE."""
    X = np.column_stack([np.ones(len(ref)), ref, ref ** 2, g.astype(float)])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    cov = (res @ res / dof) * np.linalg.pinv(X.T @ X)
    return float(beta[3]), float(np.sqrt(max(cov[3, 3], 0.0)))


def tier_index_array(v):
    v = np.asarray(v, float)
    return (v[..., None] < np.asarray(OV.TIER_EDGES) - OV.EDGE_EPS).sum(-1)


def letter(i):
    return OV.TIERS[int(i)][0]


def confusion(a, b):
    """{letter under a: {letter under b: n}} over the letters that occur."""
    out = defaultdict(Counter)
    for x, y in zip(a, b):
        out[x][y] += 1
    return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}


# ------------------------------------------------------------------ pieces

def fit_means(rows, pool, dim="overall"):
    """Sonnet's per-model means on the overview's basis, over `pool`."""
    p, _, seeds, X, _ = OV.build_matrix(rows, pool=pool, dim=dim)
    return dict(zip(p, (float(v) for v in OV.seed_adjusted_means(X)))), seeds, X


def aligned_matrix(scores, rows, pool, seeds, dim="overall"):
    """The second judge's seeds x models matrix on Sonnet's seed order."""
    crow = OV.other_judge_rows(scores, rows, dim)
    p2, _, s2, XC, _ = OV.build_matrix(crow, pool=pool, dim=dim)
    X = np.full((len(seeds), len(pool)), np.nan)
    for j, m in enumerate(p2):
        for i, s in enumerate(s2):
            X[seeds.index(s), pool.index(m)] = XC[i, j]
    return X


def seed_bootstrap(X, XC, B, rng_seed=OV.RNG_SEED):
    """The overview's seed draws (same generator, same order), for both
    judges at once. Returns (Sonnet means, ChatGPT means), each B x models."""
    S = X.shape[0]
    rng = np.random.default_rng(rng_seed)
    Ds, Dc = np.empty((B, X.shape[1])), np.empty((B, X.shape[1]))
    for i in range(B):
        c = np.bincount(rng.integers(0, S, S), minlength=S).astype(float)
        Ds[i] = OV.seed_adjusted_means(X, c)
        Dc[i] = OV.seed_adjusted_means(XC, c)
    return Ds, Dc


def standardised(c, s):
    """c rescaled to s's mean and sd across models (18a's other reading)."""
    c, s = np.asarray(c, float), np.asarray(s, float)
    return (c - c.mean()) / (c.std() or 1.0) * s.std() + s.mean()


def premium_block(y, ref, g, models, draws_idx, label, who, over, n_groups):
    """One vendor premium, three ways, with model-resampled intervals."""
    fwd, fse = ols_group(y, ref, g)
    rev, rse = ols_group(ref, y, g)
    one = np.ones((1, len(y)))
    t_all, t_non = (float(v[0]) for v in OV._tilts(y, ref, g, one))
    fb, rb, tb = [], [], []
    W = []
    for ii in draws_idx:
        gi = g[ii]
        if not gi.any() or gi.all():
            continue
        fb.append(ols_group(y[ii], ref[ii], gi)[0])
        rb.append(ols_group(ref[ii], y[ii], gi)[0])
        W.append(np.bincount(ii, minlength=len(y)))
    if W:
        _, tn = OV._tilts(y, ref, g, np.asarray(W, float))
        tb = list(tn)
    many = n_groups > 1
    return dict(
        group=label, sessions=int(len(y)), group_sessions=int(g.sum()),
        group_models=int(len({m for m, x in zip(models, g) if x})),
        models=int(len(set(models))),
        regression=dict(
            what="%s score on [1, %s score, its square, %s]: how much higher %s "
                 "scores the group's sessions than sessions %s scored the same"
                 % (who, over, "group", who, over),
            coefficient=r3(fwd), se=r3(fse), t=round(fwd / fse, 1) if fse else None,
            ci95_model_resampled=ci(fb) if many else None),
        reverse_regression=dict(
            what="%s score on [1, %s score, its square, group]: a premium that is "
                 "%s's alone shows here as a negative coefficient; a positive one "
                 "means the forward regression carries a regression-to-the-mean "
                 "share (the group is also better by %s)" % (over, who, who, over),
            coefficient=r3(rev), se=r3(rse), t=round(rev / rse, 1) if rse else None,
            ci95_model_resampled=ci(rb) if many else None),
        rescaled_difference=dict(
            what="%s minus %s rescaled to %s's mean and sd, group minus the rest: "
                 "direction-free (the overview's tilt)" % (who, over, who),
            vs_rest=r3(t_non), vs_all_sessions=r3(t_all),
            ci95_model_resampled=ci(tb) if many else None),
        note=(None if many else "one model: no model-resampled interval; the session "
                                "SE treats its 20 sessions as independent"))


# ------------------------------------------------------------------ build

def analyse(canon, rows, scores, pool, means, tiers, model_boot, rng_seed):
    """Every figure for one set of ChatGPT scores that needs no seed
    bootstrap (the per-model table with seed intervals is built once, on the
    primary set, by model_table)."""
    out = {}
    src_models = [canon[s]["model"] for s in sorted(scores)]
    # ---- per session
    both = [s for s in sorted(scores) if s in canon]
    sonnet = {r["session_id"]: r for r in rows}
    floor = sorted(s for s in both if float(sonnet[s]["overall"]) == FLOOR
                   and scores[s]["overall"] == FLOOR)
    keep = [s for s in both if s not in floor]
    mods = [canon[s]["model"] for s in keep]
    draws = session_index_draws(mods, model_boot, rng_seed)
    sess = {}
    for d in DIMS:
        a = np.array([OV.dim_value(sonnet[s], d) for s in keep])
        b = np.array([scores[s][d] for s in keep])
        sess[d] = agreement(a, b, draws)
    out["session_agreement"] = dict(
        sessions=len(keep), models=len(set(mods)), excluded_both_at_floor=floor,
        dimensions=sess)
    # ---- per model, the overview's basis
    cadj, cplain, cn = OV.other_judge_means(scores, rows, pool)
    ok = [m for m in pool if m in cadj and cn.get(m, 0) >= OV.CROSS_MIN_SESSIONS]
    picks = model_picks(len(ok), model_boot, rng_seed)
    mdim, cdim, sdim = {}, {}, {}
    for d in DIMS:
        sm = fit_means(rows, pool, d)[0]
        cm = OV.other_judge_means(scores, rows, pool, d)[0]
        sdim[d], cdim[d] = sm, cm
        a = np.array([sm[m] for m in ok])
        b = np.array([cm[m] for m in ok])
        mdim[d] = agreement(a, b, list(picks))
    S = np.array([means[m] for m in ok])
    C = np.array([cadj[m] for m in ok])
    offset = OV.scale_offset(means, cadj, ok)
    diff = C + offset - S
    top = np.array([tiers[m]["tier"] == "A" for m in ok])
    by_band = {}
    for key, sel, label in (("sonnet_A", top, "Sonnet's A letter (3.8 and above)"),
                            ("below_A", ~top, "below A")):
        idx = np.flatnonzero(sel)
        spread = float(S[idx].std()) if len(idx) > 1 else None
        dis = float(np.sqrt(np.mean((diff[idx]) ** 2))) if len(idx) else None
        blk = (agreement(S[idx], C[idx], list(model_picks(len(idx), model_boot, rng_seed)))
               if len(idx) > 3 else dict(n=int(len(idx))))
        blk.update(label=label, sonnet_spread_sd=r3(spread),
                   disagreement_rms_after_offset=r3(dis),
                   ratio=r3(dis / spread) if spread else None)
        by_band[key] = blk
    out["model_agreement"] = dict(
        models=len(ok), dimensions=mdim, by_band=by_band,
        by_band_note="Inside a letter the spread between models is small, so a "
                     "correlation there is low partly by range restriction. The ratio "
                     "sets the judges' disagreement (root mean square of the "
                     "difference after the scale offset) against the spread of "
                     "Sonnet's means in that band: above 1, the judges disagree more "
                     "than the models differ (15b's reading).")
    # ---- scale
    boot_off = [float(np.mean(S[p] - C[p])) for p in picks]
    sess_diff = np.array([float(sonnet[s]["overall"]) - scores[s]["overall"] for s in both])
    slope = float(np.polyfit(S, C, 1)[0])
    z = standardised(C, S)
    out["scale"] = dict(
        offset=dict(
            value=r3(offset), ci95_model_resampled=ci(boot_off),
            method="mean over the %d tiered models of Sonnet's model mean minus "
                   "ChatGPT's, both on the overview's model + seed fit, each model "
                   "weighted once (analyze_round4_overview.scale_offset). Adding it "
                   "to ChatGPT's means gives both judges the same mean across these "
                   "models, ROUND4_DESIGN 18a's centring." % len(ok),
            alternatives=dict(
                session_mean_difference=r3(sess_diff.mean()),
                median_of_model_differences=r3(np.median(S - C)))),
        spread=dict(
            sonnet_sd_across_models=r3(S.std()), chatgpt_sd_across_models=r3(C.std()),
            sd_ratio=r3(C.std() / S.std()),
            ols_slope_chatgpt_on_sonnet=r3(slope),
            note="An offset moves every model by the same amount; it does not undo a "
                 "difference in spread. ChatGPT's model means spread %.0f%% as wide "
                 "as Sonnet's, so after the offset alone Sonnet's top models sit a "
                 "little lower under ChatGPT and its bottom models a little higher "
                 "for that reason alone. The mean-and-sd rescale in `tiers` removes "
                 "both." % (100 * C.std() / S.std())))
    # ---- letters
    ts = [tiers[m]["tier"] for m in ok]
    tc_raw = [OV.tier_letter(v) for v in C]
    tc_off = [OV.tier_letter(v) for v in C + offset]
    tc_z = [OV.tier_letter(v) for v in z]
    ix = {L: i for i, (L, _, _) in enumerate(OV.TIERS)}
    depends = [m for m, a, b in zip(ok, ts, tc_off) if a != b]
    out["tier_summary"] = dict(
        models=len(ok),
        raw_same_letter=sum(a == b for a, b in zip(ts, tc_raw)),
        same_letter_after_offset=len(ok) - len(depends),
        same_letter_after_rescale=sum(a == b for a, b in zip(ts, tc_z)),
        tier_depends_on_judge=depends,
        moved_after_rescale=sorted(m for m, a, b in zip(ok, ts, tc_z) if a != b))
    out["_per_model"] = dict(ok=ok, S=S, C=C, offset=offset, diff=diff, z=z,
                             ts=ts, tc_raw=tc_raw, tc_off=tc_off, tc_z=tc_z, ix=ix,
                             cadj=cadj, cplain=cplain, cn=cn, sdim=sdim, cdim=cdim)
    # ---- vendor premiums (skeptic's session set: blank scenes out)
    ps = [s for s in both if not canon[s]["blank_scene"]]
    pm = [canon[s]["model"] for s in ps]
    sv = np.array([float(sonnet[s]["overall"]) for s in ps])
    cv = np.array([scores[s]["overall"] for s in ps])
    pdraws = session_index_draws(pm, model_boot, rng_seed)
    prem = {}
    g = np.array([GROUPS["claude"][1](m) for m in pm])
    prem["claude_sonnet_over_chatgpt"] = premium_block(
        sv, cv, g, pm, pdraws, GROUPS["claude"][0], "Sonnet", "ChatGPT",
        len({m for m in pm if GROUPS["claude"][1](m)}))
    for key in ("openai", "gpt_6", "gpt_6_astra"):
        g = np.array([GROUPS[key][1](m) for m in pm])
        prem["%s_chatgpt_over_sonnet" % key] = premium_block(
            cv, sv, g, pm, pdraws, GROUPS[key][0], "ChatGPT", "Sonnet",
            len({m for m in pm if GROUPS[key][1](m)}))
    out["vendor_premiums"] = prem
    out["_sessions"] = dict(n=len(both), models=len(set(src_models)))
    return out


def claude_letter_check(rows, pool, tiers, prem):
    """What subtracting Sonnet's measured Claude premium from every Claude
    session does to the Claude models' letters (the overview's check, on the
    full-corpus sizes)."""
    out = {}
    blk = prem["claude_sonnet_over_chatgpt"]
    sizes = (("regression", blk["regression"]["coefficient"]),
             ("regression_interval_upper", (blk["regression"]["ci95_model_resampled"] or [None, None])[1]),
             ("rescaled_difference", blk["rescaled_difference"]["vs_rest"]),
             ("rescaled_difference_interval_upper",
              (blk["rescaled_difference"]["ci95_model_resampled"] or [None, None])[1]))
    claude = sorted(m for m in pool if m.startswith("claude_"))
    for label, size in sizes:
        if size is None:
            continue
        chk = OV.tier_shift_check(rows, set(), pool, tiers, shift=("claude_", size))
        out[label] = dict(shift=-size, claude_models=len(claude),
                          claude_models_changing_letter=len(chk["tier_changes"]),
                          changes=chk["tier_changes"])
    return out


def openai_letter_check(scores, rows, pool, means, tiers, prem):
    """Which OpenAI models' `tier_depends_on_judge` goes away when ChatGPT's
    measured OpenAI premium is taken off their sessions (ChatGPT side only;
    the published letter is Sonnet's and does not move)."""
    size = prem["openai_chatgpt_over_sonnet"]["regression"]["coefficient"]
    flat = {s: v["overall"] for s, v in scores.items()}
    base = OV.cross_judge_block(NAME, flat, {}, rows, pool, means, tiers)[1]
    adj = {s: (v - size if s.split("::")[0].startswith("gpt_") else v)
           for s, v in flat.items()}
    after = OV.cross_judge_block(NAME, adj, {}, rows, pool, means, tiers)[1]
    openai = sorted(m for m in pool if m.startswith("gpt_"))
    return dict(
        shift=-size, openai_models=len(openai),
        tier_depends_before=sorted(m for m in openai if base[m].get("tier_depends_on_judge")),
        tier_depends_after=sorted(m for m in openai if after[m].get("tier_depends_on_judge")),
        differences_after={m: after[m]["difference"] for m in openai})


def model_table(pm, rows, pool, short, per, Ds, Dc, tiers, scores):
    """One row per model; seed-bootstrap intervals from the overview's draws."""
    ok, S, C, off = pm["ok"], pm["S"], pm["C"], pm["offset"]
    pos = {m: i for i, m in enumerate(pool)}
    j = np.array([pos[m] for m in ok])
    s_lo, s_hi = np.nanpercentile(Ds, [2.5, 97.5], axis=0)
    c_lo, c_hi = np.nanpercentile(Dc, [2.5, 97.5], axis=0)
    offb = np.nanmean(Ds[:, j] - Dc[:, j], axis=1)
    dB = Dc[:, j] + offb[:, None] - Ds[:, j]
    d_lo, d_hi = np.percentile(dB, [2.5, 97.5], axis=0)
    letters_differ = (tier_index_array(Ds[:, j]) != tier_index_array(Dc[:, j] + offb[:, None])).mean(0)
    n_rows = Counter(r["model"] for r in rows)
    out = {}
    for k, m in enumerate(ok):
        i = pos[m]
        moved = pm["ix"][pm["ts"][k]] - pm["ix"][pm["tc_off"][k]]
        out[m] = dict(
            n_sessions=n_rows[m], chatgpt_sessions=pm["cn"][m], n_seeds=len(per[m]),
            basis="seed_adjusted",
            group=("claude" if m.startswith("claude_") else "openai"
                   if m.startswith("gpt_") else "other"),
            sonnet=dict(
                overall=r4(S[k]), ci95=[r4(s_lo[i]), r4(s_hi[i])],
                interval_reaches_edge=OV.reaches_edge(s_lo[i], s_hi[i]),
                tier=pm["ts"][k],
                **{d: r4(pm["sdim"][d][m]) for d in DIMS[1:]}),
            chatgpt=dict(
                overall=r4(C[k]), ci95=[r4(c_lo[i]), r4(c_hi[i])],
                overall_plain=r4(pm["cplain"][m]), tier=pm["tc_raw"][k],
                overall_after_offset=r4(C[k] + off), tier_after_offset=pm["tc_off"][k],
                tier_after_rescale=pm["tc_z"][k],
                **{d: r4(pm["cdim"][d][m]) for d in DIMS[1:]}),
            difference_after_offset=r3(pm["diff"][k]),
            difference_ci95=[r3(d_lo[k]), r3(d_hi[k])],
            difference_interval_excludes_zero=bool(d_lo[k] > 0 or d_hi[k] < 0),
            beyond_band=bool(abs(pm["diff"][k]) > BAND),
            letters_moved=int(moved),
            tier_depends_on_judge=pm["ts"][k] != pm["tc_off"][k],
            share_of_seed_draws_letters_differ=r3(letters_differ[k]))
    for m in short:
        cs = [scores[s]["overall"] for s in scores if s.split("::")[0] == m]
        ss = [float(r["overall"]) for r in rows if r["model"] == m]
        out[m] = dict(n_sessions=len(ss), chatgpt_sessions=len(cs), n_seeds=len(per[m]),
                      basis="plain", group="other",
                      note="%d of %d seeds: untiered, plain means, no letter"
                           % (len(per[m]), len({r["seed"] for r in rows})),
                      sonnet=dict(overall=r4(np.mean(ss)) if ss else None, tier=None),
                      chatgpt=dict(overall=r4(np.mean(cs)) if cs else None, tier=None),
                      tier_depends_on_judge=None)
    return dict(sorted(out.items()))


def moves_table(models):
    """The models whose letter depends on the judge, and how."""
    rows = []
    for m, r in models.items():
        if not r.get("tier_depends_on_judge"):
            continue
        rows.append(dict(
            model=m, sonnet_tier=r["sonnet"]["tier"],
            chatgpt_tier_after_offset=r["chatgpt"]["tier_after_offset"],
            letters_moved=r["letters_moved"],
            direction="higher under ChatGPT" if r["letters_moved"] > 0 else "lower under ChatGPT",
            difference_after_offset=r["difference_after_offset"],
            difference_ci95=r["difference_ci95"],
            beyond_band=r["beyond_band"],
            difference_interval_excludes_zero=r["difference_interval_excludes_zero"],
            sonnet_interval_reaches_edge=r["sonnet"]["interval_reaches_edge"],
            share_of_seed_draws_letters_differ=r["share_of_seed_draws_letters_differ"],
            group=r["group"]))
    return sorted(rows, key=lambda x: (-abs(x["difference_after_offset"]), x["model"]))


def bridge_block(scores, agent, sonnet):
    sids = sorted(s for s in agent if s in scores)
    if len(sids) < 5:
        return dict(n=len(sids), note="fewer than 5 bridge sessions: no figure")
    app = np.array([scores[s]["overall"] for s in sids])
    ag = np.array([agent[s]["overall"] for s in sids])
    so = np.array([float(sonnet[s]["overall"]) for s in sids])
    d = app - ag
    return dict(
        n=len(sids), sessions=sids,
        app_vs_agent=dict(pearson=r3(pearson(app, ag)), mean_diff_app_minus_agent=r3(d.mean()),
                          median_abs_diff=r3(np.median(np.abs(d))),
                          within_0_5=r3(np.mean(np.abs(d) <= 0.5 + 1e-9))),
        sonnet_vs_app=dict(pearson=r3(pearson(so, app)), mean_diff=r3((so - app).mean())),
        sonnet_vs_agent=dict(pearson=r3(pearson(so, ag)), mean_diff=r3((so - ag).mean())),
        references=dict(chatgpt_same_harness=REFERENCE["chatgpt_vs_chatgpt_same_harness"],
                        gemini_harness_shift=REFERENCE["gemini_harness_shift"]),
        reading="Two ChatGPT runs on the same text: the Codex pass (`app` in the "
                "key names) and the earlier blind passes (`agent`; judge_round2_chatgpt, "
                "judge_inc1_chatgpt). Each run was a coordinator handing its work to "
                "clean-context raters, so this compares two runs with different "
                "rater sets; where the earlier passes ran is not recorded. The level "
                "barely moves (mean difference %+.2f, Codex minus earlier) and the "
                "two runs agree at r %+.2f, a little below the %+.3f of the two "
                "earlier passes on the 120-session sample (17c); Gemini moved %.2f "
                "between its chat-client and API passes (18c). Mixing the 179 reused "
                "rows into the corpus is therefore a small effect, and `sensitivity` "
                "shows the figures without them. n=%d is small."
                % (d.mean(), pearson(app, ag), REFERENCE["chatgpt_vs_chatgpt_same_harness"]["r"],
                   REFERENCE["gemini_harness_shift"]["mean_diff"], len(sids)))


def summary_of(res):
    """The sensitivity row for one set of scores."""
    ts = res["tier_summary"]
    p = res["vendor_premiums"]
    return dict(
        sessions=res["_sessions"]["n"],
        session_pearson_overall=res["session_agreement"]["dimensions"]["overall"]["pearson"],
        session_pearson_overall_ci95=res["session_agreement"]["dimensions"]["overall"]["pearson_ci95"],
        model_pearson_overall=res["model_agreement"]["dimensions"]["overall"]["pearson"],
        model_pearson_overall_ci95=res["model_agreement"]["dimensions"]["overall"]["pearson_ci95"],
        scale_offset=res["scale"]["offset"]["value"],
        raw_same_letter=ts["raw_same_letter"],
        same_letter_after_offset=ts["same_letter_after_offset"],
        tier_depends_on_judge=ts["tier_depends_on_judge"],
        claude_premium_regression=p["claude_sonnet_over_chatgpt"]["regression"]["coefficient"],
        claude_premium_regression_ci95=p["claude_sonnet_over_chatgpt"]["regression"]["ci95_model_resampled"],
        claude_premium_rescaled=p["claude_sonnet_over_chatgpt"]["rescaled_difference"]["vs_rest"],
        openai_premium_regression=p["openai_chatgpt_over_sonnet"]["regression"]["coefficient"],
        openai_premium_regression_ci95=p["openai_chatgpt_over_sonnet"]["regression"]["ci95_model_resampled"],
        openai_premium_rescaled=p["openai_chatgpt_over_sonnet"]["rescaled_difference"]["vs_rest"])


def _iv(x):
    return "[%.2f, %.2f]" % tuple(x) if x else "(no interval)"


def _excludes_zero(x):
    return bool(x) and (x[0] > 0 or x[1] < 0)


def premium_sentence(p, who, over, group):
    """One vendor term in words, with the reverse-regression check."""
    f, r, t = p["regression"], p["reverse_regression"], p["rescaled_difference"]
    head = ("%s scores %s' sessions %+.2f %s above sessions %s scored the same "
            "(%d of %s sessions, %d models); %+.2f %s on the direction-free rescaled "
            "difference."
            % (who, group, f["coefficient"], _iv(f["ci95_model_resampled"]), over,
               p["group_sessions"], format(p["sessions"], ","), p["group_models"], t["vs_rest"],
               _iv(t["ci95_model_resampled"])))
    if r["coefficient"] < 0 and _excludes_zero(r["ci95_model_resampled"]):
        tail = (" The reverse regression points the same way (%+.2f %s: %s scores "
                "those sessions lower than %s at the same score predicts), so the "
                "difference survives both directions."
                % (r["coefficient"], _iv(r["ci95_model_resampled"]), over, who))
    else:
        tail = (" The reverse regression gives %+.2f %s, not the negative figure a "
                "difference that is %s's alone would give, so part of the forward "
                "figure is the regression's own artifact (the group scores above "
                "the rest under %s as well); the direction-free rescaled "
                "difference is the better guide to its size."
                % (r["coefficient"], _iv(r["ci95_model_resampled"]), who, over))
    return head + tail


def reading_block(doc):
    """What the full corpus can and cannot establish, from the numbers."""
    sa = doc["session_agreement"]["dimensions"]["overall"]
    ma = doc["model_agreement"]["dimensions"]["overall"]
    bb = doc["model_agreement"]["by_band"]
    off = doc["scale"]["offset"]
    t = doc["tiers"]
    mv = t["after_offset"]["moves"]
    cnt = t["after_offset"]["counts"]
    pc = doc["vendor_premiums"]["claude_sonnet_over_chatgpt"]
    po = doc["vendor_premiums"]["openai_chatgpt_over_sonnet"]
    cl = doc["vendor_premiums"]["claude_letter_check"]
    ol = doc["vendor_premiums"]["openai_letter_check"]
    sp = doc["scale"]["spread"]
    can = [
        "Both families order the models alike at the broad scale: per model Pearson "
        "%+.2f %s and Spearman %+.2f %s over %d models; per session Pearson %+.2f %s "
        "over %s sessions, where Sonnet against itself gave %+.3f (ROUND4_DESIGN 17c)."
        % (ma["pearson"], _iv(ma["pearson_ci95"]), ma["spearman"], _iv(ma["spearman_ci95"]),
           ma["n"], sa["pearson"], _iv(sa["pearson_ci95"]), format(sa["n"], ","),
           REFERENCE["sonnet_vs_sonnet"]["r"]),
        "ChatGPT uses the scale %.2f %s lower than Sonnet (one offset for every model), "
        "and its model means spread %.0f%% as wide. Its raw letters therefore sit "
        "lower: on the same fixed ranges, raw, %d of %d models get Sonnet's letter."
        % (off["value"], _iv(off["ci95_model_resampled"]), 100 * sp["sd_ratio"],
           t["raw"]["same_letter"], t["models"]),
        "After that offset %d of %d models keep their letter and %d change (%d higher "
        "under ChatGPT, %d lower). %d of the %d differ from Sonnet by more than the "
        "card's 0.3 band, %d have a seed-bootstrap interval of the difference that "
        "excludes zero, and %d already have a Sonnet interval that reaches a letter "
        "edge on its own. Across the seed bootstrap the two letters differ in at "
        "least 90%% of draws for %d of them and in under half for %d, so the list's "
        "edge cases are not firm. Rescaling for spread as well leaves %d with the "
        "same letter."
        % (t["after_offset"]["same_letter"], t["models"], cnt["moved"],
           cnt["higher_under_chatgpt"], cnt["lower_under_chatgpt"], cnt["beyond_band"],
           cnt["moved"], cnt["difference_interval_excludes_zero"],
           cnt["sonnet_interval_reaches_edge"],
           cnt["letters_differ_in_90pct_of_seed_draws"],
           cnt["letters_differ_in_under_half_of_seed_draws"],
           t["after_rescale"]["same_letter"]),
        "Inside Sonnet's A letter the two judges agree less (Pearson %+.2f %s, n=%d; "
        "below A %+.2f %s, n=%d). Inside A their disagreement is %.2f times the spread "
        "between the models (below A %.2f): the order inside A depends on the judge, "
        "as 15b found on the sample."
        % (bb["sonnet_A"]["pearson"], _iv(bb["sonnet_A"].get("pearson_ci95")),
           bb["sonnet_A"]["n"], bb["below_A"]["pearson"],
           _iv(bb["below_A"].get("pearson_ci95")), bb["below_A"]["n"],
           bb["sonnet_A"]["ratio"], bb["below_A"]["ratio"]),
        premium_sentence(po, "ChatGPT", "Sonnet", "OpenAI models"),
        premium_sentence(pc, "Sonnet", "ChatGPT", "Claude models")
        + " Subtracting the forward figure from every Claude session moves %d of %d "
          "Claude models to another letter; subtracting the rescaled one moves %d."
        % (cl["regression"]["claude_models_changing_letter"], cl["regression"]["claude_models"],
           cl["rescaled_difference"]["claude_models_changing_letter"]),
    ]
    cannot = [
        "Which judge is right. Neither is a ground truth, the rubric's calibration "
        "sentence fits both readings (15a, 18), and the human arena covers 19 models "
        "on 12 seeds. A vendor term measured between two judges is relative: it "
        "cannot say whether one judge is generous to its own family or the other "
        "harsh to it.",
        "Whether a vendor-linked difference is favouritism or a style preference the "
        "other judge does not share. Both judges were blind to model names, so it is "
        "not the label; each could still recognise a style. Taking ChatGPT's measured "
        "OpenAI term off the OpenAI sessions changes which OpenAI models' letters "
        "depend on the judge from %s to %s."
        % (", ".join(ol["tier_depends_before"]) or "none",
           ", ".join(ol["tier_depends_after"]) or "none"),
        "ChatGPT's self-consistency on the full corpus. Each session was scored once; "
        "the 24 bridge sessions (two runs) and 17c's 120 are the only repeats.",
        "Which ChatGPT model served the Codex pass. Codex did not record it. The "
        "first ChatGPT pass was recorded as ChatGPT (Astra) (sec 15), so `gpt_6_astra` "
        "may be the judge's own model.",
    ]
    groups = defaultdict(list)
    for x in mv:
        groups[x["group"]].append(x["model"])
    tiers_line = [
        "The published letter stays Sonnet's, on its fixed ranges; nothing is adjusted "
        "by this file. `tier_depends_on_judge` marks the %d models whose letter the "
        "other family would not give once its scale offset is removed: for them the "
        "letter says as much about the judge as about the model." % len(mv),
        "Claude models among them: %s. OpenAI models among them: %s."
        % (", ".join(groups["claude"]) or "none", ", ".join(groups["openai"]) or "none"),
    ]
    return {"can_establish": can, "cannot_establish": cannot, "round4_tiers": tiers_line}


def build(results, seed_boot=SEED_BOOT, model_boot=MODEL_BOOT, rng_seed=RNG_SEED):
    results = Path(results)
    canon, copies, _ = OV.load_corpus(results)
    sj = results / "session_judge_v2.jsonl"
    rows = OV.load_judge_rows(sj)
    val = OV.validate_judge_rows(rows, canon, copies)
    scores, src, pmeta = load_package(results / MERGED, canon)
    agent, agent_files = load_bridge(results, canon)
    pool, short, seeds, X, per = OV.build_matrix(rows)
    means = dict(zip(pool, (float(v) for v in OV.seed_adjusted_means(X))))
    tiers, _ = OV.assign_tiers(means)
    sonnet = {r["session_id"]: r for r in rows}

    res = analyse(canon, rows, scores, pool, means, tiers, model_boot, rng_seed)
    pm = res.pop("_per_model")
    sess = res.pop("_sessions")
    XC = aligned_matrix({s: v["overall"] for s, v in scores.items()}, rows, pool, seeds)
    Ds, Dc = seed_bootstrap(X, XC, seed_boot)
    models = model_table(pm, rows, pool, short, per, Ds, Dc, tiers, scores)
    moves = moves_table(models)
    ts = res.pop("tier_summary")
    ok = pm["ok"]
    res["vendor_premiums"]["claude_letter_check"] = claude_letter_check(
        rows, pool, tiers, res["vendor_premiums"])
    res["vendor_premiums"]["openai_letter_check"] = openai_letter_check(
        scores, rows, pool, means, tiers, res["vendor_premiums"])

    # ---- sensitivity: the reused rows and the bridge sessions
    app = {s for s in scores if src.get(s) == APP_SOURCE}
    bridge = set(agent)
    variants = {
        "all_rows": ("every session: %d Codex rows and %d rows reused from the "
                     "earlier blind passes; bridge sessions carry the Codex row"
                     % (len(app), len(scores) - len(app)),
                     scores),
        "without_reused_rows": ("Codex rows only: the %d reused rows from the "
                                "earlier passes dropped" % (len(scores) - len(app)),
                                {s: v for s, v in scores.items() if s in app}),
        "without_bridge_sessions": ("the %d bridge sessions dropped" % len(bridge),
                                    {s: v for s, v in scores.items() if s not in bridge}),
        "app_rows_without_bridge": ("Codex rows only, bridge sessions dropped",
                                    {s: v for s, v in scores.items()
                                     if s in app and s not in bridge}),
        "bridge_on_agent_rows": ("every session, the bridge sessions on their row "
                                 "from the earlier passes",
                                 {s: agent.get(s, v) for s, v in scores.items()}),
    }
    sens = {}
    for key, (what, sc) in variants.items():
        if key != "all_rows" and (len(sc) < 20 or sc == scores):
            continue            # nothing to drop, or too little left to fit
        r = res if key == "all_rows" else analyse(
            canon, rows, sc, pool, means, tiers, model_boot, rng_seed)
        row = summary_of(dict(r, tier_summary=ts if key == "all_rows" else r["tier_summary"],
                              _sessions=sess if key == "all_rows" else r["_sessions"]))
        row["what"] = what
        base = set(ts["tier_depends_on_judge"])
        row["tier_depends_changes_vs_all_rows"] = dict(
            added=sorted(set(row["tier_depends_on_judge"]) - base),
            removed=sorted(base - set(row["tier_depends_on_judge"])))
        sens[key] = row

    n_rows = Counter(r["model"] for r in rows)
    doc = dict(
        title="Round 4: a second judge family over the whole corpus",
        generated_by="rounds/r4/analyze_round4_second_judge.py",
        read_this_first=(
            "Two judge families scored every craft session: Claude Sonnet 5 (the "
            "published tier) and %s. The letter stays Sonnet's. This file says how "
            "far the two agree, how much of their gap is one scale offset, which "
            "models' letters depend on the judge, and what vendor-linked "
            "differences remain. It does not say which judge is right." % LABEL),
        judges=dict(
            first=dict(judge=OV.JUDGE, label="Claude Sonnet 5 (session judge v2)",
                       role="sets the published letter", file="session_judge_v2.jsonl",
                       rows=val),
            second=dict(
                judge=NAME, label=LABEL, package="results/%s" % MERGED,
                harness=("ChatGPT run blind in Codex on a ChatGPT subscription: opaque "
                         "ids, no model or seed names; %d sessions in eleven chunks of "
                         "about 100. One coordinating session, as Levi asked, gave each "
                         "whole chunk to its own clean-context agent, three at a time, "
                         "not one conversation per chunk as the package planned (the "
                         "judges' reports: judge_full_chatgpt/app_pass/reports). The "
                         "other %d rows are reused from the earlier blind ChatGPT "
                         "passes (judge_round2_chatgpt, judge_inc1_chatgpt) on "
                         "byte-identical text; each of those was also a coordinator "
                         "handing parts to three clean-context raters (their "
                         "METHOD.md), and where they ran is not recorded"
                         % (len(app), len(scores) - len(app))),
                model_version="not recorded by Codex",
                rows_by_source=dict(sorted(Counter(src.values()).items())),
                **pmeta)),
        coverage=dict(corpus_sessions=len(canon), sessions_with_both=sess["n"],
                      models=sess["models"], tiered_models=len(ok),
                      untiered=[dict(model=m, n_seeds=len(per[m]), sessions=n_rows[m])
                                for m in short],
                      twelve_seed_models=sorted(m for m in pool if len(per[m]) < len(seeds)),
                      seeds=len(seeds), bridge_sessions=len(bridge),
                      note="Seed-adjusted means for both judges (each with its own "
                           "seed effects), exactly as the overview sets a 12-seed "
                           "model's tier mean on all %d seeds." % len(seeds)),
        session_agreement=res["session_agreement"],
        model_agreement=res["model_agreement"],
        scale=res["scale"],
        models=models,
        tiers=dict(
            letters={L: OV.tier_label(L) for L, _, _ in OV.TIERS},
            sonnet_sizes=dict(sorted(Counter(pm["ts"]).items())),
            models=len(ok),
            raw=dict(same_letter=ts["raw_same_letter"],
                     sizes=dict(sorted(Counter(pm["tc_raw"]).items())),
                     confusion=confusion(pm["ts"], pm["tc_raw"]),
                     note="ChatGPT's own letters on the same fixed ranges, raw: they "
                          "sit lower because ChatGPT uses the scale lower"),
            after_offset=dict(
                same_letter=ts["same_letter_after_offset"],
                sizes=dict(sorted(Counter(pm["tc_off"]).items())),
                confusion=confusion(pm["ts"], pm["tc_off"]),
                tier_depends_on_judge=ts["tier_depends_on_judge"],
                moves=moves,
                counts=dict(
                    moved=len(moves),
                    higher_under_chatgpt=sum(1 for x in moves if x["letters_moved"] > 0),
                    lower_under_chatgpt=sum(1 for x in moves if x["letters_moved"] < 0),
                    beyond_band=sum(1 for x in moves if x["beyond_band"]),
                    difference_interval_excludes_zero=sum(
                        1 for x in moves if x["difference_interval_excludes_zero"]),
                    sonnet_interval_reaches_edge=sum(
                        1 for x in moves if x["sonnet_interval_reaches_edge"]),
                    letters_differ_in_90pct_of_seed_draws=sum(
                        1 for x in moves if x["share_of_seed_draws_letters_differ"] >= 0.9),
                    letters_differ_in_under_half_of_seed_draws=sum(
                        1 for x in moves if x["share_of_seed_draws_letters_differ"] < 0.5),
                    by_group=dict(sorted(Counter(x["group"] for x in moves).items()))),
                rule="ChatGPT's mean plus the scale offset, on the same fixed letters; "
                     "a model whose letter differs from Sonnet's is "
                     "`tier_depends_on_judge` (the overview's flag). "
                     "`share_of_seed_draws_letters_differ` is how often the two "
                     "letters differ across the seed bootstrap (offset re-estimated "
                     "in each draw)."),
            after_rescale=dict(
                same_letter=ts["same_letter_after_rescale"],
                moved=ts["moved_after_rescale"],
                note="Sensitivity: ChatGPT's model means rescaled to Sonnet's mean and "
                     "sd across models, which also undoes the difference in spread")),
        vendor_premiums=res["vendor_premiums"],
        bridge=bridge_block(scores, agent, sonnet),
        sensitivity=sens,
        earlier=EARLIER,
        method=dict(
            session_set="sessions both judges scored on the current text (hash-checked); "
                        "for agreement, sessions both judges put at the 1.0 floor are "
                        "left out (no model text to judge, pipeline/compare_external_judge.py's "
                        "rule); for the vendor terms, blank scenes are left out (the "
                        "continuity check's rule)",
            model_means="the overview's model + seed fit over the tiered pool, each "
                        "judge with its own seed effects (analyze_round4_overview."
                        "seed_adjusted_means); untiered models get plain means",
            spearman="average ranks for ties",
            model_resampling="%d draws, numpy default_rng(%d): models drawn with "
                             "replacement, every session of a drawn model comes along; "
                             "the same draws for every figure computed on one session "
                             "set" % (model_boot, rng_seed),
            seed_bootstrap="%d draws replaying the overview's own (numpy "
                           "default_rng(%d)), both judges on each draw; the offset is "
                           "re-estimated in each draw" % (seed_boot, OV.RNG_SEED),
            groups={k: v[0] for k, v in GROUPS.items()}),
        inputs=inputs_block(results, agent_files),
    )
    doc["reading"] = reading_block(doc)
    return doc


def inputs_block(results, extra):
    names = ["session_judge_v2.jsonl"] + [os.path.basename(p) for p in OV.session_sources(results)]
    out = {n: OV.sha(results / n) for n in names if (results / n).exists()}
    for f in sorted((results / MERGED).glob("*.json")):
        out["%s/%s" % (MERGED, f.name)] = OV.sha(f)
    if (results / KEYMAP).exists():
        out[KEYMAP] = OV.sha(results / KEYMAP)
    for rel in extra:
        p = results.parent / rel
        out[str(Path(rel).relative_to("results"))] = OV.sha(p)
    return dict(sorted(out.items()))


# ------------------------------------------------------------------ output

def summary(doc):
    sa = doc["session_agreement"]["dimensions"]
    ma = doc["model_agreement"]["dimensions"]
    t = doc["tiers"]
    p = doc["vendor_premiums"]
    out = ["%s vs Sonnet 5: %d sessions, %d models"
           % (LABEL, doc["coverage"]["sessions_with_both"], doc["coverage"]["models"])]
    for d in DIMS:
        out.append("  %-16s session r %+.3f %s rho %+.3f (n=%d) | model r %+.3f %s rho %+.3f (n=%d)"
                   % (DIM_LABEL[d], sa[d]["pearson"], sa[d]["pearson_ci95"], sa[d]["spearman"],
                      sa[d]["n"], ma[d]["pearson"], ma[d]["pearson_ci95"], ma[d]["spearman"],
                      ma[d]["n"]))
    bb = doc["model_agreement"]["by_band"]
    out.append("  inside A r %+.3f (n=%d, ratio %.2f); below A r %+.3f (n=%d, ratio %.2f)"
               % (bb["sonnet_A"]["pearson"], bb["sonnet_A"]["n"], bb["sonnet_A"]["ratio"],
                  bb["below_A"]["pearson"], bb["below_A"]["n"], bb["below_A"]["ratio"]))
    o = doc["scale"]["offset"]
    out.append("scale offset %.3f %s (session mean diff %.3f); sd ratio %.3f"
               % (o["value"], o["ci95_model_resampled"],
                  o["alternatives"]["session_mean_difference"], doc["scale"]["spread"]["sd_ratio"]))
    out.append("letters: raw same %d of %d; after offset same %d, moved %d %s; after rescale same %d"
               % (t["raw"]["same_letter"], t["models"], t["after_offset"]["same_letter"],
                  t["after_offset"]["counts"]["moved"], t["after_offset"]["counts"],
                  t["after_rescale"]["same_letter"]))
    for x in t["after_offset"]["moves"]:
        out.append("  %-24s %s -> %s  d %+.3f %s  edge %s  draws %.2f"
                   % (x["model"], x["sonnet_tier"], x["chatgpt_tier_after_offset"],
                      x["difference_after_offset"], x["difference_ci95"],
                      x["sonnet_interval_reaches_edge"], x["share_of_seed_draws_letters_differ"]))
    for k, v in p.items():
        if not k.endswith(("_over_chatgpt", "_over_sonnet")):
            continue
        out.append("%-34s fwd %+.3f %s | rev %+.3f %s | rescaled %+.3f %s"
                   % (k, v["regression"]["coefficient"], v["regression"]["ci95_model_resampled"],
                      v["reverse_regression"]["coefficient"],
                      v["reverse_regression"]["ci95_model_resampled"],
                      v["rescaled_difference"]["vs_rest"],
                      v["rescaled_difference"]["ci95_model_resampled"]))
    for k, v in p["claude_letter_check"].items():
        out.append("  claude shift %s %.3f: %d of %d Claude models change letter"
                   % (k, v["shift"], v["claude_models_changing_letter"], v["claude_models"]))
    ol = p["openai_letter_check"]
    out.append("  openai premium off ChatGPT: tier depends %s -> %s"
               % (ol["tier_depends_before"], ol["tier_depends_after"]))
    b = doc["bridge"]
    if "app_vs_agent" in b:
        out.append("bridge n=%d: r %+.3f, Codex minus earlier %+.3f, median |d| %.2f"
                   % (b["n"], b["app_vs_agent"]["pearson"],
                      b["app_vs_agent"]["mean_diff_app_minus_agent"],
                      b["app_vs_agent"]["median_abs_diff"]))
    for k, v in doc["sensitivity"].items():
        out.append("sens %-24s n=%d sess r %+.3f model r %+.3f off %.3f same %d depends %d "
                   "claude %+.3f openai %+.3f %s"
                   % (k, v["sessions"], v["session_pearson_overall"], v["model_pearson_overall"],
                      v["scale_offset"], v["same_letter_after_offset"],
                      len(v["tier_depends_on_judge"]), v["claude_premium_regression"],
                      v["openai_premium_regression"], v["tier_depends_changes_vs_all_rows"]))
    return "\n".join(out)


def dump(obj, path):
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out", default=None, help="default: <results>/%s" % OUT)
    ap.add_argument("--seed-boot", type=int, default=SEED_BOOT)
    ap.add_argument("--model-boot", type=int, default=MODEL_BOOT)
    ap.add_argument("--rng-seed", type=int, default=RNG_SEED)
    a = ap.parse_args(argv)
    try:
        doc = build(a.results, a.seed_boot, a.model_boot, a.rng_seed)
    except OV.InputError as e:
        print("FAIL CLOSED, nothing written.\n%s" % e, file=sys.stderr)
        return 2
    out = Path(a.out or Path(a.results) / OUT)
    dump(doc, out)
    print(summary(doc))
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
