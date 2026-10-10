#!/usr/bin/env python3
"""Fetch the single-message community arena votes from the site's public export.

    GET https://plotlightstudios.com/api/plotpoints/raw?round=1&mode=arena

Round 1, mode `arena`: the 2,013 single-message votes (closed; round archive
https://plotlightstudios.com/plotpoints/round/1). They are written to
web/data/votes.jsonl (git-ignored), one JSON object per vote in the shape the
arena server's own log had: id, round, mode, timestamp (the client's),
server_timestamp (the site's created_at), scenario_id, context, model_a,
model_b, winner (A / B / tie), is_catch, catch_correct, source, signed_in.
Timestamps are UTC ISO 8601 with a Z and three fraction digits, as the arena's
log wrote them (six when a value has microseconds).

Voter ids: the site's export gains a `voter_id` column (random per-voter
UUIDs, published so vote-stuffing checks can be reproduced); it is passed
through whenever the CSV has it. An older copy without it cannot feed the
per-voter work (arena/analyze_voter_quality.py, the suspect-voter filter in
arena/analyze_community_arena.py), which refuses rather than run on a partial log.
The export never carries response text, so arena/analyze_engagement_regressor.py
cannot run on this file.

The other modes are not fetched here. data/multiturn_arena_votes.jsonl is
rebuilt from the round-2 export by arena/refresh_multiturn_arena_votes.py, with its
provenance README. data/rubric_votes.jsonl is not refetched (the public export
drops the rated response text that file holds); it keeps its voter ids.

This script used to pull a JSON endpoint on the original arena domain. That
domain is no longer the project's, and nothing here fetches from it.

Usage:
    python3 arena/fetch_arena_votes.py                 # fetch into web/data/votes.jsonl
    python3 arena/fetch_arena_votes.py --csv FILE      # a saved copy of the CSV
    python3 arena/fetch_arena_votes.py --out PATH
"""
import argparse
import csv
import hashlib
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAW_URL = "https://plotlightstudios.com/api/plotpoints/raw"
ARENA_ROUND, ARENA_MODE = 1, "arena"
ARENA_CSV_URL = "%s?round=%d&mode=%s" % (RAW_URL, ARENA_ROUND, ARENA_MODE)
FETCH_TIMEOUT = 600          # seconds; the round-2 export takes about two minutes

DEST = Path("web/data/votes.jsonl")

# Columns the conversion reads. The export also has model, scores and notes
# (rubric mode only), which an arena vote leaves empty.
CSV_COLUMNS = ("id", "round", "mode", "scenario_id", "context", "model_a",
               "model_b", "winner", "is_catch", "catch_correct", "source",
               "signed_in", "client_timestamp", "created_at")
WINNERS = frozenset({"A", "B", "tie"})
_BOOL = {"true": True, "false": False, "1": True, "0": False}


