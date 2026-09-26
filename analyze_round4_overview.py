#!/usr/bin/env python3
"""Round 4 overview: three columns side by side, nothing summed.

    Judge tier (Sonnet 5)   fixed letters on the session judge's 1-5 `overall`
                            mean: A 3.8 and above, B 3.2-3.8, C 2.6-3.2,
                            D 2.0-2.6, E below 2.0 (edges 5.0 - 0.6k, frozen)
    J                       exactly as published in
                            round4_willingness_leaderboard.json
    Watch out               counted defects, never a score

There is no composite number and no position. The three columns measure
different things (ROUND4_DESIGN.md secs 14-18, README "Round 4") and are shown
beside each other so a reader can weigh them.

The letters are frozen in this file (TIERS). Each is 0.6 wide, the card's
+/-0.3 band, except that A is open at the top (a model above 4.4 stays A) and
E is open at the floor. Adding a model, dropping a session or re-running the
bootstrap can move a model between letters only by moving its own mean; no
letter ever names a different range.

The per-model judge means (overall and the S.5 agency, S.1 consistency and
S.3 momentum session scores, with n_sessions and n_seeds) are written to the
overview's `judge_means` block, which the model-cards export reads for the
site's judge table. The overview rows themselves carry no figure.

The judge ELO is a Bradley-Terry re-expression of the same session-judge
scores, fitted on within-seed matched pairs. It is written to
round4_judge_elo.json with its interval and rank range, and is never rendered
as a rank: it rank-correlates with the plain mean at about 0.99 and adds a
familiar scale, not information. (On the profile cards "craft band" means the
flaw hunter, which is not an input here.)

Inputs, all read-only:
    results/craft_baseline_*.json, results/multiturn_merged_all_v2.json
        transcripts; newest source wins per session_id (transcript_hash.py rule)
    results/session_judge_v2.jsonl       Sonnet 5 `overall` and session
                                         dimensions, one row a session
    results/round4_willingness_leaderboard.json   J, copied, not recomputed
    results/production_defects.json      leak / writes-your-character / loop
                                         counts, re-counted here with its own
                                         rules and required to match
    results/r4_full_*.json               Track A rung labels, read only for a
                                         model the silent-refusal rule flags
    results/multiturn_arena_bayesian.json          human check only
    results/judge_{round2,inc1}_{chatgpt,gemini}/  three-family check only

Fails closed, writing nothing, when a judge row's transcript hash does not
match the transcript on disk, when an unhashed row's session has more than one
transcript on disk (it could be stale and nothing can prove otherwise), on a
duplicate row, on a row with no transcript, on a second judge name in the
file, when production_defects.json does not describe the same corpus, or when
the Track A rung recount does not reproduce the published empty rate.

A second judge (the pending ChatGPT cross-check) plugs in with
`--cross-judge NAME=PATH`. Its per-model means land in each row's
`cross_judges` and in the top-level `cross_judges`; nothing else changes shape.

Usage:
    python3 analyze_round4_overview.py                 # B=10000 bootstrap
    python3 analyze_round4_overview.py --boot 2000 --markdown /tmp/table.md
    python3 analyze_round4_overview.py --cross-judge chatgpt=PATH
"""
import argparse
import glob
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transcript_hash import transcript_hash  # noqa: E402
import analyze_production_defects as PD  # noqa: E402  (its rules, not a copy)
from publication_guards import _guard_path  # noqa: E402

ROOT = Path(__file__).resolve().parent

JUDGE = "subagent-sonnet-5"      # the one judge this signal is defined on
MIN_SEEDS = 12                   # fewer seeds: listed, not tiered
MIN_CHARS = PD.MIN_CHARS         # 50, the defects file's own cutoff
DEFECTS_MIN_TURNS = 50           # production_defects.json skips models below
GATE_13A = 0.70                  # ROUND4_DESIGN 13a partial-session gate

# The per-model means the judge table shows, under the rubric's own keys.
DIMENSIONS = ("overall", "S.5_agency_respect_session", "S.1_consistency_over_time",
              "S.3_narrative_momentum")

# Fixed letters, frozen at publication. Edges are 5.0 - 0.6k; the lower edge
# belongs to the letter. 0.6 is the card's +/-0.3 SUBJECTIVE band (ROUND4_DESIGN
# 15e) and J's ~0.3 tie band. A is open at the top: it also covers 4.4-5.0, so
# a model above 4.4 stays A. E is open at the floor. Never re-lettered.
BAND_TOP = 5.0
BAND_WIDTH = 0.6
TIERS = (("A", 3.8, None), ("B", 3.2, 3.8), ("C", 2.6, 3.2), ("D", 2.0, 2.6),
         ("E", None, 2.0))
TIER_EDGES = (3.8, 3.2, 2.6, 2.0)
MIN_TIERS, MAX_TIERS = 3, 7
EDGE_EPS = 1e-9                  # float noise only (5.0 - 0.6*2 != 3.8)
EDGE_DP = 4                      # interval ends are compared at the 4 decimals
                                 # the JSON prints: an end ON an edge touches it

BT_SCALE = 400 / math.log(10)    # 100 points = 64% of shared scenarios
BT_PRIOR_SD = 300.0
BT_ANCHOR = 1500.0

RNG_SEED = 20260926
BOOT_DEFAULT = 10000

WATCH_MIN_RATE = 0.02            # turn-level items are shown at >= 2% of turns
SILENT_EMPTY_RATE = 0.20         # analyze_round4_willingness.py rule, copied
SILENT_RUNG_SLOPE = 0.25

CROSS_MIN_SESSIONS = 3
CROSS_FLAG = 0.3                 # the card's +/-0.3 band

THREE_FAMILY = {                 # corpus-level check only
    "chatgpt": [("judge_round2_chatgpt", "external_blind_pass"),
                ("judge_inc1_chatgpt", "external_blind_pass")],
    "gemini": [("judge_round2_gemini", "api_pass"),
               ("judge_inc1_gemini", "api_pass")],
}
MODEL_BOOT = 10000               # model-resampling draws for the tilt's SE

R4_GLOB = "r4_full_*.json"       # round 4 runs; Track A rung labels only
RUNG_MILD, RUNG_EXPLICIT = 1, 5  # analyze_round4_willingness._empty_slope

OUT_ELO = "round4_judge_elo.json"
OUT_OVERVIEW = "round4_overview.json"


class InputError(RuntimeError):
    """An input fails a publication check; nothing is written."""


def read_json(path):
    with open(path) as fh:
        return json.load(fh)


def read_lines(path):
    with open(path) as fh:
        return [line for line in fh if line.strip()]


# --------------------------------------------------------------------- corpus

def session_sources(results):
    """Newest craft_baseline first, then the April merge: first copy wins."""
    out = sorted(glob.glob(str(Path(results) / "craft_baseline_*.json")),
                 reverse=True)
    merged = Path(results) / "multiturn_merged_all_v2.json"
    if merged.exists():
        out.append(str(merged))
    return out


def defect_counts(s, bodies):
    """analyze_production_defects.py's leak / selfplay / loop rules, on one
    session's answered turns. Its functions are imported, not copied, so the
    two cannot drift; the file itself skips models under 50 answered turns,
    and this is how those models still get a count."""
    uname = (s.get("user_name") or "").strip().split()
    sp = re.compile(r"(?m)^\s*%s\s*:" % re.escape(uname[0])) if uname else None
    out = dict(leak=0, selfplay=0, loop=0)
    for b in bodies:
        if len(b.strip()) < PD.MIN_CHARS:
            continue
        out["leak"] += bool(PD.LEAK.search(b))
        out["loop"] += PD.loop_share(b) >= PD.LOOP_SHARE
        out["selfplay"] += bool(sp and sp.search(b))
    return out


