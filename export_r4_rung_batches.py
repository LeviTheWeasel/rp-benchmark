#!/usr/bin/env python3
"""Export unlabelled round-4 rungs as judging batches for the subscription path.

classify_r4_refusals.py does this over the API, one focused call per rung.
Judging moved off OpenRouter, so the same work now goes out as batches. The
rubrics, the ladder text and the exchange-splitting are IMPORTED from the
classifier rather than restated here: a paraphrased rubric would silently make
the two paths non-comparable, and the corpus is meant to be one instrument.

What the judge does NOT decide: content_hits, is_control and disputed are
mechanical functions of the reply and the seed. They are computed at import,
exactly as the API path computes them, so the two routes cannot drift on them.

Incremental by construction: a session that already carries rung_labels is
skipped, and batch numbering continues past the highest index on disk.
"""
import argparse
import glob
import hashlib
import json
import re
from pathlib import Path

from classify_r4_refusals import (TRACK_A_SYSTEM, TRACK_B_SYSTEM, B4_EXTRA,
                                  B_DEFAULT_EXTRA, exchanges)
from draft_r4_rungs import LADDERS
from harness.multiturn import load_seeds
from harness.r4_private import load_r4

BATCH_DIR = Path("/tmp/claude-1000/-home-levi-ST-VAUDEVILLE/"
                 "0e0eeb99-f00a-4b4d-87ff-9f01392fa806/scratchpad/r4_rung_batches")


def verdict_fits(verdict: dict, reply: str) -> bool:
    """Was this verdict written about THIS reply?

    The quote is the anchor: a label written about the full reply carries a
    clause that is not in the truncated copy, and the reverse. PARSE_ERROR
    carries prose instead of a quote, so it is checked against the shape of
    the reply it claims is unreadable.
    """
    if verdict.get("label") == "PARSE_ERROR":
        return len((reply or "").strip()) <= PARSE_ERROR_MAX_CHARS
    ev = strip_no_delivery(verdict.get("evidence") or "").strip()
    return bool(ev) and ev in (reply or "")


# Track B raters mark "accepted the premise but produced nothing" by prefixing
# the quote. The quote after the prefix is still verbatim, so strip it before
# any substring check -- the first version of this rule demanded the prefix and
# then rejected every verdict carrying it.
NO_DELIVERY = "NO-DELIVERY:"


def strip_no_delivery(ev: str) -> str:
    return ev[len(NO_DELIVERY):].lstrip() if ev.startswith(NO_DELIVERY) else ev


# A reply this short is a generation dropout, not a reply. Raters label these
# PARSE_ERROR; longer text called unreadable is re-judged rather than trusted.
PARSE_ERROR_MAX_CHARS = 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-batch", type=int, default=120)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    seeds = {s["id"]: s for s in load_seeds(round4="all")}
    items, empties, no_seed, superseded = [], 0, 0, 0

    # NEWEST FIRST, first-wins -- the rule analyze_round4_willingness.py already
    # uses. A model re-generated after the token-ceiling fix has the same
    # (model, seed) in the run that was replaced and in its replacement, with
    # DIFFERENT text. item_id is model::seed::turn and carries no file, so
    # exporting both sends two raters the same id over two different replies,
    # and whichever verdict is read first wins at import -- a score attached to
    # a transcript that is not the one it was made against.
    seen = set()
    for f in sorted(glob.glob("results/r4_full_*.json"), reverse=True):
        # Track B text rejoined from its private companion; exchanges()
        # raises for an unlabelled session whose text is not on disk.
        data = load_r4(f)
        for s in data.get("sessions", []):
            if s.get("error"):
                continue
            # Claim the key BEFORE the already-labelled check. With the checks
            # the other way round, a NEWER session that already carries labels
            # never claims its key, so the older copy it replaced looks fresh
            # and gets exported -- sending raters 151 truncated transcripts the
            # analyzer will never read, because the analyzer resolves the same
            # pair to the labelled repair. Identical ordering bug to the one
            # already fixed in import_r4_rung_batches.py.
            key = (s.get("test_model"), s.get("seed_id"))
            if key in seen:
                superseded += 1
                continue
            seen.add(key)
            if s.get("rung_labels"):
                continue
            seed = seeds.get(s.get("seed_id"))
            if not seed:
                no_seed += 1
                continue
            for spec, user_text, reply in exchanges(s, seed):
                # An empty reply carries no signal and needs no judge. The API
                # path labels it mechanically; so does the importer. Sending it
                # out would invite a rater to score silence as a refusal.
                if not (reply or "").strip():
                    empties += 1
                    continue
                track = seed["track"]
                if track == "A":
                    ladder = "gore" if seed.get("subtrack") == "gore" else "intimacy"
                    rubric = TRACK_A_SYSTEM % {
                        "rung_desc": LADDERS[ladder].get(spec.get("rung"),
                                                         "(unspecified)")}
                else:
                    extra = (B4_EXTRA if seed.get("probe_type") == "B4"
                             else B_DEFAULT_EXTRA)
                    rubric = TRACK_B_SYSTEM % {"extra": extra}
                items.append({
                    "item_id": "%s::%s::t%s" % (s["test_model"], s["seed_id"],
                                                spec["turn"]),
                    # Binds the verdict to the exact reply it was made against.
                    "reply_sha": hashlib.sha256(
                        reply.encode("utf-8")).hexdigest()[:12],
                    "source_file": Path(f).name,
                    "model": s["test_model"], "seed": s["seed_id"],
                    "track": track, "subtrack": seed.get("subtrack"),
                    "probe_type": seed.get("probe_type"),
                    "rung": spec.get("rung"), "turn": spec["turn"],
                    "rubric": rubric,
                    "user_turn": user_text, "ai_reply": reply})

    # Never re-issue an item that already has a verdict on disk -- but a
    # verdict counts only if it was made against THIS reply. The first cut of
    # these batches shipped 155 item_ids twice over two different texts, so
    # matching on the id alone would keep a label written about the truncated
    # copy. Every verdict carries a quote; that quote is the anchor.
    verdicts = {}
    for out in BATCH_DIR.glob("*.out.json"):
        try:
            for r in json.load(open(out)):
                verdicts.setdefault(r.get("item_id"), []).append(r)
        except (OSError, ValueError):
            continue

    fresh, stale = [], 0
    for i in items:
        if any(verdict_fits(r, i["ai_reply"]) for r in verdicts.get(i["item_id"], [])):
            continue
        if i["item_id"] in verdicts:
            stale += 1
        fresh.append(i)

    print("rungs needing a label : %d" % len(items))
    print("  already judged      : %d" % (len(items) - len(fresh)))
    print("  empty replies (auto): %d" % empties)
    if stale:
        print("  verdicts REJECTED - written about a different copy of the "
              "reply: %d" % stale)
    if no_seed:
        print("  sessions whose seed is missing: %d" % no_seed)
    if superseded:
        print("  sessions skipped as superseded by a newer run: %d" % superseded)
    if args.dry_run:
        return

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    start = 0
    for p in BATCH_DIR.glob("r4rung_*.json"):
        m = re.match(r"r4rung_(\d+)\.json$", p.name)
        if m:
            start = max(start, int(m.group(1)))
    n = 0
    for k in range(0, len(fresh), args.per_batch):
        n += 1
        bid = "r4rung_%03d" % (start + n)
        (BATCH_DIR / (bid + ".json")).write_text(
            json.dumps(fresh[k:k + args.per_batch], indent=1, ensure_ascii=False))
    print("wrote %d batches -> %s" % (n, BATCH_DIR))


if __name__ == "__main__":
    main()
