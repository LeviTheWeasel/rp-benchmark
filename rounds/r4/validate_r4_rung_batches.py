#!/usr/bin/env python3
"""Check every rung out-file against the batch it claims to answer.

Parallel raters share one scratchpad. One of them wrote a helper at a generic
path, another overwrote it, and for a while the first was reading a different
batch's items. It noticed. The next one might not, and a swapped item_id set is
the one contamination that a label-shaped output cannot reveal by itself.

Set equality is the test that catches it: an answer built from another batch's
text still has to carry item_ids from somewhere, and they will not be these.
"""
import json
import sys
from pathlib import Path

BATCH_DIR = Path("/tmp/claude-1000/-home-levi-ST-VAUDEVILLE/"
                 "0e0eeb99-f00a-4b4d-87ff-9f01392fa806/scratchpad/r4_rung_batches")
TRACK_A = {"engaged", "soft_deflect", "refused"}
TRACK_B = {"held", "complied"}

bad = 0
for src in sorted(BATCH_DIR.glob("r4rung_*.json")):
    if src.name.endswith(".out.json"):
        continue
    out = src.with_suffix("").with_suffix(".out.json") \
        if False else BATCH_DIR / (src.stem + ".out.json")
    if not out.exists():
        continue
    items = json.load(open(src))
    try:
        rows = json.load(open(out))
    except ValueError as e:
        print("%-16s UNPARSEABLE: %s" % (src.stem, e))
        bad += 1
        continue
    by_id = {i["item_id"]: i for i in items}
    got = [r.get("item_id") for r in rows]
    problems = []
    if len(rows) != len(items):
        problems.append("%d rows for %d items" % (len(rows), len(items)))
    missing = set(by_id) - set(got)
    alien = set(got) - set(by_id)
    if missing:
        problems.append("%d items unanswered" % len(missing))
    if alien:
        problems.append("%d item_ids from OUTSIDE this batch: %s"
                        % (len(alien), sorted(alien)[:3]))
    if len(set(got)) != len(got):
        problems.append("duplicate item_ids in the output")

    quote_fail = label_fail = 0
    for r in rows:
        it = by_id.get(r.get("item_id"))
        if it is None:
            continue
        allowed = TRACK_A if it["track"] == "A" else TRACK_B
        lab = r.get("label")
        if lab not in allowed and lab != "PARSE_ERROR":
            label_fail += 1
        ev = r.get("evidence") or ""
        if ev.startswith("NO-DELIVERY:"):
            ev = ev[len("NO-DELIVERY:"):].lstrip()
        # PARSE_ERROR may carry prose instead of a quote; every other label
        # must be anchored in the reply it describes.
        if lab != "PARSE_ERROR" and ev and ev not in it["ai_reply"]:
            quote_fail += 1
    if label_fail:
        problems.append("%d labels illegal for their track" % label_fail)
    if quote_fail:
        problems.append("%d quotes not found in the reply" % quote_fail)

    if problems:
        bad += 1
        print("%-16s FAIL  %s" % (src.stem, "; ".join(problems)))
    else:
        print("%-16s ok    %d items" % (src.stem, len(rows)))

print("\n%s" % ("all checked batches clean" if not bad
                else "%d batch(es) need attention" % bad))
sys.exit(1 if bad else 0)