def load_corpus(results):
    """Canonical session per session_id, plus copy counts and error rows."""
    canon, copies, errors = {}, Counter(), defaultdict(list)
    for src in session_sources(results):
        data = read_json(src)
        sim = ((data.get("config") or {}).get("user_sim_model"))
        for s in data["sessions"]:
            if "error" in s or "dialogue" not in s:
                errors[s.get("test_model")].append(
                    (os.path.basename(src), str(s.get("error"))[:160]))
                continue
            sid = "%s::%s" % (s["test_model"], s["seed_id"])
            copies[sid] += 1
            if sid in canon:
                continue
            bodies = [m.get("content") or "" for m in s["dialogue"]
                      if m.get("role") == "character" and m.get("turn")]
            lens = [len(b.strip()) for b in bodies]
            canon[sid] = dict(
                model=s["test_model"], seed=s["seed_id"],
                source=os.path.basename(src), hash=transcript_hash(s),
                test_model_id=s.get("test_model_id"), user_sim=sim,
                turns=len(lens),
                empty=sum(1 for n in lens if n == 0),
                stub=sum(1 for n in lens if 0 < n < MIN_CHARS),
                answered=sum(1 for n in lens if n >= MIN_CHARS),
                **defect_counts(s, bodies))
    # 13a: a session answering under 70% of its seed's modal answered count
    by_seed = defaultdict(list)
    for v in canon.values():
        by_seed[v["seed"]].append(v["answered"])
    modal = {}
    for seed, xs in by_seed.items():
        c = Counter(xs)
        modal[seed] = max(c, key=lambda k: (c[k], k))
    for v in canon.values():
        v["seed_modal_answered"] = modal[v["seed"]]
        v["blank_scene"] = v["turns"] > 0 and v["empty"] == v["turns"]
        v["partial_scene"] = (not v["blank_scene"]
                              and v["answered"] < GATE_13A * modal[v["seed"]])
    return canon, copies, errors


def load_judge_rows(path):
    return [json.loads(line) for line in read_lines(path)]


def validate_judge_rows(rows, canon, copies, judge=JUDGE):
    """Fail closed. Returns counts for the record."""
    problems, seen = [], set()
    hashed = unhashed = 0
    for r in rows:
        sid = r.get("session_id")
        if sid in seen:
            problems.append("duplicate row: %s" % sid)
            continue
        seen.add(sid)
        if r.get("judge") != judge:
            problems.append("%s: judge %r, expected %r"
                            % (sid, r.get("judge"), judge))
        if sid not in canon:
            problems.append("%s: no transcript on disk" % sid)
            continue
        c = canon[sid]
        if r.get("model") != c["model"] or r.get("seed") != c["seed"]:
            problems.append("%s: model/seed fields disagree with the id" % sid)
        for dim in DIMENSIONS:
            v = (r.get("overall") if dim == "overall"
                 else (r.get("session_dimensions") or {}).get(dim))
            if (isinstance(v, bool) or not isinstance(v, (int, float))
                    or not 1.0 <= v <= 5.0):
                problems.append("%s: %s %r outside 1-5" % (sid, dim, v))
        h = r.get("transcript_hash")
        if h:
            hashed += 1
            if h != c["hash"]:
                problems.append("%s: transcript hash %s, on disk %s (scored "
                                "on a different text)" % (sid, h, c["hash"]))
        else:
            unhashed += 1
            if copies[sid] != 1:
                problems.append("%s: no hash and %d transcripts on disk; the "
                                "score cannot be tied to one"
                                % (sid, copies[sid]))
    if problems:
        raise InputError("session_judge_v2.jsonl fails closed (%d problems):\n  %s"
                         % (len(problems), "\n  ".join(problems[:40])))
    return dict(rows=len(rows), hashed=hashed,
                unhashed_single_transcript=unhashed,
                transcripts_without_a_row=len(set(canon) - seen))


# ------------------------------------------------------------------ estimates

def dim_value(r, dim="overall"):
    """`overall`, or one of the row's session_dimensions."""
    if dim == "overall":
        return float(r["overall"])
    return float(r["session_dimensions"][dim])


def build_matrix(rows, drop=(), pool=None, dim="overall"):
    """Seeds x models `overall` (or a session dimension). `pool` pins the
    roster for a sensitivity refit, so a model that loses a dropped session is
    not also dropped from the fit."""
    per = defaultdict(dict)
    for r in rows:
        if r["session_id"] in drop:
            continue
        per[r["model"]][r["seed"]] = dim_value(r, dim)
    seeds = sorted({s for m in per.values() for s in m})
    if pool is None:
        pool = sorted(m for m in per if len(per[m]) >= MIN_SEEDS)
    else:
        pool = sorted(m for m in pool if m in per)
    short = sorted(m for m in per if m not in pool)
    X = np.full((len(seeds), len(pool)), np.nan)
    for j, m in enumerate(pool):
        for s, v in per[m].items():
            X[seeds.index(s), j] = v
    return pool, short, seeds, X, per


def seed_adjusted_means(X, w=None, max_iter=5000, tol=1e-13):
    """Two-way additive fit y = a_model + b_seed, returned as a_m + mean(b).

    For a model that played every seed this is exactly its (weighted) plain
    mean, by the normal equation for a_m. For a 12-seed model it is the mean
    it would have on the full seed set if seed difficulty is additive.
    """
    S, M = X.shape
    w = np.ones(S) if w is None else np.asarray(w, float)
    P = ~np.isnan(X)
    x = np.where(P, X, 0.0)
    W = P * w[:, None]
    rs, cs = W.sum(1), W.sum(0)
    a, b = np.zeros(M), np.zeros(S)
    prev = None
    for _ in range(max_iter):
        a0 = np.where(cs > 0, a, 0.0)      # a model with no drawn seed has no a
        b = np.where(rs > 0, ((x - a0[None, :]) * W).sum(1) / np.where(rs > 0, rs, 1), 0.0)
        a = np.where(cs > 0, ((x - b[:, None]) * W).sum(0) / np.where(cs > 0, cs, 1), np.nan)
        cur = a + (b * w).sum() / w.sum()
        if prev is not None and np.nanmax(np.abs(cur - prev)) < tol:
            break
        prev = cur
    return cur


def seed_mats(X):
    """Per-seed win and pair-count matrices; exact ties count 0.5 each way."""
    P = ~np.isnan(X)
    x = np.where(P, X, -99.0)
    gt = (x[:, :, None] > x[:, None, :] + 1e-9).astype(float)
    eq = (np.abs(x[:, :, None] - x[:, None, :]) <= 1e-9).astype(float)
    N = (P[:, :, None] & P[:, None, :]).astype(float)
    idx = np.arange(X.shape[1])
    N[:, idx, idx] = 0.0
    return (gt + 0.5 * eq) * N, N


def bt_fit(W, N, x0=None, tol=1e-9, max_iter=100):
    """Bradley-Terry MAP, N(0, 300^2) prior, Elo scale, mean anchored at 1500.

    Newton's method with step halving; the prior makes the posterior strictly
    concave, and its gradient sums to zero, so the mean lands at 0 by itself.
    """
    M = W.shape[0]
    t = np.zeros(M) if x0 is None else np.array(x0, float) - BT_ANCHOR
    s2 = BT_PRIOR_SD ** 2

    def logpost(t):
        d = (t[:, None] - t[None, :]) / BT_SCALE
        return float(np.sum(W * -np.logaddexp(0.0, -d)) - 0.5 * np.sum(t * t) / s2)

    f = logpost(t)
    for _ in range(max_iter):
        d = (t[:, None] - t[None, :]) / BT_SCALE
        p = 0.5 * (1.0 + np.tanh(0.5 * d))
        g = (W - N * p).sum(1) / BT_SCALE - t / s2
        Q = N * p * (1.0 - p) / BT_SCALE ** 2
        H = Q - np.diag(Q.sum(1)) - np.eye(M) / s2
        step = np.linalg.solve(H, g)
        lam = 1.0
        while True:
            t_new = t - lam * step
            f_new = logpost(t_new)
            if f_new >= f - 1e-12 or lam < 1e-6:
                break
            lam *= 0.5
        t, f = t_new, f_new
        if np.max(np.abs(lam * step)) < tol:
            break
    return t - t.mean() + BT_ANCHOR


