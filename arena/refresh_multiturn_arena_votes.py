#!/usr/bin/env python3
"""Rebuild data/multiturn_arena_votes.jsonl from the site's public round-2 CSV.

The round-2 human multi-turn arena closed on plotlightstudios.com on
2026-06-13 at 1,943 votes (round archive: /plotpoints/round/2). The repo had
stopped at a 1,262-vote pull from 2026-06-04, with a different order at the
top. This script replaces that pull with the site's public raw export

    GET https://plotlightstudios.com/api/plotpoints/raw?round=2&mode=multiturn_arena

and keeps the 30 older ballots that exist only in the previous file: votes
cast on arena.l3vi4th4n.ai after its 507 round-2 votes were imported into the
site (source "arena_l3vi4th4n_only"). arena/analyze_multiturn_arena.py keeps those
30 unscored, so its ranking is the round's published one.

Voter ids. They are random per-voter UUIDs that exist to catch vote stuffing,
so they are published raw. Each vote's id comes from the CSV's voter_id column
(present once the site ships it), else from an earlier copy of this file
(--ids-from, or the previous file), matched on the vote id exactly; a vote with
no known id has no voter_id field. --hmac writes HMAC-SHA256(secret, id) via
publication_guards.voter_pseudonym instead. arena/analyze_multiturn_arena.py reports
the voter count as unknown while any scored row lacks an id.

Provenance (URL, fetch time, CSV sha256, counts) goes to
data/multiturn_arena_votes.README.md, rewritten on every run.

Usage:
    python3 arena/refresh_multiturn_arena_votes.py             # fetch; takes ~2 min
    python3 arena/refresh_multiturn_arena_votes.py --csv FILE --fetched-at ISO
                                                         # a saved copy
"""
import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from lib.publication_guards import VOTER_HMAC_ENV, voter_pseudonym, voter_secret

URL = ("https://plotlightstudios.com/api/plotpoints/raw"
       "?round=2&mode=multiturn_arena")
ARCHIVE = "https://plotlightstudios.com/plotpoints/round/2"
ROUND, MODE = 2, "multiturn_arena"
# The round-2 archive's closing totals. The round is closed, so a different
# row count means the export or the archive changed; stop rather than guess.
ARCHIVE_VOTES, ARCHIVE_VOTERS, ARCHIVE_PAIRS = 1943, 482, 190
LEGACY_SOURCE = "arena_l3vi4th4n_only"

OUT = Path("data/multiturn_arena_votes.jsonl")
README = Path("data/multiturn_arena_votes.README.md")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-"
                   r"[0-9a-f]{12}$", re.I)


def fetch(url, timeout):
    req = Request(url, headers={"User-Agent": "rp-benchmark refresh"})
    with urlopen(req, timeout=timeout) as r:
        return r.read()


def site_rows(raw: bytes):
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
    bad = [r["id"] for r in rows
           if r.get("round") != str(ROUND) or r.get("mode") != MODE]
    if bad:
        raise SystemExit("%d rows are not round %d / %s (first: %s)"
                         % (len(bad), ROUND, MODE, bad[0]))
    if len({r["id"] for r in rows}) != len(rows):
        raise SystemExit("duplicate vote ids in the CSV")
    pairs = {tuple(sorted((r["model_a"], r["model_b"]))) for r in rows}
    if len(rows) != ARCHIVE_VOTES or len(pairs) != ARCHIVE_PAIRS:
        raise SystemExit(
            "CSV has %d votes / %d pairs; the round-2 archive says %d / %d"
            % (len(rows), len(pairs), ARCHIVE_VOTES, ARCHIVE_PAIRS))
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "round": ROUND,
            "timestamp": r["client_timestamp"] or None,
            "server_timestamp": r["created_at"],
            "mode": r["mode"],
            "scenario_id": r["scenario_id"],
            "context": r["context"],
            "model_a": r["model_a"],
            "model_b": r["model_b"],
            "winner": r["winner"],
            "is_catch": r["is_catch"] == "true",
            "catch_correct": {"true": True, "false": False}.get(
                r["catch_correct"]),
            "source": r["source"],
            "signed_in": r["signed_in"] == "1",
            **({"voter_id": r["voter_id"]} if r.get("voter_id") else {}),
        })
    return out


def previous_rows(path=OUT):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(l) for l in open(path) if l.strip()]


def known_voter_ids(*row_sets):
    """vote id -> raw voter id, from rows that carry a UUID voter_id."""
    known = {}
    for rows in row_sets:
        for r in rows:
            v = r.get("voter_id")
            if isinstance(v, str) and _UUID.match(v):
                known.setdefault(r["id"], v)
    return known


