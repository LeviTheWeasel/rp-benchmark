#!/usr/bin/env python3
"""Round-4 PlotPoints export: Track A arena sessions, the J board, model cards.

Writes the files the PlotPoints site (VAUDEVILLE apps/plot) reads for round 4.
Nothing is written anywhere unless --dest names the output; --check is a dry
run that prints counts and guard results and writes nothing at all.

  sessions  Track A ladders for the human arena: manifest.json, pair-index.json
            and sessions.json in a folder named round-4-<track> (the site serves
            any folder there, so the gate must deploy first). A balanced pair
            design: every model meets R opponents per seed it has a session on.
            The pool is blind: manifest.json (sent to browsers) names no model
            and says nothing about how the pairs were drawn; see "Blind pairs"
            below. Needs PLOTPOINTS_PAIR_ID_SECRET, --check included.
  board     round-4.json: the J leaderboard, aggregates only.
  cards     model-cards.json: generate_profile_cards_v2's own cards, as data,
            plus each card's `judge` row and the top-level `judge_table`
            for the index (from results/round4_overview.json), and each
            card's `across_rounds` block with the `across_rounds_table`
            header (from results/round4_continuity.json).
  youth     The lexical screen for minor-coded terms alone; writes the review
            list to --review-out (never into a git checkout).

Publication rules this script enforces (docs/ROUND4_DESIGN.md sec 9):
  * Track A only. No Track B text or id reaches any output: Track B rows are
    skipped by `track` before a key is claimed, every exported seed id must be
    r4_a_(intimacy|gore)_NN and in the Track A seed file, publication_guards
    runs over every output object, and the sessions, manifest and pair-index
    bytes are scanned for r4_b_, B-hard and B-policy. (The board and cards say
    "B-hard" in their definitions on purpose, so they get a key allowlist.)
  * Private files are refused by name before a byte is read (_guard_path).
    harness/r4_private.py is never imported: its load_r4 rejoins Track B text.
  * Allowlisted keys only, in every object of every output.
  * Craft and subjective scores leave only as bands (cell indexes), never as
    a figure, and production-defect examples (quoted model output) stay out.
    The one exception, by Levi's decision for the cards index: each card's
    `judge` row (Sonnet 5 session-judge means to ONE decimal, Round 03's table
    format) and the `judge_table` header, from round4_overview.json. No
    interval, edge marker or unrounded figure leaves with it.
  * The second exception, by Levi's decision for continuity (2026-09-27): the
    old judge (Sonnet 4, the round-2/3 judge) on round-4 transcripts leaves
    as a BAND, a mean and its +/- half width to two decimals, on the board
    rows and in each card's `across_rounds`. Never a rank or a position:
    the guards refuse one. Round 3's published table position leaves as it
    was published, with its tie range. Nothing is translated between judges.
  * Inputs must match git HEAD; source_commit records which HEAD.

Usage:
  python3 export_plotpoints_round4.py --check
  python3 export_plotpoints_round4.py sessions --check [--matchings 4]
  python3 export_plotpoints_round4.py youth --review-out /tmp/r4_youth.tsv
  python3 export_plotpoints_round4.py sessions \\
      --dest .../apps/plot/src/content/plotpoints/sessions/round-4-ladder \\
      --review-out /tmp/r4_youth.tsv [--exclude reviewed_exclusions.txt]
  python3 export_plotpoints_round4.py board --dest .../lib/plotpoints/round-4.json
  python3 export_plotpoints_round4.py cards --dest .../lib/plotpoints/model-cards.json

--exclude FILE: one "<seed_id>::<model>  <reason>" per line (# comments). Each
listed session is dropped before the pair design. pair-index.json records it
with its reason; manifest.excluded keeps only the seed and a reason code. An
unknown key or a missing reason fails.

PLOTPOINTS_PAIR_ID_SECRET: the HMAC key for pair ids and side coins. Read from
the environment by this script and nothing else; there is no default and no
flag, it is never printed and never written to any file, and it must be at
least 32 characters (openssl rand -hex 32). Keep it in a password manager and
reuse it for every export of a pool: a different key changes every pair id,
and ids freeze into vote rows once voting opens.

Blind pairs (the shared format the site implements against):
  manifest.json     Served. {"round", "label", "export_id", "export_hash",
                    "message_cap", "blind": true, "pairs", "seeds",
                    "excluded"}. pairs are [{"id": "p_<12 hex>", "seed_id"}],
                    sorted by id, with no model field. id = "p_" + the first
                    12 hex digits of HMAC-SHA256(key,
                    "<export_id>|<seed_id>|<model_lo>|<model_hi>"), the two
                    model ids sorted, so an id is stable for a given
                    sessions.json and key whatever --matchings is, and nobody
                    without the key can recompute one from the roster.
                    excluded is [{"seed_id", "reason": <EXCLUSION_CODES key>}].
                    No design, rng seed, source commit or source file: with
                    the public code and data those rebuild the pair list.
  pair-index.json   Server-only, never served or imported client-side:
                    {"export_id", "source_commit", "source_files", "design",
                    "excluded", "pairs": {"<id>": {"seed_id", "model_a",
                    "model_b"}}}. model_a is the session shown first (as A).
                    Which of the two that is is a keyed coin, the low bit of
                    HMAC-SHA256(key, "sides|<id>")[0] (pair_sides): 1 puts
                    the alphabetically later model first. excluded carries
                    the full {"key", "seed_id", "model", "code", "reason"}.
  sessions.json     Unchanged, keyed "<seed_id>::<model>", server-only.
"""
import argparse
import hashlib
import hmac
import json
import os
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from publication_guards import (  # noqa: E402
    TEXT_FIELDS, PublicationGuardError, _carries_text, _guard_path,
    _guard_record, _read_public_json)
from transcript_hash import transcript_hash  # noqa: E402
import generate_profile_cards_v2 as cards_v2  # noqa: E402
from make_j_barchart import NAMES, VENDOR, FINETUNES, reduced  # noqa: E402

RESULTS = PROJECT_ROOT / "results"
LEADERBOARD = RESULTS / "round4_willingness_leaderboard.json"
OVERVIEW_NAME = "round4_overview.json"      # analyze_round4_overview.py output
CONTINUITY_NAME = "round4_continuity.json"  # analyze_round4_continuity.py output
SEEDS_A = PROJECT_ROOT / "hf_dataset" / "_source" / "adversarial_seeds_r4_track_a.json"
R4_GLOB = "r4_full_*.json"
CARD_INPUTS = ("model_card_verdicts.json", "per_turn_failures_v2.jsonl",
               "behavioral_metrics.json", "model_profiles_v2.json",
               "community_arena_bayesian.json",
               "flaw_hunter_session_summary_v2.json",
               "production_defects.json", "model_coverage.json")

ROUND = 4
LABEL = "Round 04 · Track A ladders"
SEED_ID_RE = re.compile(r"^r4_a_(intimacy|gore)_(\d\d)$")
# The site's track-name rule (sessions.ts), with the round fixed.
DEST_FOLDER_RE = re.compile(r"^round-4-[a-z][a-z0-9_-]{0,32}$")
# Per message, in UTF-16 code units, which is what the site's JS .length
# counts. gemma_4_31b x r4_a_intimacy_05 has a 65,536-character reply.
MESSAGE_CAP = 12_000
DEFAULT_MATCHINGS = 4
DEFAULT_RNG_SEED = 4
DESIGN_METHOD = (
    "Per seed, the models with a session sit on matchings_per_seed / 2 "
    "random Hamiltonian cycles that share no pair (each cycle is two perfect "
    "matchings when the count is even), so every model meets exactly "
    "matchings_per_seed opponents per seed and each seed's pair graph is "
    "connected. The random stream is seeded per seed from "
    "'<rng_seed>:<seed_id>', so a larger even matchings_per_seed keeps every "
    "existing pair and only appends.")
# Only sessions, manifest and pair-index: the board and the cards say "B-hard" in their
# definitions on purpose (gaps 4) and are checked by key allowlist instead.
FORBIDDEN_BYTES = (b"r4_b_", b"B-hard", b"B-policy", b"r4_trackb")

PAIR_ID_SECRET_ENV = "PLOTPOINTS_PAIR_ID_SECRET"
# The roster, the seed ids and the export_id are all public, so a guessed key
# can be tested offline against any served id: a short one would fall.
PAIR_ID_SECRET_MIN = 32

# The served manifest. Nothing here names a model or says how the pairs were
# drawn: design, rng seed, method, source commit and source files live in
# pair-index.json (with the public code and data they rebuild the pair list).
MANIFEST_KEYS = {"round", "label", "export_id", "export_hash", "message_cap",
                 "blind", "pairs", "seeds", "excluded"}
MANIFEST_WITHHELD_KEYS = {"design", "kind", "matchings_per_seed", "rng_seed",
                          "method", "source_commit", "source_files", "key",
                          "model", "code"}
DESIGN_KEYS = {"kind", "matchings_per_seed", "rng_seed", "method"}
# Blind pool: the browser sees an opaque id and the seed, nothing else.
PAIR_KEYS = {"id", "seed_id"}
PAIR_ID_RE = re.compile(r"^p_[0-9a-f]{12}$")
PAIR_INDEX_KEYS = {"export_id", "source_commit", "source_files", "design",
                   "excluded", "pairs"}
PAIR_INDEX_ENTRY_KEYS = {"seed_id", "model_a", "model_b"}
SEED_KEYS = {"failure_target", "setting_summary", "character_name", "user_name",
             "label", "subtrack", "content_flags", "explicitness", "ask_turns",
             "ask_message_indexes"}
# Served exclusions: the seed and a code, never the model or the reviewer's
# words. pair-index.json keeps the full entry.
EXCLUDED_KEYS = {"seed_id", "reason"}
INDEX_EXCLUDED_KEYS = {"key", "seed_id", "model", "code", "reason"}
NOT_SCORED_REASON = ("newest run has no rung labels yet; the J analyzer "
                     "leaves it out too")
EXCLUSION_CODES = {
    "not_scored": "the newest run has no rung labels; the J board leaves it out",
    "content_review": "dropped after a person read it (--exclude)",
}
SESSION_KEYS = {"seed_id", "test_model", "character_name", "user_name",
                "num_turns", "transcript_hash", "export_hash", "dialogue"}
DIALOGUE_KEYS = {"role", "content"}
DIALOGUE_OPTIONAL_KEYS = {"cut_from_chars"}

BOARD_KEYS = {"schema_version", "round", "export_id", "source_commit", "source",
              "n_sessions", "note", "j_definition", "ranking_rule",
              "quadrant_medians", "j_ties", "notes", "rows"}
BOARD_ROW_KEYS = {"model", "name", "vendor", "is_finetune", "rank", "ranked",
                  "unranked_reason", "J", "quadrant", "tied_with", "held_first",
                  "held_under_pressure", "over_refusal_hard_rungs",
                  "over_refusal_intimacy", "over_refusal_gore",
                  "over_refusal_rate", "policy_compliance_rate", "overshoot_rate",
                  "empty", "n_sessions_a", "n_sessions_b", "usable_exchanges_a",
                  "hard_refusals_a", "reduced_seed_set", "elo", "composite",
                  "human", "old_judge_band", "r3_nsfw_rank"}
WILLINGNESS_KEYS = {"J", "rank", "ranked", "of", "unranked_reason", "tied_with",
                    "usable_exchanges_a", "held_first", "over_refusal_hard_rungs",
                    "over_refusal_intimacy", "over_refusal_gore",
                    "held_under_pressure", "policy_compliance_rate",
                    "overshoot_rate", "empty"}
CARDS_KEYS = {"schema_version", "reviewed_on", "scope", "sources", "inputs",
              "source_commit", "export_id", "willingness_source", "judge_table",
              "across_rounds_table", "cards"}
CARD_KEYS = {"id", "name", "vendor", "is_finetune", "verdict", "coverage",
             "standing_modes", "trap_pooled", "trap_modes", "willingness",
             "behavioral", "craft", "production_defects", "subjective",
             "community_r1", "strength", "weakness", "elo", "composite", "judge",
             "across_rounds"}
CRAFT_KEYS = {"axis", "cells", "filled", "sessions", "top_flaws"}
SUBJECTIVE_KEYS = {"judge", "axis", "cells", "filled", "axes"}
DEFECT_KEYS = {"turns", "leak_rate", "leak_turns", "selfplay_rate",
               "selfplay_turns", "loop_turns", "loop_rate", "loop_worst_turn",
               "token_overhead_x"}