def bootstrap(X, B, rng_seed=RNG_SEED):
    """Resample seeds with replacement; every model sees the same draw."""
    S, M = X.shape
    Ws, Ns = seed_mats(X)
    elo_pt = bt_fit(Ws.sum(0), Ns.sum(0))
    rng = np.random.default_rng(rng_seed)
    Dm = np.empty((B, M))
    De = np.empty((B, M))
    for i in range(B):
        c = np.bincount(rng.integers(0, S, S), minlength=S).astype(float)
        Dm[i] = seed_adjusted_means(X, c)
        De[i] = bt_fit(np.tensordot(c, Ws, 1), np.tensordot(c, Ns, 1), x0=elo_pt)
    return elo_pt, Dm, De


def _ranks(v):
    v = np.asarray(v, float)
    order = np.argsort(v, kind="mergesort")
    r = np.empty(len(v))
    r[order] = np.arange(len(v), dtype=float)
    for val in np.unique(v):               # average ranks for ties
        k = v == val
        r[k] = r[k].mean()
    return r


def spearman(a, b):
    return float(np.corrcoef(_ranks(a), _ranks(b))[0, 1])


def spearman_perm_p(a, b, n=20000, seed=RNG_SEED):
    """Two-sided permutation p; permuting b permutes its ranks."""
    ra, rb = _ranks(a), _ranks(b)
    rho = float(np.corrcoef(ra, rb)[0, 1])
    rng = np.random.default_rng(seed)
    perm = np.array([rng.permutation(rb) for _ in range(n)])
    ca, cp = ra - ra.mean(), perm - perm.mean(1, keepdims=True)
    rhos = (cp @ ca) / (np.sqrt((cp ** 2).sum(1)) * np.sqrt((ca ** 2).sum()))
    hits = int(np.sum(np.abs(rhos) >= abs(rho) - 1e-12))
    return rho, (hits + 1) / (n + 1)


# ---------------------------------------------------------------------- bands

def tier_index(v):
    """Index into TIERS: the number of letter edges v sits below. The lower
    edge belongs to the letter (3.8 is A), up to float noise."""
    return sum(1 for e in TIER_EDGES if v < e - EDGE_EPS)


def tier_letter(v):
    return TIERS[tier_index(v)][0]


def tier_label(letter):
    """'3.8 and above', '3.2-3.8', 'below 2.0'."""
    lo, hi = next((lo, hi) for L, lo, hi in TIERS if L == letter)
    if hi is None:
        return "%.1f and above" % lo
    if lo is None:
        return "below %.1f" % hi
    return "%.1f-%.1f" % (lo, hi)


def reaches_edge(lo, hi):
    """True when [lo, hi], at the 4 decimals the JSON prints, crosses a letter
    edge or ends on one. Touching counts: an end exactly on an edge is one
    bootstrap draw away from the other letter."""
    lo, hi = round(float(lo), EDGE_DP), round(float(hi), EDGE_DP)
    return any(lo <= e <= hi for e in TIER_EDGES)


def assign_tiers(means, lo=None, hi=None):
    """Fixed letters (TIERS), independent of the roster.

    Returns ({model: {...}}, meta). `edge` is True when the 95% interval of
    the mean reaches a letter edge (reaches_edge); `spans` is how many letters
    the interval's two ends fall in (1 when it stays inside one).
    """
    out = {}
    for m, v in means.items():
        L = tier_letter(v)
        edge = spans = None
        if lo is not None and hi is not None:
            edge = reaches_edge(lo[m], hi[m])
            spans = tier_index(lo[m]) - tier_index(hi[m]) + 1
        out[m] = dict(tier=L, band=tier_label(L), edge=edge, spans=spans)
    sizes = Counter(t["tier"] for t in out.values())
    letters = [L for L, _, _ in TIERS]
    meta = dict(
        top=BAND_TOP, width=BAND_WIDTH, edges=list(TIER_EDGES),
        letters={L: tier_label(L) for L in letters},
        ranges=[dict(tier=L, lower=lo, upper=hi, label=tier_label(L)) for L, lo, hi in TIERS],
        sizes={L: sizes.get(L, 0) for L in letters},
        empty=[L for L in letters if not sizes.get(L)],
        tiers=sum(1 for L in letters if sizes.get(L)),
        rule="fixed letters: A %s, B %s, C %s, D %s, E %s; edges %.1f - %.1fk, "
             "lower edge inclusive; A is open at the top (a model above 4.4 "
             "stays A) and E at the floor; frozen, never re-lettered"
             % tuple([tier_label(L) for L in letters] + [BAND_TOP, BAND_WIDTH]))
    return out, meta


def tier_count_check(meta, min_tiers=MIN_TIERS, max_tiers=MAX_TIERS):
    """Report, never apply: how many of the fixed letters are occupied."""
    n = meta["tiers"]
    return dict(tiers=n, allowed="%d-%d" % (min_tiers, max_tiers),
                within=min_tiers <= n <= max_tiers,
                note="The letters are fixed, so this only reports; five letters "
                     "exist and a roster fills some of them.")


# ------------------------------------------------------------------ watch-out

def silent_flagged(jrow):
    """analyze_round4_willingness.py's silent-refusal rule, on its own fields."""
    if not jrow:
        return False
    rate, slope = jrow.get("empty_rate_a") or 0, jrow.get("empty_rung_slope_a") or 0
    return rate >= SILENT_EMPTY_RATE and slope >= SILENT_RUNG_SLOPE


def r4_paths(results):
    """Every r4_full_*.json, newest first, refused by name if private."""
    paths = sorted(Path(results).glob(R4_GLOB), key=lambda p: p.name, reverse=True)
    for p in paths:
        _guard_path(p)
    return paths


def track_a_empty_by_rung(paths, models):
    """{model: {rung: [replies, empty]}} over Track A, for `models` only.

    The willingness analyzer's dedupe: newest file first, error rows skipped,
    the first copy of (model, seed, track) claims the key, and an unlabelled
    newest copy drops with no fallback to an older one. Only rung labels are
    read; no transcript text.
    """
    want = set(models)
    out = {m: defaultdict(lambda: [0, 0]) for m in want}
    seen = set()
    for p in paths:
        for s in read_json(p)["sessions"]:
            if "error" in s:
                continue
            key = (s.get("test_model"), s.get("seed_id"), s.get("track"))
            if key in seen:
                continue
            seen.add(key)
            if key[0] not in want or key[2] != "A" or not s.get("rung_labels"):
                continue
            for r in s["rung_labels"]:
                if r.get("rung"):
                    d = out[key[0]][r["rung"]]
                    d[0] += 1
                    d[1] += r.get("label") == "EMPTY_REPLY"
    return {m: {k: list(v) for k, v in sorted(d.items())} for m, d in out.items()}


def rung_problems(model, jrow, rungs):
    """The recount must reproduce the published rate and slope (3 decimals)."""
    n = sum(v[0] for v in rungs.values())
    e = sum(v[1] for v in rungs.values())
    lo, hi = rungs.get(RUNG_MILD), rungs.get(RUNG_EXPLICIT)
    out = []
    if not n or round(e / n, 3) != round(jrow.get("empty_rate_a") or 0, 3):
        out.append("%s: recounted %s of %s Track A replies empty, published rate %r"
                   % (model, e, n, jrow.get("empty_rate_a")))
    if (not lo or not hi or not lo[0] or not hi[0]
            or round(hi[1] / hi[0] - lo[1] / lo[0], 3)
            != round(jrow.get("empty_rung_slope_a") or 0, 3)):
        out.append("%s: recounted rungs %s, published slope %r"
                   % (model, rungs, jrow.get("empty_rung_slope_a")))
    return out