def fetch_csv(url: str = ARENA_CSV_URL, timeout: int = FETCH_TIMEOUT) -> bytes:
    """The raw CSV bytes. urllib.request.urlopen is looked up on each call,
    so a test can stub the network by patching it."""
    req = urllib.request.Request(url, headers={"User-Agent": "rp-benchmark fetch"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def iso_utc(ts: str) -> str:
    """"2026-04-14T19:16:56.291+00:00" -> "2026-04-14T19:16:56.291Z".

    The CSV gives Postgres-style offsets with trailing zeros trimmed from the
    fraction ("...:56.29+00:00", or none at all); the arena's log wrote UTC
    with a Z and three digits. Microseconds are kept when there are any.
    An empty value stays empty."""
    ts = (ts or "").strip()
    if not ts:
        return ""
    d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("timestamp without a UTC offset: %r" % ts)
    d = d.astimezone(timezone.utc)
    frac = ("%06d" % d.microsecond) if d.microsecond % 1000 else (
        "%03d" % (d.microsecond // 1000))
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + frac + "Z"


def _bool(value: str, where: str):
    """"true"/"false" (or 1/0) -> bool; "" -> None."""
    v = (value or "").strip().lower()
    if v == "":
        return None
    if v not in _BOOL:
        raise SystemExit("%s: not a boolean: %r" % (where, value))
    return _BOOL[v]


def votes_from_csv(raw, round_: int = ARENA_ROUND,
                   mode: str = ARENA_MODE) -> list[dict]:
    """Parse the site's raw export into arena-log vote dicts, in CSV order.

    Stops (SystemExit) on a CSV that is not the expected export: a missing
    column, a row from another round or mode, a duplicate id, a winner other
    than A / B / tie. A `voter_id` column, if the CSV has one, is passed
    through as is (the public export has none)."""
    text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
    reader = csv.DictReader(io.StringIO(text, newline=""))
    missing = [c for c in CSV_COLUMNS if c not in (reader.fieldnames or ())]
    if missing:
        raise SystemExit("not the site's raw vote export: no %s column"
                         % ", ".join(missing))
    has_voter = "voter_id" in reader.fieldnames
    out, seen = [], set()
    for r in reader:
        vid = r["id"]
        where = "vote %s" % (vid or "(no id)")
        if not vid or vid in seen:
            raise SystemExit("%s: missing or duplicate vote id" % where)
        seen.add(vid)
        if r["round"] != str(round_) or r["mode"] != mode:
            raise SystemExit("%s is round %s / %s; expected round %d / %s"
                             % (where, r["round"], r["mode"], round_, mode))
        if r["winner"] not in WINNERS:
            raise SystemExit("%s: winner %r is not A, B or tie"
                             % (where, r["winner"]))
        vote = {
            "id": vid,
            "round": round_,
            "mode": r["mode"],
            "timestamp": iso_utc(r["client_timestamp"]),
            "server_timestamp": iso_utc(r["created_at"]),
            "scenario_id": r["scenario_id"],
            "context": r["context"],
            "model_a": r["model_a"],
            "model_b": r["model_b"],
            "winner": r["winner"],
            "is_catch": _bool(r["is_catch"], where) is True,
            "catch_correct": _bool(r["catch_correct"], where),
            "source": r["source"],
            "signed_in": _bool(r["signed_in"], where) is True,
        }
        if has_voter and r["voter_id"]:
            vote["voter_id"] = r["voter_id"]
        out.append(vote)
    return out


def carries_voter_ids(votes: list[dict]) -> bool:
    """True when at least one vote has a voter id (raw or pseudonymous)."""
    return any(v.get("voter_id") for v in votes)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--csv", type=Path,
                    help="read a saved copy of the CSV instead of fetching it")
    ap.add_argument("--out", type=Path, default=DEST,
                    help="where to write the votes (default: %(default)s)")
    ap.add_argument("--timeout", type=int, default=FETCH_TIMEOUT,
                    help="seconds (default: %(default)s)")
    args = ap.parse_args()

    if args.csv:
        raw = args.csv.read_bytes()
        print("Reading %s" % args.csv)
    else:
        print("Fetching %s ..." % ARENA_CSV_URL)
        raw = fetch_csv(ARENA_CSV_URL, args.timeout)
    votes = votes_from_csv(raw)
    print("  %d votes (round %d, %s), %d bytes, sha256 %s"
          % (len(votes), ARENA_ROUND, ARENA_MODE, len(raw),
             hashlib.sha256(raw).hexdigest()[:16]))
    print("  voter ids: %s" % ("present in this CSV" if carries_voter_ids(votes)
                               else "none (the public export carries none)"))
    args.out.parent.mkdir(exist_ok=True, parents=True)
    with open(args.out, "w") as f:
        for v in votes:
            f.write(json.dumps(v) + "\n")
    print("  wrote %s" % args.out)


if __name__ == "__main__":
    main()