# The judge table (Levi's exception to "bands only", for the index): Round
# 03's columns, one decimal. Card key -> round4_overview.json judge_means key.
JUDGE_COLUMNS = (("overall", "overall"),
                 ("agency", "S.5_agency_respect_session"),
                 ("consistency", "S.1_consistency_over_time"),
                 ("momentum", "S.3_narrative_momentum"))
JUDGE_KEYS = {"tier", "overall", "agency", "consistency", "momentum",
              "n_sessions", "n_seeds", "note"}
JUDGE_TABLE_KEYS = {"judge", "scale", "bands", "not_comparable_with", "note"}
JUDGE_BAND_KEYS = {"tier", "lower", "upper", "label"}
JUDGE_SOURCE = "subagent-sonnet-5"           # the judge name in judge_means
JUDGE_LABEL = "claude-sonnet-5 (session judge v2)"
JUDGE_NOT_COMPARABLE = "Round 03 judge (Sonnet 4)"
# The frozen letters (analyze_round4_overview.TIERS); an overview with any
# other ranges is refused rather than published under these names.
JUDGE_TIERS = (("A", 3.8, None), ("B", 3.2, 3.8), ("C", 2.6, 3.2),
               ("D", 2.0, 2.6), ("E", None, 2.0))

# Continuity (analyze_round4_continuity.py). The old judge leaves as a band
# only: mean and half width, two decimals. Round 3's position leaves as
# published, with its tie range.
OLD_JUDGE_ID = "anthropic/claude-sonnet-4"
OLD_JUDGE_BAND_KEYS = {"mean", "half_width", "n_sessions"}
R3_RANK_KEYS = {"rank", "tie", "of"}
ACROSS_KEYS = {"returning", "rounds", "old_judge_band", "r2_human", "r3_nsfw",
               "transcripts"}
ACROSS_R2_KEYS = {"elo", "ci95", "n_votes", "rank", "of", "voted_transcripts"}
ACROSS_R3_KEYS = {"rank", "tie", "of", "craft", "n", "refusal_pct"}
ACROSS_TABLE_KEYS = {"source", "old_judge", "band_rule", "core_seeds",
                     "r3_refusal", "note"}
ACROSS_TRANSCRIPTS = {"same", "regenerated", "mixed", "new_in_round4"}
ACROSS_ROUNDS = {"round 2", "round 3"}
# Never on a board row or a card, whatever the continuity file carries: a
# rank on the old judge, a translation between judges, a composite, or a
# round-4 refusal figure set beside round 3's.
ACROSS_BANNED = {"old_judge_rank", "rank_old_judge", "position", "old_scale",
                 "v2_on_old_scale", "translated", "mapped_v1", "composite",
                 "c_star", "refusal_r4", "r4_refusal_pct", "refusal_delta",
                 "low", "high"}
BOARD_NOTES_CONTINUITY = {
    "old_judge_band": (
        "Old judge: Sonnet 4, the Round 02 and 03 craft judge, re-run on these "
        "Round 04 transcripts. Mean over the 12 core seeds (09-20), plus or "
        "minus half its 95% seed-bootstrap interval. A band, not a rank: most "
        "neighbouring bands overlap. Not comparable with the Round 04 judge's "
        "numbers."),
    "r3_nsfw_rank": (
        "Position in the published Round 03 NSFW table (Sonnet 4 craft, 40 "
        "models). tie gives the positions that share the same published score. "
        "A different track and judge setup from Round 04."),
}

# Display names for the 13 models that have a card but no round-4 row, so
# make_j_barchart has none. Names from the site's data.ts, in NAMES' style.
CARD_ONLY = {
    "claude_sonnet_4_5": ("Sonnet 4.5", "anthropic"),
    "deepseek_r1_0528": ("DeepSeek R1 0528", "deepseek"),
    "deepseek_v3_2": ("DeepSeek V3.2", "deepseek"),
    "gemini_2_5_flash": ("Gemini 2.5 Flash", "google"),
    "gemini_3_1_flash_lite": ("Gemini 3.1 Flash Lite", "google"),
    "gemini_3_1_pro": ("Gemini 3.1 Pro", "google"),
    "gemma_4_26b": ("Gemma 4 26B", "google"),
    "glm_4_7": ("GLM 4.7", "zhipu"),
    "grok_4_1": ("Grok 4.1", "xai"),
    "kimi_k2_5": ("Kimi K2.5", "moonshot"),
    "llama_4_maverick": ("Llama 4 Maverick", "meta"),
    "mistral_small_creative": ("Mistral Small Creative", "mistral"),
    "qwen3_5_flash": ("Qwen3.5 Flash", "qwen"),
}

EM_DASH = "\u2014"
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]")


class ExportError(RuntimeError):
    """An export check failed; nothing was written."""


class PairIdSecretError(ExportError):
    """A blind pool was asked for without a usable PLOTPOINTS_PAIR_ID_SECRET."""


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

def display(model):
    """(name, vendor, is_finetune) for a model id; unknown ids fail."""
    if model in NAMES:
        if model not in VENDOR:
            raise ExportError("no vendor for %s in make_j_barchart.VENDOR" % model)
        return NAMES[model], VENDOR[model], model in FINETUNES
    if model in CARD_ONLY:
        name, vendor = CARD_ONLY[model]
        return name, vendor, False
    raise ExportError("no display name for %s: add it to make_j_barchart.NAMES "
                      "or CARD_ONLY" % model)


def canonical_hash(obj):
    blob = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_date(name):
    """YYYYMMDD from an r4_full_YYYYMMDD_HHMMSS.json name."""
    mo = re.search(r"_(\d{8})_\d{6}\.json$", name)
    if not mo:
        raise ExportError("cannot date %s" % name)
    return mo.group(1)


# --------------------------------------------------------------------------
# Git provenance
# --------------------------------------------------------------------------

def _git(*args):
    return subprocess.run(["git", "-C", str(PROJECT_ROOT), *args],
                          capture_output=True, text=True, check=True).stdout


def source_commit():
    return _git("rev-parse", "HEAD").strip()


def input_problems(paths):
    """Inputs that are untracked or differ from HEAD (empty list = clean)."""
    rel = [str(Path(p).resolve().relative_to(PROJECT_ROOT)) for p in paths]
    tracked = set(_git("ls-files", "--", *rel).split("\n")) - {""}
    out = ["%s is not tracked by git" % r for r in rel if r not in tracked]
    for line in _git("status", "--porcelain", "--", *rel).splitlines():
        out.append("%s differs from HEAD (%s)" % (line[3:], line[:2].strip()))
    return out


def refuse_benchmark_dest(path, name):
    """Site outputs never land in this (public) repo: Track A text included."""
    p = Path(path).resolve()
    if p == PROJECT_ROOT or PROJECT_ROOT in p.parents:
        raise ExportError("%s: refusing --dest %s inside the benchmark repo; "
                          "write into the site checkout" % (name, path))


def inside_git_checkout(path):
    p = Path(path).resolve()
    for d in [p] + list(p.parents):
        if (d / ".git").exists():
            return d
    return None


# --------------------------------------------------------------------------
# Sessions: read, dedupe, export
# --------------------------------------------------------------------------

def r4_paths(results_dir=RESULTS):
    """Every r4_full_*.json, newest first (the analyzer's order). Guarded by
    name here and again on read."""
    paths = sorted(Path(results_dir).glob(R4_GLOB), key=lambda p: p.name,
                   reverse=True)
    for p in paths:
        _guard_path(p)
    return paths


def dedupe_track_a(paths):
    """Track A sessions by (model, seed), exactly as
    analyze_round4_willingness.py:266-297 picks them.

    Files newest first. A row with an "error" key is skipped BEFORE its key is
    claimed; the (model, seed, track) key is claimed next; only then does a
    missing rung_labels drop the row, with no fallback to an older copy. Rows
    whose track is not "A" are passed over without being claimed; claims are
    per track, so that changes nothing for Track A and keeps every Track B
    row out of this function's hands.
    """
    seen, kept, origin = set(), {}, {}
    stats = Counter()
    unlabelled = []
    for path in paths:
        if not Path(path).exists():
            continue
        d = _read_public_json(path)
        for s in d["sessions"]:
            if s.get("track") != "A":
                stats["other_track_rows"] += 1
                continue
            stats["track_a_rows"] += 1
            if "error" in s:
                stats["error_rows"] += 1
                continue
            key = (s.get("test_model"), s.get("seed_id"), s.get("track"))
            if key in seen:
                stats["superseded"] += 1
                continue
            seen.add(key)
            if not s.get("rung_labels"):
                stats["unlabelled"] += 1
                unlabelled.append((s.get("test_model"), s.get("seed_id"),
                                   Path(path).name))
                continue
            kept[(s["test_model"], s["seed_id"])] = s
            origin[(s["test_model"], s["seed_id"])] = Path(path).name
    stats["claimed"] = len(seen)
    stats["labelled"] = len(kept)
    return kept, origin, unlabelled, stats


def load_seeds(path=SEEDS_A):
    seeds = _read_public_json(path)
    out = {}
    for s in seeds:
        sid = s["id"]
        if s.get("track") != "A" or not SEED_ID_RE.match(sid):
            raise ExportError("seed file holds a non-Track-A seed: %s" % sid)
        out[sid] = s
    return out


def seed_label(seed_id):
    mo = SEED_ID_RE.match(seed_id)
    return "%s %s" % (mo.group(1).capitalize(), mo.group(2))


def utf16_len(text):
    return len(text.encode("utf-16-le")) // 2


def cap_text(text, cap=MESSAGE_CAP):
    """(shown text, original length or None). Lengths in UTF-16 code units."""
    n = utf16_len(text)
    if n <= cap:
        return text, None
    cut = text[:cap]
    while utf16_len(cut) > cap:
        cut = cut[:-1]
    return cut, n


def ask_indexes(seed):
    """Message index of each scripted ask: turn t sits at 2t - 1."""
    return [2 * c["turn"] - 1 for c in seed["challenge_turns"]]


def export_session(s, seed, cap=MESSAGE_CAP):
    dialogue = []
    for m in s["dialogue"]:
        role = "assistant" if m.get("role") in ("assistant", "character") else "user"
        # None content occurs when reasoning models exhaust tokens before
        # output; "" is the honest signal and the site shows "(no reply)".
        content, cut_from = cap_text(m.get("content") or "", cap)
        e = {"role": role, "content": content}
        if cut_from is not None:
            e["cut_from_chars"] = cut_from
        dialogue.append(e)
    return {
        "seed_id": s["seed_id"],
        "test_model": s["test_model"],
        "character_name": s.get("character_name") or seed["character_name"],
        "user_name": s.get("user_name") or seed["user_name"],
        "num_turns": s.get("num_turns", len(s["dialogue"])),
        # The benchmark's own hash (model turns only) ties a vote to the
        # scores; export_hash covers exactly what the voter was shown.
        "transcript_hash": transcript_hash(s),
        "export_hash": canonical_hash(dialogue)[:16],
        "dialogue": dialogue,
    }


def check_asks(s, seed):
    """The scripted asks sit where ask_message_indexes says, verbatim."""
    want = ask_indexes(seed)
    got = [i for i, m in enumerate(s["dialogue"]) if m.get("is_challenge")]
    if got != want:
        return "ask indexes %s, expected %s" % (got, want)
    for i, c in zip(want, seed["challenge_turns"]):
        m = s["dialogue"][i]
        if m.get("role") != "user" or (m.get("content") or "") != c["user_input"]:
            return "message %d is not the seed's ask %d" % (i, c["rung"])
    return None


def load_exclude(path):
    """{"seed::model": reason} from an exclude file."""
    out = {}
    for ln, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split(None, 1)
        key = parts[0]
        reason = parts[1].strip().lstrip("#").strip() if len(parts) > 1 else ""
        if key.count("::") != 1 or not all(key.split("::")):
            raise ExportError("%s:%d: want <seed_id>::<model>, got %r" % (path, ln, key))
        if not reason:
            raise ExportError("%s:%d: %s has no reason; every exclusion needs one"
                              % (path, ln, key))
        if key in out:
            raise ExportError("%s:%d: %s listed twice" % (path, ln, key))
        out[key] = reason
    return out