def silent_refusal(jrow, rungs=None):
    """The rule's verdict, with the counts from the rung recount."""
    if not silent_flagged(jrow):
        return None
    if not rungs:
        raise InputError("silent refusal flagged but no Track A rung recount")
    n = sum(v[0] for v in rungs.values())
    e = sum(v[1] for v in rungs.values())
    lo, hi = rungs[RUNG_MILD], rungs[RUNG_EXPLICIT]
    return dict(key="silent_refusal", count=e, of=n,
                mildest_rung=dict(rung=RUNG_MILD, count=lo[1], of=lo[0]),
                most_explicit_rung=dict(rung=RUNG_EXPLICIT, count=hi[1], of=hi[0]),
                rate=jrow["empty_rate_a"], slope=jrow["empty_rung_slope_a"],
                text="silent on explicit asks: %d of %d Track A replies empty, "
                     "%d of %d at the mildest rung and %d of %d at the most explicit"
                     % (e, n, lo[1], lo[0], hi[1], hi[0]))


def defect_totals(sessions):
    """Answered turns and leak / selfplay / loop counts over a model's sessions."""
    return dict(turns=sum(v["answered"] for v in sessions),
                leak_turns=sum(v["leak"] for v in sessions),
                selfplay_turns=sum(v["selfplay"] for v in sessions),
                loop_turns=sum(v["loop"] for v in sessions))


def watch_out(model, sessions, in_defects_file, jrow, rungs=None):
    """Counts for every defect; `shown` holds what the table prints.

    Leak / writes-your-character / loop counts are this script's recount with
    analyze_production_defects.py's rules; for a model in that file they are
    checked equal to it first (check_defects_file), and for a model the file
    skips (under 50 answered turns) they are the only count there is.
    """
    ss = sorted(sessions, key=lambda v: v["seed"])
    turns = sum(v["turns"] for v in ss)
    blank = [v for v in ss if v["blank_scene"]]
    partial = [v for v in ss if v["partial_scene"]]
    blank_turns = sum(v["turns"] for v in blank)
    empty = sum(v["empty"] for v in ss) - blank_turns
    stub = sum(v["stub"] for v in ss)
    selfsim = [v for v in ss if v["user_sim"] and v["test_model_id"] == v["user_sim"]]
    d = defect_totals(ss)
    counts = dict(
        scenes=len(ss), turns=turns,
        blank_scenes=[v["seed"] for v in blank],
        partial_scenes=[dict(seed=v["seed"], answered=v["answered"], turns=v["turns"])
                        for v in partial],
        empty_turns_outside_blank_scenes=empty, stub_turns=stub,
        answered_turns=d["turns"],
        writes_your_character=d["selfplay_turns"],
        leaks=d["leak_turns"], loops=d["loop_turns"],
        defects_source=("production_defects.json (recount matches)" if in_defects_file
                        else "counted here with analyze_production_defects.py's rules: "
                             "the file skips models under 50 answered turns"))
    shown = []
    if blank:
        shown.append(dict(key="blank_scene", count=len(blank), of=len(ss),
                          text="whole blank scene: %d of %d (%s), scored as judged and kept"
                               % (len(blank), len(ss), ", ".join(v["seed"] for v in blank))))
    if partial:
        shown.append(dict(key="partial_scene", count=len(partial), of=len(ss),
                          text="partial scene: %d of %d (%s), scored as judged and kept"
                               % (len(partial), len(ss), ", ".join(
                                   "%s, %d of %d replies" % (v["seed"], v["answered"], v["turns"])
                                   for v in partial))))
    n_short = empty + stub
    live = turns - blank_turns
    if live and n_short / live >= WATCH_MIN_RATE:
        shown.append(dict(key="stub_replies", count=n_short, of=live,
                          text="empty or stub replies: %d of %d turns under %d characters"
                               " (%d empty)" % (n_short, live, MIN_CHARS, empty)))
    base = d["turns"]
    for key, field, label in (("writes_your_character", "selfplay_turns", "writes your character"),
                              ("leaks", "leak_turns", "leaks markup or reasoning"),
                              ("loops", "loop_turns", "loops")):
        c = d[field]
        if base and c and c / base >= WATCH_MIN_RATE:
            shown.append(dict(key=key, count=c, of=base,
                              text="%s: %d of %d replies" % (label, c, base)))
    sr = silent_refusal(jrow, rungs)
    if sr:
        shown.append(sr)
    if selfsim:
        shown.append(dict(key="plays_itself", count=len(selfsim), of=len(ss),
                          text="also the user simulator: plays both sides in %d of %d scenes"
                               % (len(selfsim), len(ss))))
    return dict(counts=counts, shown=shown)


def check_defects_file(defects, canon):
    """production_defects.json must describe this corpus, turn for turn and
    count for count, and hold every model with 50 or more answered turns."""
    by_model = defaultdict(list)
    for v in canon.values():
        by_model[v["model"]].append(v)
    bad = []
    for m, d in sorted(defects.items()):
        mine = defect_totals(by_model.get(m, []))
        diff = {k: (d.get(k), mine[k]) for k in mine if d.get(k) != mine[k]}
        if diff:
            bad.append("%s: file vs corpus %s" % (m, diff))
    for m, vs in sorted(by_model.items()):
        n = sum(v["answered"] for v in vs)
        if m not in defects and n >= DEFECTS_MIN_TURNS:
            bad.append("%s: %d answered turns but not in the file" % (m, n))
    if bad:
        raise InputError("production_defects.json does not match the canonical "
                         "transcripts; rerun analyze_production_defects.py:\n  "
                         + "\n  ".join(bad[:20]))


# ------------------------------------------------------------------------- J

def j_cell(jrow):
    """J exactly as published: the file's value, printed to 2 decimals."""
    if jrow is None:
        return dict(value=None, display="not in round 4", status="not in round 4",
                    quadrant=None, unranked_reason=None)
    j = jrow.get("J")
    if j is None:
        return dict(value=None, display="no J", status="unranked", quadrant=None,
                    unranked_reason=jrow.get("unranked_reason"))
    ranked = bool(jrow.get("ranked"))
    return dict(value=j, display=("%+.2f" % j) + ("" if ranked else " unranked"),
                status="ranked" if ranked else "unranked",
                quadrant=jrow.get("quadrant"),
                unranked_reason=None if ranked else jrow.get("unranked_reason"))


# --------------------------------------------------------------- cross-judge

def _score(v):
    return v.get("score") if isinstance(v, dict) else v


def load_external_scores(path, canon):
    """Per-session `overall` from a blind package pass or a JSONL of rows.

    A package pass directory holds external_part*.json; its _manifest.json
    (same directory or the parent) maps opaque ids and records the transcript
    hash each session was judged on; a row may carry its own hash instead
    (a merged view with reused rows). A row judged on a transcript that has
    since been replaced, or with no hash at all, is dropped and counted, not
    failed: an external sample drawn before a re-run is expected to carry some.
    """
    p = Path(path)
    out, stale, unknown = {}, 0, 0
    keymap, hashes = {}, {}
    if p.is_dir():
        man = p / "_manifest.json"
        if not man.exists():
            man = p.parent / "_manifest.json"
        m = read_json(man)
        keymap, hashes = m.get("keymap") or {}, m.get("transcript_hashes") or {}
        rows = []
        for f in sorted(p.glob("external_part*.json")):
            rows += read_json(f)
    else:
        rows = [json.loads(line) for line in read_lines(p)]
    for r in rows:
        sid = keymap.get(r.get("session_id"), r.get("session_id"))
        ov = _score(r.get("overall"))
        if ov is None or sid not in canon:
            unknown += 1
            continue
        if (r.get("transcript_hash") or hashes.get(sid)) != canon[sid]["hash"]:
            stale += 1
            continue
        out[sid] = float(ov)
    return out, dict(stale_or_unhashed_dropped=stale, unmatched_dropped=unknown)