def _when(row):
    ts = row.get("server_timestamp") or row.get("timestamp") or ""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="read a saved copy of the CSV instead of "
                                  "fetching it")
    ap.add_argument("--fetched-at", help="with --csv: when that copy was "
                                         "fetched (ISO 8601, UTC)")
    ap.add_argument("--timeout", type=int, default=600,
                    help="seconds; the endpoint takes about two minutes")
    ap.add_argument("--ids-from", action="append", default=[], metavar="JSONL",
                    help="an earlier copy of this file whose voter ids fill in "
                         "votes the CSV has none for (matched on vote id); "
                         "repeatable")
    ap.add_argument("--hmac", action="store_true",
                    help="write HMAC-SHA256(%s, id) instead of raw ids"
                         % VOTER_HMAC_ENV)
    args = ap.parse_args()

    if args.csv:
        raw = Path(args.csv).read_bytes()
        fetched = args.fetched_at or "unknown (read from %s)" % args.csv
    else:
        print("Fetching %s ..." % URL)
        started = datetime.now(timezone.utc)
        raw = fetch(URL, args.timeout)
        done = datetime.now(timezone.utc)
        fetched = "%s to %s" % (started.isoformat(timespec="seconds"),
                                done.isoformat(timespec="seconds"))
    sha = hashlib.sha256(raw).hexdigest()
    site = site_rows(raw)
    site_ids = {r["id"] for r in site}

    prev = previous_rows()
    known_raw = known_voter_ids(site, prev,
                                *(previous_rows(p) for p in args.ids_from))
    legacy = []
    for r in prev:
        if r["id"] in site_ids:
            continue
        if r.get("source") != LEGACY_SOURCE:
            raise SystemExit(
                "vote %s (source %r) is in the previous file but not in the "
                "site export; only %s rows are expected there"
                % (r["id"], r.get("source"), LEGACY_SOURCE))
        legacy.append({k: v for k, v in r.items() if k != "voter_id"})

    secret = voter_secret() if args.hmac else None
    rows = sorted(site + legacy, key=lambda r: (_when(r), r["id"]))
    n_ids = 0
    for r in rows:
        raw_id = known_raw.get(r["id"])
        r.pop("voter_id", None)
        if raw_id:
            r["voter_id"] = voter_pseudonym(secret, raw_id) if secret else raw_id
            n_ids += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    by_source = Counter(r["source"] for r in rows)
    first, last = site[0]["server_timestamp"], site[-1]["server_timestamp"]
    voter_line = (
        "%s on %d of %d rows; the rest carry no voter_id yet and get one when "
        "the site's CSV serves its voter_id column (re-run this script)."
        % ("HMAC-SHA256(%s, raw id)" % VOTER_HMAC_ENV if secret else "raw",
           n_ids, len(rows))
        if n_ids < len(rows) else
        "%s on every row." % ("HMAC-SHA256(%s, raw id)" % VOTER_HMAC_ENV
                              if secret else "raw"))
    README.write_text("""\
# data/multiturn_arena_votes.jsonl

Human votes from the round-2 multi-turn arena (full 12-turn dialogues, 20
models, 20 adversarial seeds). Written by `arena/refresh_multiturn_arena_votes.py`;
scored by `arena/analyze_multiturn_arena.py`.

## Source

- Site export: `GET {url}`
  (round {round}, mode `{mode}`; checked against the round archive,
  {archive}: {av:,} votes, {avo} voters, {ap} pairs, closed 2026-06-13).
- Fetched: {fetched}
- CSV: {nbytes:,} bytes, sha256 `{sha}`, {nsite:,} rows, created_at
  {first} to {last}.
- Plus {nleg} older rows kept from the previous file, source
  `{legacy}`: ballots cast on `arena.l3vi4th4n.ai` (the round-1/2 arena's
  original domain, which the project no longer controls) after its 507
  round-2 votes were imported into the site on 2026-04-30. They never reached
  the site's round-2 tally, so `arena/analyze_multiturn_arena.py` keeps them unscored.

Rows by source: {sources}. Total {ntot:,} rows, sorted by server timestamp.

## Fields

`timestamp` is the client timestamp and `server_timestamp` the site's
`created_at`, both as the CSV gives them. `signed_in` is the CSV's boolean;
the export leaves out IP hashes, user agents and user ids.

Voter ids: {voters} They are random per-voter UUIDs published so vote-stuffing
checks can be reproduced; ids come from the CSV's voter_id column when it has
one, else from an earlier copy of this file matched on the vote id. While any
row lacks an id, the voter count (the archive's {avo}) and the voter-clustered
bootstrap (`arena/analyze_multiturn_arena_bootstrap.py`) cover only the rows that
have one.

Before this refresh the file held a 1,262-vote pull from 2026-06-04 (1,232 of
those votes are in the CSV unchanged, plus the {nleg} kept above).
""".format(url=URL, round=ROUND, mode=MODE, archive=ARCHIVE,
           av=ARCHIVE_VOTES, avo=ARCHIVE_VOTERS, ap=ARCHIVE_PAIRS,
           fetched=fetched, nbytes=len(raw), sha=sha, nsite=len(site),
           first=first, last=last, nleg=len(legacy),
           legacy=LEGACY_SOURCE,
           sources=", ".join("%s %d" % kv for kv in sorted(by_source.items())),
           ntot=len(rows), voters=voter_line))

    print("site rows:   %d (sha256 %s)" % (len(site), sha[:16]))
    print("legacy rows: %d (%s)" % (len(legacy), LEGACY_SOURCE))
    print("voter ids:   %d of %d rows (%s)"
          % (n_ids, len(rows), "HMAC" if secret else "raw"))
    print("wrote %s (%d rows) and %s" % (OUT, len(rows), README))


if __name__ == "__main__":
    main()