def _seed_design(models, matchings, rng):
    """Pairs for one seed; see DESIGN_METHOD."""
    n = len(models)
    if n < 2:
        return []
    if matchings >= n - 1:
        return [(a, b) for i, a in enumerate(models) for b in models[i + 1:]]
    used, out = set(), []

    def take(edges):
        used.update(edges)
        out.extend(sorted(edges))

    for _ in range(matchings // 2):
        for _attempt in range(100000):
            order = models[:]
            rng.shuffle(order)
            cyc = {tuple(sorted((order[i], order[(i + 1) % n]))) for i in range(n)}
            if len(cyc) == n and not cyc & used:
                take(cyc)
                break
        else:
            raise ExportError("no pair-disjoint cycle found for %d models" % n)
    if matchings % 2:
        for _attempt in range(100000):
            order = models[:]
            rng.shuffle(order)
            match = {tuple(sorted(order[i:i + 2])) for i in range(0, n - 1, 2)}
            if n % 2:
                last = order[-1]
                partner = rng.choice(order[:-1])
                match.add(tuple(sorted((last, partner))))
            if not match & used:
                take(match)
                break
        else:
            raise ExportError("no pair-disjoint matching found for %d models" % n)
    return out


def design_pairs(models_by_seed, matchings=DEFAULT_MATCHINGS,
                 rng_seed=DEFAULT_RNG_SEED):
    """[(seed_id, model_a, model_b)] with model_a < model_b, sorted."""
    pairs = []
    for seed in sorted(models_by_seed):
        rng = random.Random("%s:%s" % (rng_seed, seed))
        for a, b in _seed_design(sorted(models_by_seed[seed]), matchings, rng):
            pairs.append((seed, a, b))
    return sorted(pairs)


def pair_id_secret(environ=None):
    """The HMAC key for pair ids and side coins, from the environment. This
    is the only place anything reads PLOTPOINTS_PAIR_ID_SECRET. Unset, blank
    or short refuses: there is no default, because a known key (and this repo
    is public) lets anyone recompute every id from the roster."""
    env = os.environ if environ is None else environ
    raw = env.get(PAIR_ID_SECRET_ENV) or ""
    if not raw.strip():
        raise PairIdSecretError(
            "refusing to build a blind pool: %s is unset. Pair ids and side "
            "coins are HMAC-SHA256 under that key and there is no default. "
            "Use the key this pool was exported with (a new one, from "
            "`openssl rand -hex 32`, only before launch); keep it in the "
            "environment, never in a file or on the command line"
            % PAIR_ID_SECRET_ENV)
    return _check_secret(raw.encode("utf-8"))


def _check_secret(secret):
    """The key itself, or a refusal. Never echoes it."""
    if not isinstance(secret, bytes) or len(secret) < PAIR_ID_SECRET_MIN:
        raise PairIdSecretError(
            "%s must be at least %d characters: the roster and seed ids are "
            "public, so a short key can be guessed and every pair id decoded"
            % (PAIR_ID_SECRET_ENV, PAIR_ID_SECRET_MIN))
    return secret


def _mac(secret, text):
    return hmac.new(_check_secret(secret), text.encode("utf-8"), hashlib.sha256)


def _pair_fields(export_id, seed_id, model_x, model_y):
    lo, hi = sorted((model_x, model_y))
    parts = (export_id, seed_id, lo, hi)
    if any("|" in p for p in parts):
        raise ExportError("a pair id field holds '|': %r" % (parts,))
    return "|".join(parts)


def pair_id(secret, export_id, seed_id, model_x, model_y):
    """The opaque, stable pair id: HMAC-SHA256 under the pool's key, so it
    cannot be recomputed from the public roster. The model order given does
    not matter."""
    return "p_" + _mac(secret, _pair_fields(export_id, seed_id, model_x,
                                            model_y)).hexdigest()[:12]


def _unkeyed_pair_id(export_id, seed_id, model_x, model_y):
    """The old bare-sha256 id, which anyone could recompute. Only here so
    the check can name an export that still carries one."""
    blob = _pair_fields(export_id, seed_id, model_x, model_y).encode("utf-8")
    return "p_" + hashlib.sha256(blob).hexdigest()[:12]


def pair_sides(secret, pid, model_x, model_y):
    """(first, second) for a pair: first is shown as A. A keyed coin from
    the id, so it is fixed per pair, carries no alphabetical tell, and
    cannot be recomputed without the key."""
    lo, hi = sorted((model_x, model_y))
    coin = _mac(secret, "sides|" + pid).digest()[0] & 1
    return (hi, lo) if coin else (lo, hi)


def blind_pairs(secret, export_id, pairs):
    """(manifest pairs, pair-index entries) for [(seed_id, model_a, model_b)].
    Both are in id order: the design's own order (seed, then the two model
    ids alphabetically) would show through a list position."""
    index = {}
    for seed_id, a, b in pairs:
        pid = pair_id(secret, export_id, seed_id, a, b)
        if pid in index:
            raise ExportError("pair id collision: %s" % pid)
        first, second = pair_sides(secret, pid, a, b)
        index[pid] = {"seed_id": seed_id, "model_a": first, "model_b": second}
    index = {pid: index[pid] for pid in sorted(index)}
    listed = [{"id": pid, "seed_id": e["seed_id"]} for pid, e in index.items()]
    return listed, index


def pair_graph_connected(pairs):
    adj = defaultdict(set)
    for _, a, b in pairs:
        adj[a].add(b)
        adj[b].add(a)
    if not adj:
        return True
    start = next(iter(adj))
    seen, stack = {start}, [start]
    while stack:
        for y in adj[stack.pop()]:
            if y not in seen:
                seen.add(y)
                stack.append(y)
    return len(seen) == len(adj)


def public_exclusions(exclusions):
    """pair-index exclusions as the manifest serves them: the seed and the
    code only, in an order that says nothing about the model."""
    return sorted(({"seed_id": e.get("seed_id"), "reason": e.get("code")}
                   for e in exclusions),
                  key=lambda e: (str(e["seed_id"]), str(e["reason"])))


def collect_sessions(paths, seeds, roster, *, exclude=None, lb_counts=None,
                     cap=MESSAGE_CAP):
    """(sessions, exclusions, seeds_meta, used_files, report): everything
    but the pairs. Pure, and needs no key (the youth screen reads only
    this). exclusions are pair-index entries, full detail."""
    exclude = dict(exclude or {})
    kept, origin, unlabelled, stats = dedupe_track_a(paths)
    roster = set(roster)
    report = {"dedupe": dict(stats), "problems": []}

    candidates = {}
    for (model, seed_id), s in kept.items():
        if model not in roster:
            stats["outside_roster"] += 1
            continue
        if not SEED_ID_RE.match(seed_id or "") or seed_id not in seeds:
            raise ExportError("Track A session with a non-Track-A seed id: %r"
                              % seed_id)
        candidates["%s::%s" % (seed_id, model)] = s
    report["dedupe"] = dict(stats)

    # The analyzer's per-model n_sessions_a must be exactly what was kept, or
    # the dedupe here is not the one the J board was scored on.
    if lb_counts is not None:
        per_model = Counter(s["test_model"] for s in candidates.values())
        for m in roster:
            if per_model.get(m, 0) != lb_counts.get(m):
                report["problems"].append(
                    "%s: %d Track A sessions here, %s in the leaderboard"
                    % (m, per_model.get(m, 0), lb_counts.get(m)))

    unknown = sorted(set(exclude) - set(candidates))
    if unknown:
        raise ExportError("--exclude lists sessions that are not in the export: %s"
                          % ", ".join(unknown))
    excluded = [{"key": "%s::%s" % (seed_id, model), "seed_id": seed_id,
                 "model": model, "code": "not_scored",
                 "reason": NOT_SCORED_REASON}
                for model, seed_id, _ in unlabelled if model in roster]
    for key in sorted(exclude):
        seed_id, model = key.split("::")
        excluded.append({"key": key, "seed_id": seed_id, "model": model,
                         "code": "content_review", "reason": exclude[key]})
        del candidates[key]
    excluded.sort(key=lambda e: e["key"])

    sessions, ask_problems = {}, []
    for key in sorted(candidates):
        s = candidates[key]
        seed = seeds[s["seed_id"]]
        why = check_asks(s, seed)
        if why:
            ask_problems.append("%s: %s" % (key, why))
        sessions[key] = export_session(s, seed, cap)
    if ask_problems:
        raise ExportError("ask markers would be wrong:\n  " + "\n  ".join(ask_problems))

    used_files = sorted({origin[(s["test_model"], s["seed_id"])]
                         for s in sessions.values()}, reverse=True)
    seeds_meta = {}
    for sid in sorted({s["seed_id"] for s in sessions.values()}):
        seed = seeds[sid]
        seeds_meta[sid] = {
            "failure_target": seed.get("failure_target", ""),
            "setting_summary": seed.get("character_setting", ""),
            "character_name": seed.get("character_name", ""),
            "user_name": seed.get("user_name", ""),
            "label": seed_label(sid),
            "subtrack": seed["subtrack"],
            "content_flags": list(seed.get("content_flags") or []),
            "explicitness": seed.get("explicitness"),
            "ask_turns": [c["turn"] for c in seed["challenge_turns"]],
            "ask_message_indexes": ask_indexes(seed),
        }
    return sessions, excluded, seeds_meta, used_files, report


def build_sessions_export(paths, seeds, roster, *, secret, exclude=None,
                          matchings=DEFAULT_MATCHINGS, rng_seed=DEFAULT_RNG_SEED,
                          commit="unknown", lb_counts=None, cap=MESSAGE_CAP):
    """(manifest, pair_index, sessions, report). Pure: reads `paths`, writes
    nothing. manifest is browser-safe; pair_index and sessions are not.
    `secret` is the pool's pair-id key (pair_id_secret); no default."""
    _check_secret(secret)
    sessions, excluded, seeds_meta, used_files, report = collect_sessions(
        paths, seeds, roster, exclude=exclude, lb_counts=lb_counts, cap=cap)
    by_seed = defaultdict(list)
    for s in sessions.values():
        by_seed[s["seed_id"]].append(s["test_model"])
    pairs = design_pairs(by_seed, matchings, rng_seed)

    export_hash = canonical_hash(sessions)
    export_id = "r4a-%s-%s" % (file_date(used_files[0]), export_hash[:7])
    listed, index = blind_pairs(secret, export_id, pairs)
    manifest = {
        "round": ROUND,
        "label": LABEL,
        "export_id": export_id,
        "export_hash": export_hash,
        "message_cap": cap,
        "blind": True,
        "pairs": listed,
        "seeds": seeds_meta,
        "excluded": public_exclusions(excluded),
    }
    pair_index = {
        "export_id": export_id,
        "source_commit": commit,
        "source_files": used_files,
        "design": {"kind": "balanced_matchings", "matchings_per_seed": matchings,
                   "rng_seed": rng_seed, "method": DESIGN_METHOD},
        "excluded": excluded,
        "pairs": index,
    }
    return manifest, pair_index, sessions, report


# --------------------------------------------------------------------------
# Guards over outputs
# --------------------------------------------------------------------------

def _keys_exact(obj, want, where, problems, optional=()):
    got = set(obj)
    missing, extra = want - got, got - want - set(optional)
    if missing or extra:
        problems.append("%s: missing %s, unexpected %s"
                        % (where, sorted(missing), sorted(extra)))


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def _all_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_keys(v)


def _text_keys(obj, path="$"):
    """TEXT_FIELDS keys that carry text, anywhere in obj."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in TEXT_FIELDS and _carries_text(v):
                yield "%s.%s" % (path, k)
            yield from _text_keys(v, "%s.%s" % (path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _text_keys(v, "%s[%d]" % (path, i))


def copy_problems(obj, where):
    """No em dash and no emoji in strings the site will show as copy."""
    out = []
    for s in _strings(obj):
        if EM_DASH in s:
            out.append("%s: em dash in %r" % (where, s[:80]))
        if EMOJI_RE.search(s):
            out.append("%s: emoji in %r" % (where, s[:80]))
    return out


def forbidden_byte_hits(blob):
    return [b.decode() for b in FORBIDDEN_BYTES if b in blob]


def _secret_forms(secret):
    """The key as it would look in a JSON file: raw, JSON-escaped, hex."""
    text = secret.decode("utf-8", "replace")
    return {secret, json.dumps(text)[1:-1].encode("ascii"),
            secret.hex().encode("ascii")}


def _pair_index_problems(manifest, pair_index, roster, secret):
    """The blind format: manifest pairs name no model and sit in id order,
    the index resolves every manifest id and nothing else, and every id and
    side order is the one pair_id/pair_sides give under the pool's key.
    Returns (problems, {"verified": n, "unkeyed": n})."""
    problems = []
    counts = Counter()
    if manifest.get("blind") is not True:
        problems.append("manifest.blind is not true")
    _keys_exact(pair_index, PAIR_INDEX_KEYS, "pair-index", problems)
    export_id = manifest.get("export_id")
    if pair_index.get("export_id") != export_id:
        problems.append("pair-index export_id %r, manifest %r"
                        % (pair_index.get("export_id"), export_id))
    index = pair_index.get("pairs") or {}
    listed = [p.get("id") for p in manifest["pairs"]]
    if len(listed) != len(set(listed)):
        problems.append("duplicate pair ids")
    bad = sorted(str(i) for i in listed if not PAIR_ID_RE.match(str(i)))
    if bad:
        problems.append("%d pair ids are not p_<12 hex>: %s" % (len(bad), bad[:3]))
    elif listed != sorted(listed):
        problems.append("manifest pairs are not in id order: a list position "
                        "would show the design's seed-then-alphabet order")
    if set(listed) != set(index):
        problems.append("manifest and pair-index ids differ: %d only in the "
                        "manifest, %d only in the index"
                        % (len(set(listed) - set(index)), len(set(index) - set(listed))))
    for p in manifest["pairs"]:
        e = index.get(p.get("id"))
        if e is None:
            continue
        where = "pair-index %s" % p["id"]
        _keys_exact(e, PAIR_INDEX_ENTRY_KEYS, where, problems)
        if e.get("seed_id") != p.get("seed_id"):
            problems.append("%s: seed %r, manifest says %r"
                            % (where, e.get("seed_id"), p.get("seed_id")))
        a, b = e.get("model_a"), e.get("model_b")
        if not (isinstance(a, str) and isinstance(b, str) and a and b and a != b):
            problems.append("%s: models %r and %r" % (where, a, b))
            continue
        try:
            fields = (export_id or "", e.get("seed_id") or "", a, b)
            if pair_id(secret, *fields) != p["id"]:
                if _unkeyed_pair_id(*fields) == p["id"]:
                    counts["unkeyed"] += 1
                else:
                    problems.append("%s: id does not hash from its fields under "
                                    "this key" % where)
            elif pair_sides(secret, p["id"], a, b) != (a, b):
                problems.append("%s: sides are not in pair_sides order" % where)
            else:
                counts["verified"] += 1
        except ExportError as err:
            problems.append("%s: %s" % (where, err))
    if counts["unkeyed"]:
        problems.append("%d pair ids are the unkeyed sha256: anyone with the "
                        "roster can decode them" % counts["unkeyed"])
    # No model id, and nothing about how the pairs were drawn, anywhere a
    # browser reads it: excluded[] included.
    shown = set(_strings(manifest))
    leaked = sorted(shown & (set(roster) | {"model_a", "model_b", "test_model"}))
    if leaked:
        problems.append("manifest names models or model keys: %s" % leaked[:5])
    withheld = sorted(set(_all_keys(manifest)) & MANIFEST_WITHHELD_KEYS)
    if withheld:
        problems.append("manifest carries design, provenance or exclusion "
                        "detail (pair-index.json only): %s" % withheld)
    return problems, dict(counts)


def _exclusion_problems(manifest, pair_index, sessions):
    """Served exclusions are seed + code; the index keeps the rest, and the
    two agree."""
    problems = []
    for e in manifest["excluded"]:
        _keys_exact(e, EXCLUDED_KEYS, "manifest excluded %s" % e.get("seed_id"),
                    problems)
        if e.get("reason") not in EXCLUSION_CODES:
            problems.append("manifest excluded %s: reason %r is not a reason code"
                            % (e.get("seed_id"), e.get("reason")))
    full = pair_index.get("excluded")
    if not isinstance(full, list):
        problems.append("pair-index.excluded is not a list")
        return problems
    for e in full:
        where = "pair-index excluded %s" % e.get("key")
        _keys_exact(e, INDEX_EXCLUDED_KEYS, where, problems)
        if e.get("key") != "%s::%s" % (e.get("seed_id"), e.get("model")):
            problems.append("%s: key does not match seed_id::model" % where)
        if e.get("code") not in EXCLUSION_CODES:
            problems.append("%s: code %r" % (where, e.get("code")))
        if not e.get("reason"):
            problems.append("%s: no reason" % where)
        if e.get("key") in sessions:
            problems.append("%s: the session is still in sessions.json" % where)
    if manifest["excluded"] != public_exclusions(full):
        problems.append("manifest.excluded is not pair-index.excluded reduced "
                        "to seed and code")
    return problems


def check_sessions_export(manifest, pair_index, sessions, roster, matchings, *,
                          secret):
    """Every guard over the sessions outputs, the pair ids checked under
    `secret`. Returns (problems, facts)."""
    _check_secret(secret)
    problems = []
    _keys_exact(manifest, MANIFEST_KEYS, "manifest", problems)
    for p in manifest["pairs"]:
        _keys_exact(p, PAIR_KEYS, "pair %s" % p.get("id"), problems)
    more, id_counts = _pair_index_problems(manifest, pair_index, roster, secret)
    problems += more
    design = pair_index.get("design")
    if not isinstance(design, dict):
        problems.append("pair-index.design is not an object")
    else:
        _keys_exact(design, DESIGN_KEYS, "pair-index.design", problems)
        if design.get("matchings_per_seed") != matchings:
            problems.append("pair-index.design.matchings_per_seed %r, checked "
                            "against %d" % (design.get("matchings_per_seed"),
                                            matchings))
    files = pair_index.get("source_files")
    if not (isinstance(files, list) and files
            and all(isinstance(f, str) and re.match(r"^r4_full_\d{8}_\d{6}\.json$", f)
                    for f in files)):
        problems.append("pair-index.source_files is not a list of r4_full files")
    if not isinstance(pair_index.get("source_commit"), str):
        problems.append("pair-index.source_commit is not a string")
    problems += _exclusion_problems(manifest, pair_index, sessions)
    # The design checks below read the resolved pairs (broken entries were
    # reported above and are left out here).
    index = pair_index.get("pairs") or {}
    resolved = [dict(index[p["id"]], id=p["id"]) for p in manifest["pairs"]
                if isinstance(index.get(p.get("id")), dict)
                and PAIR_INDEX_ENTRY_KEYS <= set(index[p["id"]])]
    for sid, seed in manifest["seeds"].items():
        _keys_exact(seed, SEED_KEYS, "seed %s" % sid, problems)
    n_msgs = n_empty = 0
    cut = []
    cap = manifest["message_cap"]
    for key, s in sessions.items():
        _keys_exact(s, SESSION_KEYS, "session %s" % key, problems)
        if key != "%s::%s" % (s["seed_id"], s["test_model"]):
            problems.append("session key %s does not match its body" % key)
        for i, m in enumerate(s["dialogue"]):
            _keys_exact(m, DIALOGUE_KEYS, "%s[%d]" % (key, i), problems,
                        optional=DIALOGUE_OPTIONAL_KEYS)
            if m["role"] not in ("user", "assistant"):
                problems.append("%s[%d]: role %r" % (key, i, m["role"]))
            if utf16_len(m["content"]) > cap:
                problems.append("%s[%d]: over the %d cap" % (key, i, cap))
            if "cut_from_chars" in m:
                cut.append("%s[%d] %d->%d" % (key, i, m["cut_from_chars"],
                                             utf16_len(m["content"])))
            n_msgs += 1
            n_empty += (m["role"] == "assistant" and m["content"] == "")

    ids = [sid for sid in manifest["seeds"]]
    ids += [s["seed_id"] for s in sessions.values()]
    ids += [p["seed_id"] for p in manifest["pairs"]]
    ids += [p["seed_id"] for p in resolved]
    ids += [e.get("seed_id") for e in manifest["excluded"]]
    ids += [e.get("seed_id") for e in pair_index.get("excluded") or []
            if isinstance(e, dict)]
    bad_ids = sorted({str(i) for i in ids if not SEED_ID_RE.match(str(i))})
    if bad_ids:
        problems.append("non-Track-A seed ids: %s" % bad_ids)
    models = {s["test_model"] for s in sessions.values()}
    if models - set(roster):
        problems.append("models outside the roster: %s" % sorted(models - set(roster)))

    slots = Counter()
    per_seed = defaultdict(Counter)
    seen_pairs = set()
    for p in resolved:
        for side in ("model_a", "model_b"):
            if "%s::%s" % (p["seed_id"], p[side]) not in sessions:
                problems.append("pair %s: no session for %s" % (p["id"], p[side]))
            slots[p[side]] += 1
            per_seed[p["seed_id"]][p[side]] += 1
        unordered = (p["seed_id"], *sorted((p["model_a"], p["model_b"])))
        if unordered in seen_pairs:
            problems.append("pair %s: the same two sessions are paired twice" % p["id"])
        seen_pairs.add(unordered)
    short = []
    for s in sessions.values():
        n_seed = sum(1 for t in sessions.values() if t["seed_id"] == s["seed_id"])
        need = min(matchings, n_seed - 1)
        if per_seed[s["seed_id"]][s["test_model"]] < need:
            short.append("%s::%s" % (s["seed_id"], s["test_model"]))
    if short:
        problems.append("%d sessions in fewer than %d pairs" % (len(short), matchings))
    triples = [(p["seed_id"], p["model_a"], p["model_b"]) for p in resolved]
    connected = pair_graph_connected(triples)
    if not connected:
        problems.append("the model graph is not connected")

    for obj, name in ((manifest, "manifest.json"), (pair_index, "pair-index.json"),
                      (sessions, "sessions.json")):
        try:
            _guard_record(obj, name)
        except PublicationGuardError as e:
            problems.append(str(e))
    manifest_bytes = manifest_json(manifest)
    index_bytes = pair_index_json(pair_index)
    sessions_bytes = sessions_json(sessions)
    for name, blob in (("manifest.json", manifest_bytes),
                       ("pair-index.json", index_bytes),
                       ("sessions.json", sessions_bytes)):
        hits = forbidden_byte_hits(blob)
        if hits:
            problems.append("%s carries forbidden bytes: %s" % (name, hits))
        # The key goes nowhere but this process's memory.
        if any(form in blob for form in _secret_forms(secret)):
            problems.append("%s carries the pair-id key" % name)
    problems += copy_problems({"label": manifest.get("label"),
                               "excluded": manifest["excluded"]}, "manifest")
    problems += copy_problems({sid: {k: seed[k] for k in ("label", "failure_target",
                                                          "character_name", "user_name")}
                               for sid, seed in manifest["seeds"].items()}, "seeds")
    facts = {
        "sessions": len(sessions), "models": len(models),
        "seeds": len(manifest["seeds"]), "pairs": len(manifest["pairs"]),
        "pair_slots_min": min(slots.values()) if slots else 0,
        "pair_slots_max": max(slots.values()) if slots else 0,
        "per_seed_min": min((c for cs in per_seed.values() for c in cs.values()),
                            default=0),
        "per_seed_max": max((c for cs in per_seed.values() for c in cs.values()),
                            default=0),
        "connected": connected, "messages": n_msgs, "empty_replies": n_empty,
        "cut_messages": len(cut),
        "cut_sessions": len({c.split("[")[0] for c in cut}),
        "cut_by_model": Counter(c.split("::")[1].split("[")[0]
                                for c in cut).most_common(),
        "excluded": len(manifest["excluded"]),
        "excluded_by_code": dict(Counter(e.get("reason")
                                         for e in manifest["excluded"])),
        "blind": manifest.get("blind") is True,
        "ids_keyed_and_verified": id_counts.get("verified", 0),
        "ids_unkeyed": id_counts.get("unkeyed", 0),
        "pairs_in_id_order": [p.get("id") for p in manifest["pairs"]]
                             == sorted(str(p.get("id")) for p in manifest["pairs"]),
        # How often A is the alphabetically first model: about half, or the
        # side order is a tell.
        "a_side_alphabetical": sum(p["model_a"] < p["model_b"] for p in resolved),
        "manifest_bytes": len(manifest_bytes),
        "pair_index_bytes": len(index_bytes),
        "sessions_bytes": len(sessions_bytes),
        "track_b_ids": sum(blob.count(b"r4_b_") for blob in (
            manifest_bytes, index_bytes, sessions_bytes)),
    }
    return problems, facts


def manifest_json(manifest):
    return (json.dumps(manifest, indent=2) + "\n").encode("ascii")


def pair_index_json(pair_index):
    return (json.dumps(pair_index, indent=2) + "\n").encode("ascii")


def sessions_json(sessions):
    return (json.dumps(sessions) + "\n").encode("ascii")


# --------------------------------------------------------------------------
# Youth screen (gaps 2)
# --------------------------------------------------------------------------

_AGE_WORDS = ("one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
              "thirteen|fourteen|fifteen|sixteen|seventeen")
_TENS = ("twenty", "thirty", "forty", "fourty", "fifty", "sixty", "seventy",
         "eighty", "ninety")
# "thirty-four years old" is an adult: a word age must not be the tail of a
# compound number ("thirty-four", "thirty four", "a hundred and four").
_NOT_COMPOUND = ("".join(r"(?<!%s[- ])" % t for t in _TENS)
                 + r"(?<!hundred )(?<!hundred and )")
_APOS = "['’]"
YOUTH_PATTERNS = (
    ("age", re.compile(r"\b(?:[1-9]|1[0-7])[- ]?(?:years?[- ]old|yrs?[- ]old|y/o)\b", re.I)),
    ("age", re.compile(_NOT_COMPOUND + r"\b(?:%s)[- ]years?[- ]old\b" % _AGE_WORDS, re.I)),
    ("age", re.compile(r"\b(?:aged|age of|age) (?:[1-9]|1[0-7])\b|"
                       r"\b(?:aged|age of) (?:%s)\b" % _AGE_WORDS, re.I)),
    ("minor_term", re.compile(
        r"\b(?:teen(?:s|age|aged|ager|agers)?|adolescen(?:t|ts|ce)|pre-?teens?|"
        r"tweens?|under-?aged?|minors?|jailbait|loli(?:ta|con)?|shota(?:con)?|"
        r"school ?(?:girl|boy)s?|high[- ]?school(?:er|ers)?|"
        r"middle[- ]school(?:er|ers)?|junior high|grade school|elementary school|"
        r"(?:pre)?pubescent|puberty|freshman|sophomore|"
        r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
        r"eleventh|twelfth|[1-9](?:st|nd|rd|th)|1[0-2]th)[- ]grader?s?)\b", re.I)),
    ("child_term", re.compile(
        r"\b(?:child(?:ren|ish|like)?|kids?|kiddos?|little (?:girl|boy)s?|"
        r"young (?:girl|boy)s?|toddlers?|baby ?girl)\b", re.I)),
)

# bare_age: an age said as a bare number, 10 to 17, which the "years old"
# patterns miss: "Fifteen, maybe sixteen", "can't be more than sixteen",
# "a boy maybe sixteen", "Daniel Brandt. Seventeen." Counting ("Twelve.
# Eleven. Thirteen.") and quantities ("ten minutes, maybe fifteen") are the
# noise, so an estimate, range or one-word sentence only counts when an age
# cue ("young", "boy", "old enough", "mother", ...) is within
# AGE_CUE_WINDOW characters. A noun followed by a number ("a girl of
# fourteen") needs no cue, nor does an adult age hedged downwards ("Twenty
# years old, maybe less").
_NUM_10_17 = r"(?:ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|1[0-7])"
# The number ends its phrase: punctuation, the end, or an estimate's tail;
# never a noun ("ten minutes", "sixteen men").
_ENDS_PHRASE = (r"(?=\s*(?:[,.;:!?\"”)—–]|" + _APOS + r"(?!s)|$)|"
                r"\s+(?:or|maybe|perhaps|at\s+(?:most|best)|tops|if\s+that|"
                r"summers|winters|years\s+of\s+age)\b)")
_HEDGE = (r"(?:maybe|perhaps|about|around|barely|only|just|hardly|scarcely|"
          r"not\s+yet|under|younger\s+than|at\s+most|"
          r"(?:no|not|can" + _APOS + r"?t\s+be|cannot\s+be|couldn" + _APOS
          + r"?t\s+be)\s+(?:more|older)\s+than)")
BARE_AGE_RE = re.compile(
    r"\b" + _HEDGE + r"\s+" + _NUM_10_17 + r"\b" + _ENDS_PHRASE + "|"
    r"\b" + _NUM_10_17 + r"\s*(?:,|or|to|-|–)\s*(?:maybe\s+|perhaps\s+|or\s+)?"
    + _NUM_10_17 + r"\b" + _ENDS_PHRASE + "|"
    r"(?:^|(?<=[.!?])[\"”’]?\s+|(?<=[\"“]))\s*" + _NUM_10_17
    + r"(?=[.!?,])", re.I)
AGE_CUE_RE = re.compile(
    r"\b(?:young(?:er|est|sters?)?|boys?|girls?|lads?|lass(?:es)?|kids?|"
    r"child(?:ren)?|teen\w*|sons?|daughters?|mother|father|parents|born|"
    r"birthdays?|old\s+enough|aged?)\b", re.I)
AGE_CUE_WINDOW = 150
AGE_APPOSITION_RE = re.compile(
    r"\b(?:boy|girl|lad|lass|kid|child|son|daughter)s?,?\s+"
    r"(?:of\s+|aged\s+|maybe\s+|perhaps\s+|about\s+|around\s+|barely\s+|"
    r"no\s+more\s+than\s+)?" + _NUM_10_17 + r"\b"
    r"(?![- ]?(?:minutes?|hours?|seconds?|days?|weeks?|months?|feet|foot|paces|"
    r"yards|miles|men|times|years\s+(?:ago|later|before|after|since)))", re.I)
HEDGED_ADULT_RE = re.compile(
    r"\b(?:eighteen|nineteen|twenty|1[89]|20)(?:[- ]years?[- ]old)?,?\s+"
    r"(?:maybe|perhaps|or)\s+(?:less|younger|under)\b", re.I)

# boy_girl_violence, the softest tier: a referring "the boy" / "a dead girl"
# within VIOLENCE_WINDOW characters of a violence word. Not a vocative
# ("Do it now, boy."), not an endearment ("good girl"), and not "little
# girl" or "young boy", which child_term already lists.
BOY_GIRL_RE = re.compile(
    r"\b(?:the|a|an|that|this|dead|wounded|dying|injured|poor)\s+(?:[a-z]+\s+)?"
    r"(?<!little )(?<!young )(?<!good )(?<!naughty )(?<!bad )(?<!my )"
    r"(?:boy|girl|lad|lass)(?:s|" + _APOS + r"s)?\b(?!friend)", re.I)
VIOLENCE_RE = re.compile(
    r"\b(?:kill(?:s|ed|ing)?|stab(?:s|bed|bing)?|slit|slash(?:es|ed|ing)?|"
    r"cut(?:s|ting)?|blood(?:y|ied)?|bleed(?:s|ing)?|bled|wound(?:s|ed)?|throat|"
    r"knife|blade|dagger|sword|bullet|shot|guts?|bones?|corpse|dead|die[sd]?|"
    r"dying|death|skull|flesh|spine|entrails|sever(?:ed)?|surgery|amputat\w*|"
    r"scream(?:s|ed|ing)?|torture[sd]?|remains)\b", re.I)
VIOLENCE_WINDOW = 150

# Seed check, per person: the character setting and the user setting each
# need a stated adult age. "Nadia is 30" counts.
ADULT_AGE_RE = re.compile(r"\b(?:1[89]|[2-9]\d)[- ]years?[- ]old\b|"
                          r"\b(?:is|aged|age)\s+(?:1[89]|[2-9]\d)\b|"
                          r"\b(?:twenties|thirties|forties|fifties|sixties)\b|"
                          r"\badults?\b", re.I)
NUMERIC_ADULT_AGE_RE = re.compile(r"\b(?:1[89]|[2-9]\d)[- ]years?[- ]old\b|"
                                  r"\b(?:is|aged|age)\s+(?:1[89]|[2-9]\d)\b|"
                                  r"\b(?:twenties|thirties|forties|fifties|sixties)\b",
                                  re.I)
TIER_ORDER = {"age": 0, "minor_term": 1, "bare_age": 2, "child_term": 3,
              "boy_girl_violence": 4, "seed_no_adult_age": 5,
              "seed_no_numeric_age": 6}
# Tiers that state or estimate an age, as against context words.
STATED_TIERS = ("age", "minor_term", "bare_age")
CONTEXT_CHARS = 200


def _context(text, start, end):
    width = CONTEXT_CHARS
    lo = max(0, start - (width - (end - start)) // 2)
    snippet = text[lo:lo + width]
    return " ".join(snippet.split())


def _term(mo):
    return " ".join(mo.group(0).lower().split()).strip(" \"\u201c\u201d\u2019")


def text_hits(text):
    """[(tier, match)] for one text, every tier."""
    out = []
    for tier, rx in YOUTH_PATTERNS:
        out += [(tier, mo) for mo in rx.finditer(text)]
    bare = [mo for mo in BARE_AGE_RE.finditer(text)
            if AGE_CUE_RE.search(text, max(0, mo.start() - AGE_CUE_WINDOW),
                                 mo.end() + AGE_CUE_WINDOW)]
    bare += list(AGE_APPOSITION_RE.finditer(text))
    bare += list(HEDGED_ADULT_RE.finditer(text))
    taken = []
    for mo in sorted(bare, key=lambda m: m.start()):
        if any(mo.start() < e and s < mo.end() for s, e in taken):
            continue
        taken.append(mo.span())
        out.append(("bare_age", mo))
    for mo in BOY_GIRL_RE.finditer(text):
        if VIOLENCE_RE.search(text, max(0, mo.start() - VIOLENCE_WINDOW),
                              mo.end() + VIOLENCE_WINDOW):
            out.append(("boy_girl_violence", mo))
    return out


def youth_screen(sessions, seeds_meta, seeds_raw=None):
    """Lexical hits for minor-coded terms. Many are figurative; each one is
    for a person to read, not for this script to decide."""
    hits = []
    for key in sorted(sessions):
        s = sessions[key]
        sub = seeds_meta[s["seed_id"]]["subtrack"]
        for i, m in enumerate(s["dialogue"]):
            text = m["content"]
            for tier, mo in text_hits(text):
                hits.append({"tier": tier, "term": _term(mo),
                             "key": key, "seed_id": s["seed_id"],
                             "model": s["test_model"], "subtrack": sub,
                             "message_index": i, "role": m["role"],
                             "context": _context(text, mo.start(), mo.end())})
    for sid, meta in sorted(seeds_meta.items()):
        raw = (seeds_raw or {}).get(sid)
        fields = {"setting_summary": meta["setting_summary"],
                  "character_name": meta["character_name"],
                  "user_name": meta["user_name"]}
        if raw is not None:
            fields["user_setting"] = raw.get("user_setting")
        for field, text in fields.items():
            text = text or ""
            for tier, mo in text_hits(text):
                hits.append({"tier": tier, "term": _term(mo),
                             "key": sid, "seed_id": sid, "model": "-",
                             "subtrack": meta["subtrack"],
                             "message_index": "seed." + field, "role": "-",
                             "context": _context(text, mo.start(), mo.end())})
        # Each person needs their own stated adult age: gore_01 gives the
        # character's ("in her forties") but not the user's.
        people = [("setting_summary", meta["setting_summary"])]
        if raw is not None:
            people.append(("user_setting", raw.get("user_setting")))
        for field, text in people:
            text = text or ""
            tier = ("seed_no_adult_age" if not ADULT_AGE_RE.search(text) else
                    "seed_no_numeric_age" if not NUMERIC_ADULT_AGE_RE.search(text)
                    else None)
            if tier:
                hits.append({"tier": tier, "term": "-", "key": sid,
                             "seed_id": sid, "model": "-",
                             "subtrack": meta["subtrack"],
                             "message_index": "seed." + field, "role": "-",
                             "context": " ".join(text.split())[:CONTEXT_CHARS]})
    hits.sort(key=lambda h: (h["subtrack"] != "intimacy", TIER_ORDER[h["tier"]],
                             h["seed_id"], h["model"],
                             h["message_index"] if isinstance(h["message_index"], int)
                             else -1))
    return hits


def youth_summary(hits):
    by_tier = Counter(h["tier"] for h in hits)
    sess = defaultdict(set)
    for h in hits:
        if h["model"] != "-":
            sess[(h["subtrack"], h["tier"])].add(h["key"])
            sess[(h["subtrack"], "stated" if h["tier"] in STATED_TIERS
                  else "context_only")].add(h["key"])
    for sub in {s for s, _ in sess}:
        sess[(sub, "context_only")] -= sess.get((sub, "stated"), set())
    seed_flags = lambda tier: sorted("%s %s" % (h["seed_id"], h["message_index"])
                                     for h in hits if h["tier"] == tier)
    return {
        "hits_by_tier": dict(sorted(by_tier.items(), key=lambda kv: TIER_ORDER[kv[0]])),
        "sessions_flagged": len({h["key"] for h in hits if h["model"] != "-"}),
        "sessions_by_subtrack_tier": {"%s/%s" % k: len(v) for k, v in sorted(sess.items())},
        "seeds_without_stated_adult_age": seed_flags("seed_no_adult_age"),
        "seeds_without_numeric_adult_age": seed_flags("seed_no_numeric_age"),
        "terms": Counter(h["term"] for h in hits if h["term"] != "-").most_common(),
    }


def write_review(hits, path):
    """Tab-separated, one hit per line. Refuses any path inside a git checkout:
    the list quotes explicit text and must never be committed or deployed."""
    repo = inside_git_checkout(Path(path).parent)
    if repo is not None:
        raise ExportError("refusing --review-out %s: it is inside the git checkout "
                          "%s; put the review list outside every repo" % (path, repo))
    cols = ("tier", "term", "key", "seed_id", "model", "subtrack",
            "message_index", "role", "context")
    lines = ["\t".join(cols)]
    for h in hits:
        lines.append("\t".join(str(h[c]).replace("\t", " ") for c in cols))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# Board
# --------------------------------------------------------------------------

def build_board(lb, commit="unknown", continuity=None):
    cont = continuity if continuity is not None else read_continuity(RESULTS)
    rows_in = lb["leaderboard"]
    ranked = sorted((r for r in rows_in if r.get("ranked")), key=lambda r: r["rank"])
    unranked = [r for r in rows_in if not r.get("ranked")]
    if [r["rank"] for r in ranked] != list(range(1, len(ranked) + 1)):
        raise ExportError("leaderboard ranks are not 1..%d" % len(ranked))
    if any(r.get("rank") is not None or not r.get("unranked_reason") for r in unranked):
        raise ExportError("an unranked leaderboard row has a rank or no reason")
    notes = {}
    for key, field in (("held_first", "held_line_rate_note"),
                       ("held_under_pressure", "held_under_pressure_note")):
        vals = {r.get(field) for r in rows_in}
        if len(vals) != 1:
            raise ExportError("%s differs between rows; the board keeps one copy"
                              % field)
        notes[key] = vals.pop()
    r4 = cards_v2.r4_rows(lb)
    rows = []
    for r in ranked + unranked:
        m = r["model"]
        name, vendor, fine = display(m)
        w = cards_v2.willingness_fields(r4[m])
        rows.append({
            "model": m, "name": name, "vendor": vendor, "is_finetune": fine,
            "rank": w["rank"], "ranked": w["ranked"],
            "unranked_reason": w["unranked_reason"],
            "J": w["J"], "quadrant": r["quadrant"], "tied_with": w["tied_with"],
            "held_first": w["held_first"],
            "held_under_pressure": w["held_under_pressure"],
            "over_refusal_hard_rungs": w["over_refusal_hard_rungs"],
            "over_refusal_intimacy": w["over_refusal_intimacy"],
            "over_refusal_gore": w["over_refusal_gore"],
            "over_refusal_rate": r["over_refusal_rate"],
            "policy_compliance_rate": w["policy_compliance_rate"],
            "overshoot_rate": w["overshoot_rate"],
            "empty": w["empty"],
            "n_sessions_a": r["n_sessions_a"], "n_sessions_b": r["n_sessions_b"],
            "usable_exchanges_a": r["usable_exchanges_a"],
            "hard_refusals_a": r["hard_refusals_a"],
            # make_j_barchart.reduced: fewer sessions than the full seed set
            # or fewer usable first asks than the full four (the chart's *).
            "reduced_seed_set": bool(reduced(r, rows_in)),
            # Reserved until the ELO/composite design lands; the site shows a
            # column only when some row has a value.
            "elo": None, "composite": None, "human": None,
            # Continuity (round4_continuity.json): a band and a published
            # position, secondary columns; null for a model without one.
            "old_judge_band": old_judge_band(cont, m),
            "r3_nsfw_rank": r3_nsfw_rank(cont, m),
        })
    notes.update(BOARD_NOTES_CONTINUITY)
    newest = max(lb["sources"], key=lambda n: file_date(n))
    board = {
        "schema_version": 1, "round": ROUND, "export_id": None,
        "source_commit": commit,
        "source": "results/round4_willingness_leaderboard.json",
        "n_sessions": lb["n_sessions"], "note": lb["note"],
        "j_definition": lb["j_definition"], "ranking_rule": lb["ranking_rule"],
        "quadrant_medians": dict(lb["quadrant_medians"]),
        "j_ties": [{"J": t["J"], "models": list(t["models"])} for t in lb["j_ties"]],
        "notes": notes, "rows": rows,
    }
    board["export_id"] = "r4j-%s-%s" % (file_date(newest), canonical_hash(
        {k: v for k, v in board.items() if k not in ("export_id", "source_commit")})[:7])
    return board


def check_board(board, continuity=None):
    problems = []
    _keys_exact(board, BOARD_KEYS, "board", problems)
    for r in board["rows"]:
        _keys_exact(r, BOARD_ROW_KEYS, "board row %s" % r.get("model"), problems)
        where = "board row %s" % r.get("model")
        problems += _band_problems(r.get("old_judge_band"), where + ".old_judge_band")
        problems += _r3_rank_problems(r.get("r3_nsfw_rank"), where + ".r3_nsfw_rank")
        if continuity is not None and (
                r.get("old_judge_band") != old_judge_band(continuity, r.get("model"))
                or r.get("r3_nsfw_rank") != r3_nsfw_rank(continuity, r.get("model"))):
            problems.append("%s: continuity fields differ from %s"
                            % (where, CONTINUITY_NAME))
    ranked = [r for r in board["rows"] if r["ranked"]]
    if [r["rank"] for r in ranked] != list(range(1, len(ranked) + 1)):
        problems.append("board ranks are not 1..%d" % len(ranked))
    if any(r["rank"] is not None or not r["unranked_reason"]
           for r in board["rows"] if not r["ranked"]):
        problems.append("an unranked board row has a rank or no reason")
    problems += ["board text field at %s" % p for p in _text_keys(board)]
    try:
        _guard_record(board, "round-4.json")
    except PublicationGuardError as e:
        problems.append(str(e))
    problems += copy_problems(board, "board")
    return problems


# --------------------------------------------------------------------------
# Continuity (round4_continuity.json)
# --------------------------------------------------------------------------

def read_continuity(results_dir=RESULTS):
    p = Path(results_dir) / CONTINUITY_NAME
    if not p.exists():
        raise ExportError("%s missing; run analyze_round4_continuity.py" % p.name)
    doc = _read_public_json(p)
    oj = doc.get("old_judge") or {}
    if oj.get("judge") != OLD_JUDGE_ID or not oj.get("models"):
        raise ExportError("%s: old_judge missing or not %s; rerun "
                          "analyze_round4_continuity.py" % (p.name, OLD_JUDGE_ID))
    if not doc.get("rows"):
        raise ExportError("%s: no returning-model rows" % p.name)
    for m, b in oj["models"].items():
        bad = set(b) & (ACROSS_BANNED - {"low", "high"})
        if bad:
            raise ExportError("%s: old_judge.%s carries %s" % (p.name, m, sorted(bad)))
    return doc


def _continuity_rows(cont):
    return {r["model"]: r for r in cont["rows"]}


def old_judge_band(cont, model):
    """{"mean", "half_width", "n_sessions"} to two decimals, or None."""
    b = cont["old_judge"]["models"].get(model)
    if b is None:
        return None
    return {"mean": round(float(b["mean"]), 2),
            "half_width": round(float(b["half_width"]), 2),
            "n_sessions": int(b["n_sessions"])}


def r3_nsfw_rank(cont, model):
    """Round 3's published position with its tie range, or None."""
    r3 = (_continuity_rows(cont).get(model) or {}).get("r3_nsfw")
    if not r3:
        return None
    return {"rank": int(r3["rank"]), "tie": r3.get("tie"), "of": int(r3["of"])}


def across_rounds(cont, model):
    """A card's across_rounds block. A new model gets returning false, no
    earlier-round fields, and still its old-judge band when it has one."""
    row = _continuity_rows(cont).get(model)
    h = (row or {}).get("r2_human")
    r3 = (row or {}).get("r3_nsfw")
    return {
        "returning": row is not None,
        "rounds": list(row["rounds"]) if row else [],
        "old_judge_band": old_judge_band(cont, model),
        "r2_human": None if not h else {
            "elo": int(round(h["elo"])),
            "ci95": [int(round(h["ci95"][0])), int(round(h["ci95"][1]))],
            "n_votes": int(h["n_votes"]), "rank": int(h["rank"]),
            "of": int(h["of"]), "voted_transcripts": h["voted_transcripts"]},
        "r3_nsfw": None if not r3 else {
            "rank": int(r3["rank"]), "tie": r3.get("tie"), "of": int(r3["of"]),
            "craft": round(float(r3["craft"]), 2), "n": int(r3["n"]),
            "refusal_pct": r3.get("refusal_pct")},
        "transcripts": (row["same_transcripts"]["flag"] if row
                        else "new_in_round4"),
    }


def build_across_table(cont):
    oj = cont["old_judge"]
    core = cont["core_seeds"]["seeds"]
    return {
        "source": "results/%s" % CONTINUITY_NAME,
        "old_judge": "claude-sonnet-4 (the Round 02 and 03 craft judge, prompt %s)"
                     % oj["prompt_hash"],
        "band_rule": ("mean over the %d core seeds, plus or minus half the 95%% "
                      "seed-bootstrap interval; a band, never a rank" % len(core)),
        "core_seeds": "%s to %s" % (core[0], core[-1]),
        "r3_refusal": ("Round 03's refusal % is Round 03's own instrument (a "
                       "judge flag per session) and is not comparable with J."),
        "note": ("Round 04 changed the instruments, not the models. The old judge "
                 "re-scored every Round 04 transcript so the Round 02 and 03 line "
                 "continues; its numbers are not on the Round 04 judge's scale and "
                 "nothing is translated between the two. Round 02 human ratings "
                 "are the final 1,943-vote arena."),
    }


def _is_2dp(v, lo, hi):
    return (not isinstance(v, bool) and isinstance(v, (int, float))
            and lo <= v <= hi and round(v, 2) == v)


def _band_problems(b, where):
    if b is None:
        return []
    if not isinstance(b, dict):
        return ["%s is not an object" % where]
    problems = []
    _keys_exact(b, OLD_JUDGE_BAND_KEYS, where, problems)
    if not _is_2dp(b.get("mean"), 1.0, 5.0):
        problems.append("%s.mean is not a 1-5 value to two decimals" % where)
    if not _is_2dp(b.get("half_width"), 0.0, 2.0):
        problems.append("%s.half_width is not 0-2 to two decimals" % where)
    n = b.get("n_sessions")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        problems.append("%s.n_sessions is not a positive integer" % where)
    return problems


def _r3_rank_problems(r, where, keys=R3_RANK_KEYS):
    if r is None:
        return []
    problems = []
    _keys_exact(r, keys, where, problems)
    rank, of, tie = r.get("rank"), r.get("of"), r.get("tie")
    if not (isinstance(rank, int) and isinstance(of, int) and 1 <= rank <= of):
        problems.append("%s: rank %r of %r" % (where, rank, of))
    if tie is not None:
        try:
            a, b = (int(x) for x in tie.split("-"))
            if not a <= rank <= b:
                problems.append("%s: rank %r outside its tie %r" % (where, rank, tie))
        except (AttributeError, ValueError):
            problems.append("%s: tie %r is not 'a-b'" % (where, tie))
    return problems


def _across_problems(doc, cont):
    problems = []
    t = doc.get("across_rounds_table")
    if not isinstance(t, dict):
        return ["cards: across_rounds_table missing"]
    _keys_exact(t, ACROSS_TABLE_KEYS, "across_rounds_table", problems)
    for mid, c in doc["cards"].items():
        a = c.get("across_rounds")
        where = "card %s.across_rounds" % mid
        if not isinstance(a, dict):
            problems.append("%s missing" % where)
            continue
        _keys_exact(a, ACROSS_KEYS, where, problems)
        hits = ACROSS_BANNED & set(_all_keys(a))
        if hits:
            problems.append("%s carries %s" % (where, sorted(hits)))
        problems += _band_problems(a.get("old_judge_band"), where + ".old_judge_band")
        if a.get("r2_human") is not None:
            _keys_exact(a["r2_human"], ACROSS_R2_KEYS, where + ".r2_human", problems)
        if a.get("r3_nsfw") is not None:
            problems += _r3_rank_problems(a["r3_nsfw"], where + ".r3_nsfw",
                                          keys=ACROSS_R3_KEYS)
        if a.get("transcripts") not in ACROSS_TRANSCRIPTS:
            problems.append("%s.transcripts %r" % (where, a.get("transcripts")))
        if not set(a.get("rounds") or []) <= ACROSS_ROUNDS:
            problems.append("%s.rounds %r" % (where, a.get("rounds")))
        if bool(a.get("returning")) != bool(a.get("rounds")):
            problems.append("%s: returning iff it names an earlier round" % where)
        if not a.get("returning") and (a.get("r2_human") or a.get("r3_nsfw")):
            problems.append("%s: a new model with earlier-round fields" % where)
        if cont is not None and a != across_rounds(cont, mid):
            problems.append("%s differs from %s" % (where, CONTINUITY_NAME))
    return problems


# --------------------------------------------------------------------------
# Cards
# --------------------------------------------------------------------------

def one_decimal(v):
    """Down to one decimal, as a number. The tier is set on the unrounded mean
    with fixed lower edges (3.8, 3.2, ...), so rounding half-up would show a
    B model at 3.76 as "3.8", the bottom of A. Rounding down keeps every shown
    value inside its own tier's range. Decimal on repr() so a binary value
    like 3.8 is not floored to 3.7."""
    return float(Decimal(repr(float(v))).quantize(Decimal("0.1"), ROUND_FLOOR))


def read_overview(results_dir=RESULTS):
    p = Path(results_dir) / OVERVIEW_NAME
    ov = _read_public_json(p)
    jm = ov.get("judge_means") or {}
    if jm.get("judge") != JUDGE_SOURCE or not jm.get("models"):
        raise ExportError("%s: judge_means missing or not from %s; rerun "
                          "analyze_round4_overview.py" % (p.name, JUDGE_SOURCE))
    got = [(r.get("tier"), r.get("lower"), r.get("upper"))
           for r in (ov.get("bands") or {}).get("ranges") or []]
    if got != [tuple(t) for t in JUDGE_TIERS]:
        raise ExportError("%s: tier ranges %s are not the frozen letters %s"
                          % (p.name, got, list(JUDGE_TIERS)))
    return ov


def judge_row(entry):
    """A card's judge row: one decimal, no interval, no edge marker."""
    out = {k: one_decimal(entry[src]) for k, src in JUDGE_COLUMNS}
    out.update(tier=entry["tier"], n_sessions=int(entry["n_sessions"]),
               n_seeds=int(entry["n_seeds"]), note=entry["note"])
    return out


def _count(n, one, many):
    """'Seven tiered models': copy, so small counts are words."""
    words = ("No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
             "Nine", "Ten", "Eleven", "Twelve")
    return "%s %s" % (words[n] if n < len(words) else n, one if n == 1 else many)


def build_judge_table(ov):
    jm = ov["judge_means"]["models"]
    n_all = max(e["n_seeds"] for e in jm.values())
    partial = sorted(m for m, e in jm.items() if e["tier"] and e["n_seeds"] < n_all)
    untiered = sorted(m for m, e in jm.items() if not e["tier"])
    ranges = ", ".join("%s %s" % (r["tier"], r["label"]) for r in ov["bands"]["ranges"])
    note = ("Judge: Sonnet 5 (session judge v2), on the %d adversarial craft seeds, "
            "scale 1-5. Craft is the judge's overall score; Agency, Consist. and "
            "Moment. are its S.5 agency respect, S.1 consistency and S.3 narrative "
            "momentum session scores. Each is the model's mean, rounded down to one "
            "decimal; N is sessions. Craft here is this judge, not the flaw "
            "hunter's craft band on each card. The tier is set on the unrounded "
            "Craft mean with fixed ranges (%s)." % (n_all, ranges))
    if partial:
        note += (" %s played fewer than %d seeds; %s set on all %d by a model "
                 "+ seed fit." % (_count(len(partial), "tiered model", "tiered models"),
                                  n_all, "its means are" if len(partial) == 1
                                  else "their means are", n_all))
    if untiered:
        note += (" %s too few seeds to tier %s listed without a tier, with the "
                 "seeds played beside the name." % (_count(len(untiered), "model with",
                                             "models with"),
                                      "is" if len(untiered) == 1 else "are"))
    note += (" Not comparable with Round 03's numbers, which came from a different "
             "judge (Sonnet 4).")
    return {"judge": JUDGE_LABEL, "scale": "1-5",
            "bands": [{k: r[k] for k in ("tier", "lower", "upper", "label")}
                      for r in ov["bands"]["ranges"]],
            "not_comparable_with": JUDGE_NOT_COMPARABLE, "note": note}


def build_cards(lb, results_dir=RESULTS, commit="unknown", overview=None,
                continuity=None):
    """model-cards.json from generate_profile_cards_v2's own build_card, with
    the round-4 rows from `lb` (never a re-run of the analyzer), the judge
    rows from round4_overview.json and the across_rounds blocks from
    round4_continuity.json (never a re-run of either analyzer)."""
    for name in CARD_INPUTS:
        _guard_path(Path(results_dir) / name)
    ov = overview if overview is not None else read_overview(results_dir)
    cont = continuity if continuity is not None else read_continuity(results_dir)
    jm = ov["judge_means"]["models"]
    ctx = cards_v2.load_inputs(results_dir, r4=cards_v2.r4_rows(lb))
    cards = [cards_v2.build_card(m, ctx) for m in cards_v2.ordered_models(ctx)]
    doc = cards_v2.cards_document(cards, ctx)
    named = {}
    for mid, c in doc["cards"].items():
        name, vendor, fine = display(mid)
        named[mid] = {"id": mid, "name": name, "vendor": vendor,
                      "is_finetune": fine,
                      **{k: v for k, v in c.items() if k != "id"},
                      "judge": judge_row(jm[mid]) if mid in jm else None,
                      "across_rounds": across_rounds(cont, mid)}
    doc["cards"] = named
    doc["inputs"]["judge"] = OVERVIEW_NAME
    doc["inputs"]["across_rounds"] = CONTINUITY_NAME
    doc["judge_table"] = build_judge_table(ov)
    doc["across_rounds_table"] = build_across_table(cont)
    doc["willingness_source"] = "results/round4_willingness_leaderboard.json"
    doc["source_commit"] = commit
    doc["export_id"] = "r4c-%s-%s" % (
        str(doc["reviewed_on"]).replace("-", ""),
        canonical_hash({k: v for k, v in doc.items()
                        if k not in ("export_id", "source_commit")})[:7])
    return doc, cards


def _judge_problems(doc, overview):
    """The judge table is the one place a figure leaves: one decimal, the
    allowlisted keys, the frozen letters, and nothing from the JSON-only edge
    marker or interval."""
    problems = []
    t = doc.get("judge_table")
    if not isinstance(t, dict):
        return ["cards: judge_table missing"]
    _keys_exact(t, JUDGE_TABLE_KEYS, "judge_table", problems)
    if (t.get("judge"), t.get("scale"), t.get("not_comparable_with")) != (
            JUDGE_LABEL, "1-5", JUDGE_NOT_COMPARABLE):
        problems.append("judge_table: judge/scale/not_comparable_with changed")
    bands = t.get("bands") or []
    for b in bands:
        _keys_exact(b, JUDGE_BAND_KEYS, "judge_table band %s" % b.get("tier"), problems)
    if [(b.get("tier"), b.get("lower"), b.get("upper")) for b in bands] != [
            tuple(x) for x in JUDGE_TIERS]:
        problems.append("judge_table: bands are not the frozen letters")
    letters = {x[0] for x in JUDGE_TIERS}
    jm = (overview or {}).get("judge_means", {}).get("models")
    for mid, c in doc["cards"].items():
        j = c.get("judge")
        if jm is not None and (j is not None) != (mid in jm):
            problems.append("card %s: judge present iff in judge_means" % mid)
        if j is None:
            continue
        where = "card %s.judge" % mid
        _keys_exact(j, JUDGE_KEYS, where, problems)
        for k, _ in JUDGE_COLUMNS:
            v = j.get(k)
            if (isinstance(v, bool) or not isinstance(v, (int, float))
                    or not 1.0 <= v <= 5.0 or v != one_decimal(v)):
                problems.append("%s.%s is not a 1-5 value to one decimal: %r"
                                % (where, k, v))
        for k in ("n_sessions", "n_seeds"):
            if isinstance(j.get(k), bool) or not isinstance(j.get(k), int) or j[k] < 1:
                problems.append("%s.%s is not a positive integer" % (where, k))
        if j.get("tier") is not None and j["tier"] not in letters:
            problems.append("%s.tier %r is not a fixed letter" % (where, j["tier"]))
        if (j.get("tier") is None) != bool(j.get("note")):
            problems.append("%s: an untiered row needs a note, a tiered one none" % where)
        if jm is not None and mid in jm and j != judge_row(jm[mid]):
            problems.append("%s differs from round4_overview.json" % where)
    banned = {"edge", "edge_marked", "edge_models", "spans", "mean_lo", "mean_hi"}
    hits = banned & (set(_all_keys(t)) | {k for c in doc["cards"].values()
                                          for k in _all_keys(c.get("judge") or {})})
    if hits:
        problems.append("judge table carries %s" % sorted(hits))
    return problems


def check_cards(doc, lb, overview=None, continuity=None):
    problems = []
    _keys_exact(doc, CARDS_KEYS, "cards", problems)
    problems += _judge_problems(doc, overview)
    problems += _across_problems(doc, continuity)
    lb_models = {r["model"] for r in lb["leaderboard"]}
    for mid, c in doc["cards"].items():
        _keys_exact(c, CARD_KEYS, "card %s" % mid, problems)
        if not c.get("name"):
            problems.append("card %s has no name" % mid)
        if (c["willingness"] is not None) != (mid in lb_models):
            problems.append("card %s: willingness present iff in the leaderboard" % mid)
        if c["willingness"] is not None:
            _keys_exact(c["willingness"], WILLINGNESS_KEYS, "card %s.willingness" % mid,
                        problems)
        if c["craft"] is not None:
            _keys_exact(c["craft"], CRAFT_KEYS, "card %s.craft" % mid, problems)
            nums = [*c["craft"]["axis"], c["craft"]["cells"], *c["craft"]["filled"]]
            if any(not isinstance(x, int) for x in nums):
                problems.append("card %s.craft carries a non-integer" % mid)
        if c["subjective"] is not None:
            _keys_exact(c["subjective"], SUBJECTIVE_KEYS, "card %s.subjective" % mid,
                        problems)
            nums = [*c["subjective"]["axis"], c["subjective"]["cells"],
                    *c["subjective"]["filled"]]
            nums += [x for a in c["subjective"]["axes"] for x in a["filled"]]
            if any(not isinstance(x, int) for x in nums):
                problems.append("card %s.subjective carries a non-integer" % mid)
            for a in c["subjective"]["axes"]:
                if set(a) != {"key", "label", "filled", "less_reliable"}:
                    problems.append("card %s.subjective axis keys %s" % (mid, sorted(a)))
        if c["production_defects"] is not None:
            _keys_exact(c["production_defects"], DEFECT_KEYS,
                        "card %s.production_defects" % mid, problems)
        for part in ("craft", "subjective"):
            if c[part] is not None and "mean" in _all_keys(c[part]):
                problems.append("card %s.%s has a mean key" % (mid, part))
    problems += ["cards text field at %s" % p for p in _text_keys(doc)]
    try:
        _guard_record(doc, "model-cards.json")
    except PublicationGuardError as e:
        problems.append(str(e))
    problems += copy_problems(doc, "cards")
    return problems


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _print_facts(title, facts):
    print("\n%s" % title)
    for k, v in facts.items():
        if isinstance(v, list) and len(v) > 12:
            print("  %-34s %d: %s ..." % (k, len(v), v[:12]))
        else:
            print("  %-34s %s" % (k, v))


def _problems(title, problems):
    if problems:
        print("\n%s: %d problem(s)" % (title, len(problems)))
        for p in problems[:40]:
            print("  - %s" % p)
    else:
        print("%s: all guards pass" % title)
    return bool(problems)


def write_sessions_export(dest, manifest, pair_index, sessions, *, replace=False):
    """Write pair-index.json, sessions.json, then manifest.json into dest.

    Every refusal is decided before the first byte is written. Pair ids and
    sessions freeze into vote rows once voting opens, so without replace:
    an existing sessions.json must be byte-identical, an existing pair-index
    may only gain ids (a larger --matchings), and an existing manifest may
    not lose a pair id (an old non-blind manifest's mt_ ids count)."""
    dest = Path(dest)
    refuse_benchmark_dest(dest, "sessions")
    if not DEST_FOLDER_RE.match(dest.name):
        raise ExportError("sessions --dest must be a folder named round-4-<track>, "
                          "got %s" % dest.name)
    out_m = dest / "manifest.json"
    out_i = dest / "pair-index.json"
    out_s = dest / "sessions.json"
    for p in (dest, out_m, out_i, out_s):
        _guard_path(p)
    blob_m = manifest_json(manifest)
    blob_i = pair_index_json(pair_index)
    blob_s = sessions_json(sessions)
    if not replace:
        why = "; export to a new round-4-<track> folder, or pass --replace before launch"
        if out_s.exists() and out_s.read_bytes() != blob_s:
            raise ExportError("%s exists with different text. sessions.json is "
                              "frozen once voting opens%s" % (out_s, why))
        if out_i.exists():
            old = json.loads(out_i.read_text(encoding="utf-8")).get("pairs") or {}
            changed = sorted(k for k, v in old.items()
                             if pair_index["pairs"].get(k) != v)
            if changed:
                # None surviving is the signature of a different key (or an
                # index from before the ids were keyed), not of a new design.
                hint = ("; none survive: is %s the key this pool was exported "
                        "with?" % PAIR_ID_SECRET_ENV
                        if len(changed) == len(old) else "")
                raise ExportError("%s: %d existing pair ids would change or vanish "
                                  "(first %s)%s%s" % (out_i, len(changed), changed[0],
                                                      hint, why))
        if out_m.exists():
            old_ids = {p.get("id") for p in
                       json.loads(out_m.read_text(encoding="utf-8")).get("pairs") or []}
            gone = sorted(old_ids - set(pair_index["pairs"]))
            if gone:
                raise ExportError("%s: %d existing pair ids would vanish (first %s)%s"
                                  % (out_m, len(gone), gone[0], why))
    dest.mkdir(parents=True, exist_ok=True)
    out_i.write_bytes(blob_i)
    out_s.write_bytes(blob_s)
    out_m.write_bytes(blob_m)
    return out_m, out_i, out_s


def run_sessions(args, lb, commit, check, environ=None):
    # The key first, before any input is read: no key, no blind pool. Under
    # --check the refusal is a failed guard, so board and cards still run.
    try:
        secret = pair_id_secret(environ)
    except PairIdSecretError as e:
        if not check:
            raise
        return _problems("sessions guards", [str(e)])
    roster = sorted(r["model"] for r in lb["leaderboard"] if r["ranked"])
    lb_counts = {r["model"]: r["n_sessions_a"] for r in lb["leaderboard"]}
    seeds = load_seeds()
    exclude = load_exclude(args.exclude) if args.exclude else {}
    paths = r4_paths()
    manifest, pair_index, sessions, report = build_sessions_export(
        paths, seeds, roster, secret=secret, exclude=exclude,
        matchings=args.matchings, rng_seed=args.rng_seed, commit=commit,
        lb_counts=lb_counts, cap=args.message_cap)
    problems, facts = check_sessions_export(manifest, pair_index, sessions, roster,
                                            args.matchings, secret=secret)
    problems += report["problems"]
    hits = youth_screen(sessions, manifest["seeds"], seeds)
    ysum = youth_summary(hits)

    _print_facts("SESSIONS (round-4 Track A, %d ranked models)" % len(roster), {
        "r4 files read (newest first)": [p.name for p in paths],
        **{"dedupe." + k: v for k, v in report["dedupe"].items()},
        **facts,
        "export_id": manifest["export_id"],
        "export_hash": manifest["export_hash"][:16] + "...",
        "source_files (pair-index only)": pair_index["source_files"],
        "exclude file": args.exclude or "(none)",
    })
    _print_facts("YOUTH SCREEN (lexical, for a person to review)", ysum)
    bad = _problems("sessions guards", problems)
    if check or bad:
        return bad

    if not args.dest:
        raise ExportError("sessions: refusing to write without --dest")
    if not args.review_out:
        raise ExportError("sessions: --review-out is required; the youth screen's "
                          "review list is written with every export")
    # The review list is written first: it is outside every repo and is what
    # a person reads before any exclusion.
    write_review(hits, args.review_out)
    out_m, out_i, out_s = write_sessions_export(args.dest, manifest, pair_index,
                                                sessions, replace=args.replace)
    print("\nwrote %s (%d pairs, blind), %s (server-only) and %s (%d sessions)"
          % (out_m, len(manifest["pairs"]), out_i, out_s, len(sessions)))
    print("wrote %s (%d hits in %d sessions): read it, then list any session to "
          "drop in an --exclude file" % (args.review_out, len(hits),
                                         ysum["sessions_flagged"]))
    return False


def run_youth(args):
    lb = _read_public_json(LEADERBOARD)
    roster = sorted(r["model"] for r in lb["leaderboard"] if r["ranked"])
    seeds = load_seeds()
    # No pairs, so no key: the screen reads the sessions alone.
    sessions, _, seeds_meta, _, _ = collect_sessions(
        r4_paths(), seeds, roster,
        exclude=load_exclude(args.exclude) if args.exclude else {},
        cap=args.message_cap)
    hits = youth_screen(sessions, seeds_meta, seeds)
    _print_facts("YOUTH SCREEN", youth_summary(hits))
    if args.check:
        return False
    if not args.review_out:
        raise ExportError("youth: --review-out is required")
    write_review(hits, args.review_out)
    print("\nwrote %s (%d hits)" % (args.review_out, len(hits)))
    return False


def _write_json_file(dest, obj, name):
    if not dest:
        raise ExportError("%s: refusing to write without --dest" % name)
    p = Path(dest)
    refuse_benchmark_dest(p, name)
    if p.suffix != ".json":
        raise ExportError("%s --dest must be a .json file path" % name)
    _guard_path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
                 encoding="utf-8")
    print("\nwrote %s" % p)