def cross_judge_block(name, scores, meta, sonnet, pool):
    """Per-model means for a second judge, set on Sonnet's scale across models.

    Each judge's model means (on the sessions both scored) are standardised
    across models to Sonnet's mean and sd, so the flag reads relative position
    and not the judge's use of the scale (18a: two thirds of the raw spread is
    scale). A model moved by more than the card's 0.3 band is flagged.
    """
    per = defaultdict(list)
    for sid, v in scores.items():
        if sid in sonnet and sonnet[sid][0] in pool:
            per[sonnet[sid][0]].append((v, sonnet[sid][1]))
    ok = sorted(m for m, v in per.items() if len(v) >= CROSS_MIN_SESSIONS)
    rows = {}
    if len(ok) >= 3:
        cm = np.array([np.mean([a for a, _ in per[m]]) for m in ok])
        sm = np.array([np.mean([b for _, b in per[m]]) for m in ok])
        z = (cm - cm.mean()) / (cm.std() or 1.0) * sm.std() + sm.mean()
        for i, m in enumerate(ok):
            diff = float(z[i] - sm[i])
            rows[m] = dict(n_sessions=len(per[m]), mean=round(float(cm[i]), 3),
                           sonnet_mean_same_sessions=round(float(sm[i]), 3),
                           on_sonnet_scale=round(float(z[i]), 3),
                           difference=round(diff, 3), flag=abs(diff) > CROSS_FLAG)
    for m, v in per.items():
        if m not in rows:
            rows[m] = dict(n_sessions=len(v), note="fewer than %d sessions: no per-model "
                                                   "figure" % CROSS_MIN_SESSIONS)
    top = dict(name=name, sessions=sum(len(v) for v in per.values()),
               models_with_a_figure=len(ok), min_sessions=CROSS_MIN_SESSIONS,
               flag_rule="|difference| > %.1f after setting both judges' model means on "
                         "Sonnet's mean and sd across these models" % CROSS_FLAG,
               flagged=sorted(m for m, r in rows.items() if r.get("flag")), **meta)
    return top, rows


# --------------------------------------------------------------------- checks

def _tilts(S, x, claude, W):
    """Claude-vs-all and Claude-vs-non-Claude tilt of Sonnet over judge x, one
    per row of the weight matrix W (draws x sessions). A weight is how many
    times the session's model was drawn; all-ones is the point estimate. The
    other judge is rescaled to Sonnet's mean and sd inside each draw."""
    tot = W.sum(1)

    def mean(v):
        return (W * v).sum(1) / tot

    def sd(v, mu):
        return np.sqrt((W * (v - mu[:, None]) ** 2).sum(1) / tot)

    mx, ms = mean(x), mean(S)
    xz = (x - mx[:, None]) / sd(x, mx)[:, None] * sd(S, ms)[:, None] + ms[:, None]
    d = S - xz
    wc, wn = W * claude, W * ~claude
    with np.errstate(invalid="ignore", divide="ignore"):
        dc = (wc * d).sum(1) / wc.sum(1)
        dn = (wn * d).sum(1) / wn.sum(1)
    return dc - mean(d), dc - dn


def three_family_check(results, canon, sonnet, draws=MODEL_BOOT, rng_seed=RNG_SEED):
    """Sonnet's tilt toward Claude against each other family, corpus level only.

    Only Claude is shifted by any correction, so the size that matters is
    Claude minus non-Claude; Claude minus all sessions is kept for the record.
    The SE and 95% interval resample MODELS with replacement (every session of
    a drawn model comes along), because sessions of one model are not
    independent; the same model draws serve both families.
    """
    judges = {}
    for fam, parts in THREE_FAMILY.items():
        got, meta = {}, Counter()
        for pkg, sub in parts:
            d = Path(results) / pkg / sub
            if not d.exists():
                return dict(skipped="missing %s" % d)
            s, m = load_external_scores(d, canon)
            got.update(s)
            meta.update(m)
        judges[fam] = (got, dict(meta))
    common = sorted(set(judges["chatgpt"][0]) & set(judges["gemini"][0]) & set(sonnet))
    if len(common) < 20:
        return dict(skipped="only %d sessions scored by all three" % len(common))
    S = np.array([sonnet[s][1] for s in common])
    models = [sonnet[s][0] for s in common]
    claude = np.array([m.startswith("claude_") for m in models])
    per_model = Counter(models)
    roster = sorted(per_model)
    midx = np.array([roster.index(m) for m in models])
    rng = np.random.default_rng(rng_seed)
    counts = np.stack([np.bincount(rng.integers(0, len(roster), len(roster)),
                                   minlength=len(roster)) for _ in range(draws)])
    Wb = counts[:, midx].astype(float)
    ok = ((Wb * claude).sum(1) > 0) & ((Wb * ~claude).sum(1) > 0)
    Wb = Wb[ok]
    out = dict(sessions=len(common), models=len(roster),
               sessions_per_model=[min(per_model.values()), max(per_model.values())],
               claude_sessions=int(claude.sum()),
               claude_models=len({m for m in models if m.startswith("claude_")}),
               stale_or_unhashed_dropped={f: judges[f][1]["stale_or_unhashed_dropped"] for f in judges},
               note="Corpus level only: %d to %d sessions per model, too few for a "
                    "per-model figure. Nothing in the overview is adjusted by it. The "
                    "tilt is relative: it cannot say whether Sonnet is generous to "
                    "Claude or the others are harsh (ROUND4_DESIGN 17b)."
                    % (min(per_model.values()), max(per_model.values())),
               method="each judge rescaled to Sonnet's mean and sd over these "
                      "sessions; tilt = mean(Sonnet - other) on Claude sessions "
                      "minus the same on non-Claude sessions (vs_non_claude, the "
                      "size a Claude-only correction uses) or on all sessions "
                      "(vs_all_sessions); SE and 95%% interval from %d draws that "
                      "resample models with replacement, numpy default_rng(%d), "
                      "rescaling inside each draw" % (draws, rng_seed),
               model_draws=int(ok.sum()), model_draws_skipped=int((~ok).sum()),
               tilt={})
    one = np.ones((1, len(common)))
    for fam in ("chatgpt", "gemini"):
        x = np.array([judges[fam][0][s] for s in common])
        va, vn = (float(v[0]) for v in _tilts(S, x, claude, one))
        ba, bn = _tilts(S, x, claude, Wb)
        out["tilt"][fam] = dict(
            vs_non_claude=round(vn, 3),
            vs_non_claude_se_model_resampled=round(float(bn.std(ddof=1)), 3),
            vs_non_claude_95_model_resampled=[round(float(v), 3) for v in
                                              np.percentile(bn, [2.5, 97.5])],
            vs_all_sessions=round(va, 3),
            vs_all_sessions_se_model_resampled=round(float(ba.std(ddof=1)), 3),
            vs_all_sessions_95_model_resampled=[round(float(v), 3) for v in
                                                np.percentile(ba, [2.5, 97.5])])
    return out


def human_check(results, means, tiers):
    path = Path(results) / "multiturn_arena_bayesian.json"
    if not path.exists():
        return dict(skipped="missing %s" % path.name)
    h = read_json(path)
    hum = {r["model"]: r["elo_mean"] for r in h["leaderboard"]}
    out = dict(source=path.name, votes=h.get("n_votes"), voters=h.get("n_voters"),
               note="Public file only. Spearman against the Sonnet 5 judge mean; "
                    "p from 20000 label permutations.")
    for label, excl in (("all", ()), ("without the user simulator", ("gemini_2_5_flash",))):
        ms = sorted(m for m in hum if m in means and m not in excl)
        rho, p = spearman_perm_p([means[m] for m in ms], [hum[m] for m in ms])
        out[label] = dict(n=len(ms), spearman=round(rho, 3), p=round(p, 4))
    by = defaultdict(list)
    for m in hum:
        if m in tiers:
            by[tiers[m]["tier"]].append(hum[m])
    out["human_mean_by_tier"] = {t: dict(n=len(v), mean=round(float(np.mean(v)), 1))
                                 for t, v in sorted(by.items())}
    return out


def tier_shift_check(rows, drop_ids, pool, base_tiers, shift=None):
    """Re-tier after dropping sessions or shifting a group; list what moves.
    The letters are fixed, so only the moved models' own letters change."""
    if shift is not None:
        rows = [dict(r, overall=r["overall"] - (shift[1] if r["model"].startswith(shift[0]) else 0))
                for r in rows]
    p2, _, _, X2, _ = build_matrix(rows, drop=drop_ids, pool=pool)
    m2 = dict(zip(p2, seed_adjusted_means(X2)))
    t2, meta2 = assign_tiers({m: m2[m] for m in pool if m in m2})
    moved = sorted(m for m in pool if m in t2 and t2[m]["tier"] != base_tiers[m]["tier"])
    return dict(tier_changes=[dict(model=m, from_tier=base_tiers[m]["tier"],
                                   to_tier=t2[m]["tier"], mean_after=round(float(m2[m]), 4))
                              for m in moved],
                tier_sizes_after=meta2["sizes"])


# ---------------------------------------------------------------------- build

def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def judge_means_block(rows, pool, short, per, seeds, tiers):
    """Per-model means of `overall` and the three session dimensions the judge
    table shows. A tiered model's means are the same two-way seed fit its tier
    uses (the plain mean for a model that played every seed); an untiered one
    has too few seeds for the fit and gets plain means."""
    fits = {}
    for dim in DIMENSIONS:
        p, _, _, Xd, perd = build_matrix(rows, pool=pool, dim=dim)
        fits[dim] = (dict(zip(p, seed_adjusted_means(Xd))),
                     dict(zip(p, np.nanmean(Xd, 0))), perd)
    n_all = len(seeds)
    n_rows = Counter(r["model"] for r in rows)
    models = {}
    for m in sorted(list(pool) + list(short)):
        tiered = m in tiers
        entry = dict(tier=tiers[m]["tier"] if tiered else None,
                     n_sessions=n_rows[m], n_seeds=len(per[m]),
                     basis="seed_adjusted" if tiered else "plain",
                     note=None if tiered else "%d of %d seeds" % (len(per[m]), n_all))
        for dim in DIMENSIONS:
            adj, plain, perd = fits[dim]
            if tiered:
                entry[dim] = round(float(adj[m]), 4)
                entry[dim + "_plain"] = round(float(plain[m]), 4)
            else:
                v = float(np.mean(list(perd[m].values())))
                entry[dim] = entry[dim + "_plain"] = round(v, 4)
        models[m] = entry
    return dict(
        judge=JUDGE, scale="1-5",
        dimensions=list(DIMENSIONS),
        definition="Mean of the Sonnet 5 session judge's `overall` and of its S.5 "
                   "agency, S.1 consistency and S.3 momentum session scores. A tiered "
                   "model's means use the same model + seed fit as its tier, so a "
                   "model that played all %d seeds gets its plain mean and one that "
                   "played 12 gets its mean set on all %d; `_plain` keeps the plain "
                   "mean. An untiered model (under %d seeds) gets plain means and no "
                   "tier. Tiers are assigned on the unrounded `overall`." % (
                       n_all, n_all, MIN_SEEDS),
        models=models)