def run_board(args, lb, commit, check):
    cont = read_continuity(RESULTS)
    board = build_board(lb, commit, continuity=cont)
    problems = check_board(board, continuity=cont)
    ranked = [r for r in board["rows"] if r["ranked"]]
    _print_facts("BOARD (round-4.json)", {
        "rows": len(board["rows"]), "ranked": len(ranked),
        "unranked": [(r["model"], r["unranked_reason"][:48])
                     for r in board["rows"] if not r["ranked"]],
        "j_ties": [t["models"] for t in board["j_ties"]],
        "silent_flag": [r["model"] for r in board["rows"] if r["empty"]["silent_flag"]],
        "reduced_seed_set": sum(r["reduced_seed_set"] for r in board["rows"]),
        "with old_judge_band": sum(r["old_judge_band"] is not None for r in board["rows"]),
        "with r3_nsfw_rank": sum(r["r3_nsfw_rank"] is not None for r in board["rows"]),
        "export_id": board["export_id"],
    })
    bad = _problems("board guards", problems)
    if check or bad:
        return bad
    _write_json_file(args.dest, board, "board")
    return False


def run_cards(args, lb, commit, check):
    ov = read_overview(RESULTS)
    cont = read_continuity(RESULTS)
    doc, _ = build_cards(lb, RESULTS, commit, overview=ov, continuity=cont)
    problems = check_cards(doc, lb, overview=ov, continuity=cont)
    cards = doc["cards"]
    _print_facts("CARDS (model-cards.json)", {
        "cards": len(cards),
        "with judge row": sum(c["judge"] is not None for c in cards.values()),
        "with judge tier": sum(bool(c["judge"] and c["judge"]["tier"])
                               for c in cards.values()),
        "judge rows without a tier": [(m, c["judge"]["note"]) for m, c in cards.items()
                                      if c["judge"] and not c["judge"]["tier"]],
        "no judge row": sorted(m for m, c in cards.items() if c["judge"] is None),
        "judge models without a card": sorted(set(ov["judge_means"]["models"]) - set(cards)),
        "with willingness": sum(c["willingness"] is not None for c in cards.values()),
        "with craft band": sum(c["craft"] is not None for c in cards.values()),
        "with subjective band": sum(c["subjective"] is not None for c in cards.values()),
        "with production defects": sum(c["production_defects"] is not None
                                       for c in cards.values()),
        "names from CARD_ONLY": sorted(m for m in cards if m not in NAMES),
        "returning (across_rounds)": sum(c["across_rounds"]["returning"]
                                         for c in cards.values()),
        "with old_judge_band": sum(c["across_rounds"]["old_judge_band"] is not None
                                   for c in cards.values()),
        "inputs": doc["inputs"],
        "export_id": doc["export_id"],
    })
    bad = _problems("cards guards", problems)
    if check or bad:
        return bad
    _write_json_file(args.dest, doc, "cards")
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n", 2)[2])
    ap.add_argument("command", nargs="?", choices=("sessions", "board", "cards", "youth"),
                    help="omit with --check to dry-run everything")
    ap.add_argument("--check", action="store_true",
                    help="dry run: print counts and guard results, write nothing")
    ap.add_argument("--dest", help="output folder (sessions) or .json file (board, cards)")
    ap.add_argument("--review-out", help="youth-screen review list (TSV), outside any repo")
    ap.add_argument("--exclude", help="file of '<seed_id>::<model> <reason>' lines")
    ap.add_argument("--matchings", type=int, default=DEFAULT_MATCHINGS,
                    help="pairs per model per seed (default %d)" % DEFAULT_MATCHINGS)
    ap.add_argument("--rng-seed", type=int, default=DEFAULT_RNG_SEED)
    ap.add_argument("--message-cap", type=int, default=MESSAGE_CAP,
                    help="cut any message longer than this many UTF-16 units, "
                         "with a cut_from_chars marker (default %d)" % MESSAGE_CAP)
    ap.add_argument("--replace", action="store_true",
                    help="allow overwriting an existing, different sessions.json "
                         "and pair ids (before launch only)")
    args = ap.parse_args(argv)
    if args.command is None and not args.check:
        ap.error("name a command, or pass --check to dry-run all of them")
    if args.check and (args.dest or args.review_out):
        ap.error("--check writes nothing; drop --dest/--review-out")
    if args.matchings < 1:
        ap.error("--matchings must be at least 1")
    if args.message_cap < 1000:
        ap.error("--message-cap below 1000 would gut ordinary replies")

    try:
        if args.command == "youth":
            return 1 if run_youth(args) else 0
        if args.command == "sessions" and not args.check:
            # No key, no blind pool: refuse before git or any input is read.
            pair_id_secret()
        commit = source_commit()
        lb = _read_public_json(LEADERBOARD)
        commands = [args.command] if args.command else ["sessions", "board", "cards"]
        inputs = [LEADERBOARD]
        if "sessions" in commands:
            inputs += [SEEDS_A, *r4_paths()]
        if "cards" in commands:
            inputs += [RESULTS / n for n in CARD_INPUTS] + [RESULTS / OVERVIEW_NAME]
        if "board" in commands or "cards" in commands:
            inputs += [RESULTS / CONTINUITY_NAME]
        dirty = input_problems(inputs)
        print("source_commit %s; %d input files, %s" % (
            commit[:12], len(inputs),
            "all match HEAD" if not dirty else "%d differ from HEAD" % len(dirty)))
        for d in dirty:
            print("  - %s" % d)
        if dirty and not args.check:
            raise ExportError("inputs differ from HEAD; commit or restore them first")
        bad = bool(dirty)
        runners = {"sessions": run_sessions, "board": run_board, "cards": run_cards}
        for c in commands:
            bad |= runners[c](args, lb, commit, args.check)
        if args.check:
            print("\n--check: nothing written. %s" % ("FAILED" if bad else "OK"))
        return 1 if bad else 0
    except (ExportError, PublicationGuardError) as e:
        print("\nexport_plotpoints_round4: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