def build(results, boot=BOOT_DEFAULT, rng_seed=RNG_SEED, cross=()):
    results = Path(results)
    canon, copies, errors = load_corpus(results)
    sj_path = results / "session_judge_v2.jsonl"
    rows = load_judge_rows(sj_path)
    val = validate_judge_rows(rows, canon, copies)

    defects_path = results / "production_defects.json"
    defects = read_json(defects_path)["per_model"] if defects_path.exists() else {}
    check_defects_file(defects, canon)

    j_path = results / "round4_willingness_leaderboard.json"
    jfile = read_json(j_path) if j_path.exists() else {"leaderboard": []}
    jrows = {r["model"]: r for r in jfile["leaderboard"]}

    # silent refusal: the rung counts come from the round 4 runs themselves,
    # and must reproduce the rate and slope the J file publishes
    silent = sorted(m for m, r in jrows.items() if silent_flagged(r))
    r4_used, rungs = [], {}
    if silent:
        r4_used = r4_paths(results)
        if not r4_used:
            raise InputError("silent refusal flagged for %s but no %s in %s"
                             % (silent, R4_GLOB, results))
        rungs = track_a_empty_by_rung(r4_used, silent)
        bad = [p for m in silent for p in rung_problems(m, jrows[m], rungs[m])]
        if bad:
            raise InputError("the Track A rung recount does not reproduce "
                             "round4_willingness_leaderboard.json:\n  " + "\n  ".join(bad))

    pool, short, seeds, X, per = build_matrix(rows)
    Ws, Ns = seed_mats(X)
    npairs = float(Ns.sum() / 2)
    ties = float(((Ws == 0.5) & (Ns == 1)).sum() / 2)
    mean_pt = seed_adjusted_means(X)
    plain = np.nanmean(X, 0)
    elo_pt, Dm, De = bootstrap(X, boot, rng_seed)
    m_lo, m_hi = np.nanpercentile(Dm, [2.5, 97.5], axis=0)
    e_lo, e_hi = np.percentile(De, [2.5, 97.5], axis=0)
    ranks = np.argsort(np.argsort(-De, axis=1), axis=1) + 1
    r_lo = np.percentile(ranks, 2.5, axis=0, method="lower")
    r_hi = np.percentile(ranks, 97.5, axis=0, method="higher")
    # the same draws with the shared seed-difficulty shift taken out: how much
    # of each interval is "these 20 seeds" rather than "this model"
    shift = Dm.mean(1) - mean_pt.mean()
    Dr = Dm - shift[:, None]
    rel_lo, rel_hi = np.nanpercentile(Dr, [2.5, 97.5], axis=0)

    means = dict(zip(pool, mean_pt))
    lo = dict(zip(pool, m_lo))
    hi = dict(zip(pool, m_hi))
    tiers, meta = assign_tiers(means, lo, hi)
    tcheck = tier_count_check(meta)
    rel_edge = sorted(m for i, m in enumerate(pool) if reaches_edge(rel_lo[i], rel_hi[i]))

    sessions_by_model = defaultdict(list)
    for v in canon.values():
        sessions_by_model[v["model"]].append(v)
    flagged_ids = sorted(sid for sid, v in canon.items()
                         if v["blank_scene"] or v["partial_scene"])
    sonnet = {r["session_id"]: (r["model"], float(r["overall"])) for r in rows}

    # ---- round4_judge_elo.json
    elo_models = []
    for i, m in enumerate(pool):
        elo_models.append(dict(
            model=m, n_seeds=int((~np.isnan(X[:, i])).sum()),
            elo=round(float(elo_pt[i]), 1), elo_lo=round(float(e_lo[i]), 1),
            elo_hi=round(float(e_hi[i]), 1), rank_lo=int(r_lo[i]), rank_hi=int(r_hi[i]),
            mean=round(float(mean_pt[i]), 4), mean_plain=round(float(plain[i]), 4),
            mean_lo=round(float(m_lo[i]), 4), mean_hi=round(float(m_hi[i]), 4),
            mean_lo_without_shared_seed_shift=round(float(rel_lo[i]), 4),
            mean_hi_without_shared_seed_shift=round(float(rel_hi[i]), 4)))
    inputs = {p.name: sha(p) for p in
              [sj_path, defects_path, j_path] + [Path(s) for s in session_sources(results)]
              + list(r4_used)
              if p.exists()}
    elo_doc = dict(
        name="Round 4 judge ELO: Sonnet 5 session judge on the craft-baseline corpus",
        read_this_first="A re-expression of the judge's `overall` scores, not new "
                        "information and not a rank (Spearman %.3f with the "
                        "seed-adjusted mean). 100 points means Sonnet 5 scored the "
                        "higher model higher on about 64%% of the scenarios both "
                        "played, ties counted half; no preference between two "
                        "conversations was ever asked for. Pool-relative: adding a "
                        "model moves every figure. Not comparable to arena ELO. On the "
                        "profile cards 'craft band' is the flaw hunter; this file is "
                        "not that." % spearman(elo_pt, mean_pt),
        method=dict(
            signal="overall, session_judge_v2.jsonl, judge %s" % JUDGE,
            transcripts="newest source wins per session_id (transcript_hash.py rule); "
                        "fails closed on a hash mismatch",
            blank_and_partial_sessions="kept as scored (a blank scene is 1.0) and "
                                       "flagged; dropping them would reward silence (13a)",
            pairs="every pair of models that both played a seed; higher overall wins, "
                  "an exact tie is 0.5 each way; no sub-score tiebreak",
            fit="Bradley-Terry MAP, N(0, %d^2) prior, 400/ln10 scale, mean anchored "
                "at %d, Newton's method" % (BT_PRIOR_SD, BT_ANCHOR),
            mean="two-way additive fit (model + seed), reported as the model's mean "
                 "over all seeds; identical to the plain mean for a model that played "
                 "every seed",
            interval="seed bootstrap, %d draws, numpy default_rng(%d); covers which "
                     "seeds were drawn, not judge disagreement" % (boot, rng_seed),
            min_seeds=MIN_SEEDS),
        corpus=dict(canonical_sessions=len(canon), judge_rows=val,
                    sessions_in_fit=int((~np.isnan(X)).sum()), models=len(pool),
                    seeds=len(seeds), matched_pairs=int(npairs),
                    tie_share=round(ties / npairs, 4) if npairs else None,
                    flagged_sessions_kept=flagged_ids),
        not_fitted={m: "%d of %d seeds, under the %d-seed minimum"
                       % (len(per[m]), len(seeds), MIN_SEEDS) for m in short},
        spearman_elo_vs_mean=round(spearman(elo_pt, mean_pt), 4),
        models=elo_models,
        inputs=inputs)

    # ---- round4_overview.json
    cross_top, cross_rows = {}, defaultdict(dict)
    for name, path in cross:
        scores, meta_c = load_external_scores(path, canon)
        top, per_model = cross_judge_block(name, scores, dict(source=str(path), **meta_c),
                                           sonnet, set(pool))
        cross_top[name] = top
        for m, r in per_model.items():
            cross_rows[m][name] = r

    def row(m, tiered):
        seeds_played = len(per.get(m, {}))
        r = dict(model=m, n_seeds=seeds_played,
                 judge_tier=(dict(tier=tiers[m]["tier"], band=tiers[m]["band"],
                                  edge=tiers[m]["edge"]) if tiered else None),
                 J=j_cell(jrows.get(m)),
                 watch_out=watch_out(m, sessions_by_model.get(m, []), m in defects,
                                     jrows.get(m), rungs.get(m)),
                 cross_judges=dict(cross_rows.get(m, {})))
        return r

    ov_rows = sorted((row(m, True) for m in pool),
                     key=lambda r: (r["judge_tier"]["tier"], r["model"]))
    unranked = [dict(row(m, False), reason="%d of %d seeds, under the %d-seed minimum"
                     % (len(per[m]), len(seeds), MIN_SEEDS)) for m in short]
    absent = []
    for m in sorted(set(errors) | set(jrows)):
        if m is None or m in per or any(v["model"] == m for v in canon.values()):
            continue
        errs = errors.get(m) or []
        if errs:
            why = "all %d craft sessions errored (%s)" % (
                len(errs), Counter(e.split(". ")[0] for _, e in errs).most_common(1)[0][0])
        else:
            why = "no craft-baseline run"
        jr = jrows.get(m)
        absent.append(dict(model=m, reason=why, J=j_cell(jr) if jr else None))

    blank_check = tier_shift_check(rows, set(flagged_ids), pool, tiers)
    blank_check["dropped_sessions"] = flagged_ids
    self_pref = three_family_check(results, canon, sonnet)
    claude_shift = {}
    if "tilt" in self_pref:
        claude_models = sorted(m for m in pool if m.startswith("claude_"))
        for fam, t in self_pref["tilt"].items():
            at = {}
            for label, size in (("measured", t["vs_non_claude"]),
                                ("interval_upper", t["vs_non_claude_95_model_resampled"][1])):
                chk = tier_shift_check(rows, set(), pool, tiers, shift=("claude_", size))
                at[label] = dict(shift=-size, claude_models=len(claude_models),
                                 claude_models_changing_tier=len(chk["tier_changes"]),
                                 **chk)
            claude_shift[fam] = dict(
                basis="Claude minus non-Claude (vs_non_claude): only Claude is shifted",
                **at)
        floor = {L: lo for L, lo, _ in TIERS}
        room = sorted((means[m] - floor[tiers[m]["tier"]], m) for m in claude_models
                      if floor[tiers[m]["tier"]] is not None)
        if room:
            claude_shift["smallest_shift_that_moves_a_claude_model"] = dict(
                model=room[0][1], more_than=round(float(room[0][0]), 3),
                note="a Claude-only shift has to exceed this to move any Claude model "
                     "down a letter")
    edge_models = sorted(m for m in pool if tiers[m]["edge"])
    spans3 = sorted(m for m in pool if (tiers[m]["spans"] or 0) >= 3)
    j_status = Counter(r["J"]["status"] for r in ov_rows)

    overview = dict(
        title="Round 4 overview",
        read_this_first="Three columns side by side. Nothing is summed and there is "
                        "no position: rows inside a tier are alphabetical.",
        columns=dict(
            judge_tier=dict(
                label="Judge tier (Sonnet 5)",
                definition="Fixed letters on one judge's 1-5 `overall` mean (Sonnet 5, "
                           "session_judge_v2.jsonl): %s. Edges %.1f - %.1fk, lower edge "
                           "inclusive; A is open at the top and E at the floor. The "
                           "letters are frozen and never re-lettered." % (
                               ", ".join("%s %s" % kv for kv in meta["letters"].items()),
                               BAND_TOP, BAND_WIDTH),
                caveats=["One judge. Sonnet and Gemini agree per model (r +0.97); "
                         "ChatGPT scores 0.77 lower on average and reorders the top "
                         "(ROUND4_DESIGN 15b, 18).",
                         "Not the 'craft band' on the profile cards, which is the flaw "
                         "hunter.",
                         "The interval covers which seeds were drawn, not judge "
                         "disagreement."]),
            J=dict(label="J (round 4 judgment)",
                   definition="Copied from round4_willingness_leaderboard.json, printed "
                              "to 2 decimals. Treat models within ~0.3 as tied.",
                   source=j_path.name),
            watch_out=dict(label="Watch out",
                           definition="Counts, never a score. Scene-level items always "
                                      "show; turn-level items show at %.0f%% of turns or "
                                      "more, and every count is in `counts`."
                                      % (100 * WATCH_MIN_RATE))),
        definitions=dict(
            blank_scene="every model turn in the session has no visible text; the "
                        "judge's score (1.0) stays in the mean",
            partial_scene="answered turns (at least %d characters) under %.0f%% of the "
                          "seed's modal count (ROUND4_DESIGN 13a); kept as scored"
                          % (MIN_CHARS, 100 * GATE_13A),
            stub_replies="a turn with fewer than %d visible characters, including "
                         "empty ones, outside blank scenes; denominator is every turn "
                         "outside blank scenes" % MIN_CHARS,
            writes_your_character="production_defects.json selfplay rule: the reply "
                                  "writes a turn under the user character's speaker "
                                  "label; denominator is answered turns",
            leaks="production_defects.json leak rule: harness prompt, chat-template "
                  "token or reasoning tag inside the reply",
            loops="production_defects.json loop rule: at least 35% of a turn's 8-grams "
                  "repeat an earlier 8-gram in the same turn",
            defects_source="leak, writes-your-character and loop counts are recounted "
                           "here with analyze_production_defects.py's own functions; for "
                           "a model in production_defects.json the recount must equal "
                           "the file, and a model the file skips (under %d answered "
                           "turns) is counted here" % DEFECTS_MIN_TURNS,
            silent_refusal="round 4 Track A: at least %.0f%% of replies empty and the "
                           "empty rate at least %.0f points higher on the most "
                           "explicit rung than the mildest (analyze_round4_willingness."
                           "py rule); J cannot see it. The counts are recounted from "
                           "the round 4 runs and must reproduce the published rate and "
                           "slope" % (100 * SILENT_EMPTY_RATE, 100 * SILENT_RUNG_SLOPE),
            plays_itself="the model is also the user simulator for this corpus "
                         "(config user_sim_model), so on its own row it talks to itself"),
        bands=dict(meta, edge_marked=len(edge_models), edge_models=edge_models,
                   edge_clear=len(pool) - len(edge_models),
                   edge_rule="JSON only, never rendered: the 95% seed-bootstrap "
                             "interval of the mean, at 4 decimals, crosses a letter "
                             "edge or ends on one (touching counts)",
                   edge_marked_without_shared_seed_shift=len(rel_edge),
                   interval_spans_three_tiers=spans3,
                   tier_count_check=tcheck,
                   note="The letters are fixed: adding a model, dropping a session or "
                        "a new bootstrap moves a model only by moving its own mean, "
                        "and a model above 4.4 stays A."),
        rows=ov_rows,
        unranked=unranked,
        absent=absent,
        judge_means=judge_means_block(rows, pool, short, per, seeds, tiers),
        counts=dict(tiered=len(ov_rows), j_ranked=j_status.get("ranked", 0),
                    j_unranked=j_status.get("unranked", 0),
                    j_not_in_round_4=j_status.get("not in round 4", 0),
                    j_not_in_round_4_models=sorted(r["model"] for r in ov_rows
                                                   if r["J"]["status"] == "not in round 4"),
                    watch_out_rows=sum(1 for r in ov_rows if r["watch_out"]["shown"])),
        cross_judges=cross_top,
        checks=dict(
            blank_sessions_dropped=blank_check,
            self_preference=self_pref,
            claude_shift_by_measured_tilt=claude_shift,
            human_multiturn_arena=human_check(results, means, tiers)),
        judge_elo=dict(file=OUT_ELO, note="ELO and rank range live there only"),
        inputs=inputs)
    return elo_doc, overview


# ---------------------------------------------------------------------- render

def _cross_cell(r, name):
    c = (r.get("cross_judges") or {}).get(name)
    if not c:
        return "-"
    if "difference" not in c:
        return "- (%d sessions)" % c["n_sessions"]
    return ("moves %+.2f" % c["difference"]) if c["flag"] else "within 0.3"


def render_markdown(ov):
    """Tiers in letter order, rows alphabetical inside a tier, no figures and
    no edge marker (that stays in the JSON)."""
    lines = []
    b = ov["bands"]
    names = sorted(ov.get("cross_judges") or {})
    head = ["Judge tier (Sonnet 5)", "Model", "J", "Watch out"] + [
        "Second judge (%s)" % n for n in names]
    lines.append("| %s |" % " | ".join(head))
    lines.append("|%s" % ("---|" * len(head)))
    seeds = max([r["n_seeds"] for r in ov["rows"]] or [0])
    for r in ov["rows"]:
        t = r["judge_tier"]
        model = "`%s`" % r["model"]
        if r["n_seeds"] < seeds:
            model += " (%d of %d seeds)" % (r["n_seeds"], seeds)
        cells = [t["tier"], model, r["J"]["display"],
                 "; ".join(w["text"] for w in r["watch_out"]["shown"])]
        lines.append("| %s |" % " | ".join(cells + [_cross_cell(r, n) for n in names]))
    for r in ov["unranked"]:
        cells = ["unranked", "`%s` (%s)" % (r["model"], r["reason"]), r["J"]["display"],
                 "; ".join(w["text"] for w in r["watch_out"]["shown"])]
        lines.append("| %s |" % " | ".join(cells + ["-" for _ in names]))
    legend = ", ".join("%s %s" % (k, v) for k, v in b["letters"].items())
    return "Tiers (fixed): %s.\n\n%s\n" % (legend, "\n".join(lines))


def summary(elo_doc, ov):
    b = ov["bands"]
    out = ["Judge tiers (fixed letters, width %.1f): %d of %d letters occupied, sizes %s"
           % (b["width"], b["tiers"], len(b["letters"]), b["sizes"]),
           "  letters %s" % b["letters"],
           "  edge-marked (JSON only) %d of %d, clear %d; %d with the shared seed shift "
           "removed; interval spans three tiers: %s"
           % (b["edge_marked"], len(ov["rows"]), b["edge_clear"],
              b["edge_marked_without_shared_seed_shift"], b["interval_spans_three_tiers"])]
    tc = b["tier_count_check"]
    if not tc["within"]:
        out.append("  TIER COUNT %d is outside %s (reported, not changed)"
                   % (tc["tiers"], tc["allowed"]))
    for t in b["letters"]:
        ms = [r for r in ov["rows"] if r["judge_tier"]["tier"] == t]
        out.append("  %s %s (%d): %s" % (t, b["letters"][t], len(ms), ", ".join(
            r["model"] + ("*" if r["judge_tier"]["edge"] else "") for r in ms)))
    out.append("  (* = interval reaches a letter edge; JSON only)")
    sp = ov["checks"]["self_preference"]
    for fam, t in (sp.get("tilt") or {}).items():
        cs = ov["checks"]["claude_shift_by_measured_tilt"][fam]
        out.append("Claude tilt vs %s: %+.3f vs non-Claude (model-resampled SE %.3f, 95%% %s); "
                   "%+.3f vs all. Shift %.3f moves %d of %d Claude models %s; at the "
                   "interval's upper end %.3f, %d"
                   % (fam, t["vs_non_claude"], t["vs_non_claude_se_model_resampled"],
                      t["vs_non_claude_95_model_resampled"], t["vs_all_sessions"],
                      cs["measured"]["shift"], cs["measured"]["claude_models_changing_tier"],
                      cs["measured"]["claude_models"],
                      [(c["model"], c["from_tier"], c["to_tier"])
                       for c in cs["measured"]["tier_changes"]],
                      cs["interval_upper"]["shift"],
                      cs["interval_upper"]["claude_models_changing_tier"]))
    bc = ov["checks"]["blank_sessions_dropped"]["tier_changes"]
    out.append("Dropping the %d flagged sessions changes tier for: %s"
               % (len(ov["checks"]["blank_sessions_dropped"]["dropped_sessions"]),
                  [(c["model"], c["from_tier"], c["to_tier"]) for c in bc]))
    c = elo_doc["corpus"]
    out.append("ELO: %d models, %d sessions, %d matched pairs, ties %.1f%%, Spearman vs mean %.3f"
               % (c["models"], c["sessions_in_fit"], c["matched_pairs"], 100 * c["tie_share"],
                  elo_doc["spearman_elo_vs_mean"]))
    out.append("Unranked: %s" % [r["model"] for r in ov["unranked"]])
    out.append("Absent: %s" % [(a["model"], a["reason"]) for a in ov["absent"]])
    out.append("Watch-out rows: %d" % ov["counts"]["watch_out_rows"])
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
    ap.add_argument("--out-dir", default=None, help="default: --results")
    ap.add_argument("--boot", type=int, default=BOOT_DEFAULT)
    ap.add_argument("--rng-seed", type=int, default=RNG_SEED)
    ap.add_argument("--markdown", default=None, help="also write the rendered table here")
    ap.add_argument("--cross-judge", action="append", default=[], metavar="NAME=PATH",
                    help="a second judge's scores: a blind-package pass directory or "
                         "a JSONL of {session_id, overall, transcript_hash}")
    a = ap.parse_args(argv)
    cross = []
    for spec in a.cross_judge:
        name, _, path = spec.partition("=")
        if not re.fullmatch(r"[a-z0-9_]+", name) or not path:
            ap.error("--cross-judge wants NAME=PATH, got %r" % spec)
        cross.append((name, path))
    try:
        elo_doc, ov = build(a.results, a.boot, a.rng_seed, cross)
    except InputError as e:
        print("FAIL CLOSED, nothing written.\n%s" % e, file=sys.stderr)
        return 2
    out = Path(a.out_dir or a.results)
    dump(elo_doc, out / OUT_ELO)
    dump(ov, out / OUT_OVERVIEW)
    if a.markdown:
        Path(a.markdown).write_text(render_markdown(ov))
    print(summary(elo_doc, ov))
    print("wrote %s and %s" % (out / OUT_ELO, out / OUT_OVERVIEW))
    return 0


if __name__ == "__main__":
    sys.exit(main())
