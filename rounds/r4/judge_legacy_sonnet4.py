#!/usr/bin/env python3
"""Old-judge continuity column: the round-2/3 craft judge on round-4 transcripts.

Round 4 moved the craft judge from Claude Sonnet 4 (API, "v1") to Claude
Sonnet 5 (subscription subagents, "v2", results/session_judge_v2.jsonl). 779
of the 1,328 current craft sessions still carry a Sonnet 4 score on their
current transcript; the rest (the 30 new models, plus the 97 sessions
regenerated after the old 4096-token cap) never saw the old judge. This driver
gives them one, with nothing changed but the date:

    function     harness.multiturn.judge_session(session, model, nsfw=False)
                 -- called as is, so the prompt build, the transcript format
                 and the JSON parse are the harness's own, not a copy
    model        anthropic/claude-sonnet-4   (JUDGE_MODELS["claude_sonnet"])
    system       SESSION_JUDGE_SYSTEM, sha256 prefix 1ff004ccf5aa (unchanged
                 since 2026-04-13; the same file the external packages ship as
                 RUBRIC.md)
    sampling     JUDGE_CONFIG: temperature 0.1, max_tokens 4096, nothing else
    transport    harness.api.chat_completion, same retries and rate gate

The driver refuses to start if any of those has drifted.

Output: one JSON line per session in results/session_judge_v1_legacy.jsonl,
carrying the transcript_hash (transcript_hash.transcript_hash, the function the
v2 rows use) and a stricter judge_view_hash (the exact text the judge was
sent), plus the model id the API reports back, the provider that served it,
and the call's cost.

Resume-safe: a session whose session_id is already in the output file with the
same transcript_hash is skipped, so an interrupted run is finished by running
the same command again. A parse failure is retried in-run (--parse-retries);
one that survives is written with raw_parse_ok false and is not re-attempted
unless --redo-failed is given, which drops those rows first.

Spend: every call's usage.cost is summed, and OpenRouter's /credits is read at
the start, every --check-every sessions and at the end. The run stops before a
chunk whose projected cost would take total spend since --usage-baseline past
--cap-usd.

Usage:
    python3 rounds/r4/judge_legacy_sonnet4.py --dry-run                 # list targets
    python3 rounds/r4/judge_legacy_sonnet4.py --cap-usd 30 --usage-baseline 1171.10
    python3 rounds/r4/judge_legacy_sonnet4.py --sessions-file ids.txt --include-judged \\
        --out /tmp/gate_rows.jsonl --purpose drift_gate       # re-judge a set
    python3 rounds/r4/judge_legacy_sonnet4.py --verify                  # coverage check
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness import api, multiturn                     # noqa: E402
from harness.config import (JUDGE_CONFIG, JUDGE_MODELS,  # noqa: E402
                            REQUEST_DELAY_SECONDS, RESULTS_DIR)
from lib.transcript_hash import transcript_hash           # noqa: E402

LEGACY_MODEL = "anthropic/claude-sonnet-4"
EXPECTED_PROMPT_HASH = "1ff004ccf5aa"
EXPECTED_JUDGE_CONFIG = {"temperature": 0.1, "max_tokens": 4096}
JUDGE_LABEL = "api-sonnet-4-legacy"
V1_KEY = "claude_sonnet"          # the judges{} key the v1 scores live under

OUT_DEFAULT = RESULTS_DIR / "session_judge_v1_legacy.jsonl"
V2_FILE = RESULTS_DIR / "session_judge_v2.jsonl"
CREDITS_URL = "https://openrouter.ai/api/v1/credits"

# Measured on the 876 stored v1 calls: $0.0356 a session on average. Used to
# project a chunk's cost before the run has measured its own.
DEFAULT_COST_PER_SESSION = 0.036
COST_SAFETY = 1.25


# ---------------------------------------------------------------- provenance

def prompt_hash():
    """sha256 prefix of the session-judge template, before substitution."""
    return hashlib.sha256(
        multiturn.SESSION_JUDGE_SYSTEM.encode("utf-8")).hexdigest()[:12]


def check_config():
    """Refuse to run on anything but the round-2/3 judge configuration."""
    problems = []
    if prompt_hash() != EXPECTED_PROMPT_HASH:
        problems.append("SESSION_JUDGE_SYSTEM hash %s != %s"
                        % (prompt_hash(), EXPECTED_PROMPT_HASH))
    if dict(JUDGE_CONFIG) != EXPECTED_JUDGE_CONFIG:
        problems.append("JUDGE_CONFIG %r != %r"
                        % (dict(JUDGE_CONFIG), EXPECTED_JUDGE_CONFIG))
    if JUDGE_MODELS.get(V1_KEY) != LEGACY_MODEL:
        problems.append("JUDGE_MODELS[%r] is %r, the stored v1 scores used %r"
                        % (V1_KEY, JUDGE_MODELS.get(V1_KEY), LEGACY_MODEL))
    if problems:
        raise SystemExit("judge config drifted, refusing to run:\n  "
                         + "\n  ".join(problems))


def judge_view_hash(session):
    """Hash of exactly what judge_session sends: the filled system prompt and
    the formatted transcript, user turns included. Two copies of a session
    with the same judge_view_hash are the same judging task."""
    system = multiturn.SESSION_JUDGE_SYSTEM % {
        "character_name": session["character_name"],
        "user_name": session["user_name"],
        "num_turns": session["num_turns"],
    }
    body = "".join("\n**%s** (turn %d):\n%s\n" % (m["name"], m["turn"], m["content"])
                   for m in session["dialogue"])
    return hashlib.sha256((system + "\x1e" + body).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- corpus

def _sources(results_dir=RESULTS_DIR):
    """Newest first, the order every consumer uses (transcript_hash._sources)."""
    out = sorted(glob.glob(str(Path(results_dir) / "craft_baseline_*.json")),
                 reverse=True)
    merged = Path(results_dir) / "multiturn_merged_all_v2.json"
    if merged.exists():
        out.append(str(merged))
    return out


def _sid(s):
    return "%s::%s" % (s["test_model"], s["seed_id"])


def stored_v1_overall(session):
    """The stored Sonnet 4 overall on this copy, or None."""
    j = (session.get("judges") or {}).get(V1_KEY)
    if not j:
        return None
    sc = j.get("scores") or {}
    if sc.get("parse_error"):
        return None
    ov = _num(sc.get("overall"))
    return ov


def load_corpus(results_dir=RESULTS_DIR, v2_file=V2_FILE):
    """The round-4 craft corpus as session_judge_v2.jsonl defines it.

    Returns {sid: entry}, entry = {session, src, transcript_hash, view_hash,
    v1 (stored overall on an identical judging task, or None), v1_src,
    v1_judge_model}. Newest source wins for the transcript; a stored v1 score
    counts only if it was given on a copy with the same judge_view_hash.
    """
    ids = [r["session_id"] for r in read_rows(v2_file)]
    canon, v1_copies = {}, {}
    for src in _sources(results_dir):
        with open(src) as fh:
            sessions = json.load(fh)["sessions"]
        for s in sessions:
            if "error" in s or "dialogue" not in s:
                continue
            sid = _sid(s)
            ov = stored_v1_overall(s)
            if ov is not None:
                v1_copies.setdefault(sid, []).append(
                    (judge_view_hash(s), ov, os.path.basename(src),
                     s["judges"][V1_KEY].get("model")))
            if sid not in canon:
                canon[sid] = (s, os.path.basename(src))
    corpus, missing = {}, []
    for sid in ids:
        if sid not in canon:
            missing.append(sid)
            continue
        s, src = canon[sid]
        vh = judge_view_hash(s)
        match = [c for c in v1_copies.get(sid, []) if c[0] == vh]
        corpus[sid] = dict(session=s, src=src, transcript_hash=transcript_hash(s),
                           view_hash=vh,
                           v1=match[0][1] if match else None,
                           v1_src=match[0][2] if match else None,
                           v1_judge_model=match[0][3] if match else None)
    if missing:
        raise SystemExit("%d session(s) in %s have no transcript on disk: %s"
                         % (len(missing), v2_file, missing[:5]))
    return corpus


# ---------------------------------------------------------------- rows

def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def _flatten(block):
    """{"S.1_x": {"score": 4, "rationale": ".."}} -> ({"S.1_x": 4.0}, {"S.1_x": ".."})"""
    scores, rats = {}, {}
    for k, v in (block or {}).items():
        if isinstance(v, dict):
            scores[k] = _num(v.get("score"))
            if v.get("rationale"):
                rats[k] = v["rationale"]
        else:
            scores[k] = _num(v)
    return scores, rats


def build_row(session_id, entry, judged, purpose, attempts):
    """One output row from a judge_session() result (plus the captured raw)."""
    s = entry["session"]
    sc = judged.get("scores") or {}
    usage = judged.get("usage") or {}
    overall = _num(sc.get("overall"))
    ok = (isinstance(sc, dict) and not sc.get("parse_error")
          and overall is not None)
    sess_dims, r1 = _flatten(sc.get("session_dimensions") if ok else None)
    std_dims, r2 = _flatten(sc.get("standard_dimensions") if ok else None)
    extras = {}
    if ok:
        sd = sc.get("session_dimensions") or {}
        for k, field in (("S.5_agency_respect_session", "violation_count"),
                         ("S.6_temporal_reasoning", "contradictions")):
            if isinstance(sd.get(k), dict) and field in sd[k]:
                extras["%s.%s" % (k, field)] = sd[k][field]
    row = {
        "session_id": session_id,
        "model": s["test_model"],
        "seed": s["seed_id"],
        "transcript_hash": entry["transcript_hash"],
        "judge_view_hash": entry["view_hash"],
        "judge": JUDGE_LABEL,
        "judge_model_requested": LEGACY_MODEL,
        "judge_model_id": judged.get("model"),
        "provider": judged.get("provider"),
        "prompt_hash": prompt_hash(),
        "temperature": JUDGE_CONFIG["temperature"],
        "max_tokens": JUDGE_CONFIG["max_tokens"],
        "overall": overall if ok else None,
        "session_dimensions": sess_dims,
        "standard_dimensions": std_dims,
        "quality_trajectory": (sc.get("quality_trajectory") or {}) if ok else {},
        "rationales": dict(r1, **r2),
        "overall_notes": sc.get("overall_notes") if ok else None,
        "extras": extras,
        "raw_parse_ok": bool(ok),
        "attempts": attempts,
        "usage": {k: usage.get(k) for k in ("prompt_tokens", "completion_tokens", "cost")},
        "source_file": entry["src"],
        "purpose": purpose,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if not ok:
        row["raw_content"] = (sc.get("raw_content") if isinstance(sc, dict) else None) \
            or json.dumps(sc)[:20000]
    return row


def read_rows(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def done_keys(path):
    """(session_id, transcript_hash) pairs already in the output file."""
    return {(r["session_id"], r.get("transcript_hash")) for r in read_rows(path)}


def select_work(corpus, out_path, sessions=None, include_judged=False):
    """Sessions to judge now: in `sessions` (default: the whole corpus), not
    already carrying a stored v1 on this transcript (unless include_judged),
    and not already in out_path with the current transcript_hash."""
    done = done_keys(out_path)
    ids = sessions if sessions is not None else sorted(corpus)
    unknown = [sid for sid in ids if sid not in corpus]
    if unknown:
        raise SystemExit("not in the corpus: %s" % unknown[:5])
    work, skipped_done, skipped_v1 = [], 0, 0
    for sid in ids:
        e = corpus[sid]
        if not include_judged and e["v1"] is not None:
            skipped_v1 += 1
            continue
        if (sid, e["transcript_hash"]) in done:
            skipped_done += 1
            continue
        work.append(sid)
    return work, skipped_done, skipped_v1


# ---------------------------------------------------------------- calling

_tls = threading.local()


def _capturing_chat_completion(*a, **kw):
    """api.chat_completion, keeping the raw response for this thread so the
    provider can be recorded. judge_session drops `raw`; the request itself
    is untouched."""
    res = api.chat_completion(*a, **kw)
    _tls.raw = res.get("raw") or {}
    return res


def call_judge(session):
    """harness.multiturn.judge_session with the legacy model; adds provider."""
    _tls.raw = {}
    orig = multiturn.chat_completion
    if orig is not _capturing_chat_completion:
        multiturn.chat_completion = _capturing_chat_completion
    judged = multiturn.judge_session(session, LEGACY_MODEL, nsfw=False)
    judged = dict(judged)
    judged["provider"] = (getattr(_tls, "raw", None) or {}).get("provider")
    return judged


def judge_with_retries(entry, judge_fn, parse_retries):
    """(judged, attempts). Re-asks only on a parse failure; transport retries
    live in harness.api."""
    attempts = 0
    judged = None
    total_cost = 0.0
    while True:
        attempts += 1
        judged = judge_fn(entry["session"])
        total_cost += _num((judged.get("usage") or {}).get("cost")) or 0.0
        sc = judged.get("scores") or {}
        ok = not sc.get("parse_error") and _num(sc.get("overall")) is not None
        if ok or attempts > parse_retries:
            break
    judged = dict(judged)
    judged["usage"] = dict(judged.get("usage") or {}, cost=round(total_cost, 6))
    return judged, attempts


def openrouter_credits():
    """(total_credits, total_usage) from OpenRouter, or (None, None)."""
    import httpx
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        return None, None
    try:
        r = httpx.get(CREDITS_URL, headers={"Authorization": "Bearer " + key},
                      timeout=30)
        d = r.json().get("data") or {}
        return float(d["total_credits"]), float(d["total_usage"])
    except Exception as e:                           # noqa: BLE001
        print("  credits check failed: %s" % type(e).__name__, flush=True)
        return None, None


class Spend:
    """Spend since `baseline` (OpenRouter total_usage at the start of the
    whole job), taking the larger of the account's own counter and this
    run's summed usage.cost, since the counter can lag a few seconds."""

    def __init__(self, baseline, start_usage):
        self.baseline = baseline if baseline is not None else start_usage
        self.start_usage = start_usage
        self.local = 0.0
        self.n = 0
        self.lock = threading.Lock()
        self.last_account = start_usage

    def add(self, cost):
        with self.lock:
            self.local += cost or 0.0
            self.n += 1

    def spent(self, account_usage=None):
        if account_usage is not None:
            self.last_account = account_usage
        prior = ((self.start_usage - self.baseline)
                 if self.start_usage is not None and self.baseline is not None else 0.0)
        via_local = prior + self.local
        via_account = ((self.last_account - self.baseline)
                       if self.last_account is not None and self.baseline is not None
                       else 0.0)
        return max(via_local, via_account)

    def per_session(self):
        return max(self.local / self.n if self.n else 0.0, DEFAULT_COST_PER_SESSION)


def plan_chunk(spend, cap, want, account_usage=None):
    """How many of the next `want` sessions fit under the cap."""
    left = cap - spend.spent(account_usage)
    per = spend.per_session() * COST_SAFETY
    return max(0, min(want, int(left // per)))


def run(corpus, work, out_path, purpose, concurrency, cap, baseline,
        check_every, parse_retries, judge_fn=call_judge, credits_fn=openrouter_credits):
    """Judge `work` into out_path. Returns a summary dict."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    credits0, usage0 = credits_fn()
    spend = Spend(baseline, usage0)
    print("start: credit left %s, spent since baseline $%.4f, cap $%.2f"
          % ("?" if credits0 is None else "$%.2f" % (credits0 - usage0),
             spend.spent(), cap), flush=True)
    write_lock = threading.Lock()
    failures, parse_fail, written = [], [], 0
    stop_reason = None

    def one(sid):
        entry = corpus[sid]
        try:
            judged, attempts = judge_with_retries(entry, judge_fn, parse_retries)
        except api.AccountError as e:
            return sid, None, "account: %s" % e
        except Exception as e:                       # noqa: BLE001
            return sid, None, "%s: %s" % (type(e).__name__, str(e)[:300])
        row = build_row(sid, entry, judged, purpose, attempts)
        spend.add((row["usage"] or {}).get("cost"))
        with write_lock:
            with open(out_path, "a") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        return sid, row, None

    api.set_min_interval(REQUEST_DELAY_SECONDS / max(1, concurrency))
    i = 0
    account_usage = usage0
    while i < len(work):
        n = plan_chunk(spend, cap, min(check_every, len(work) - i), account_usage)
        if n == 0:
            stop_reason = ("cap: spent $%.4f of $%.2f, next session projected "
                           "$%.4f" % (spend.spent(), cap,
                                      spend.per_session() * COST_SAFETY))
            break
        chunk = work[i:i + n]
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            for sid, row, err in ex.map(one, chunk):
                if err:
                    failures.append((sid, err))
                    print("  FAIL %-48s %s" % (sid, err[:120]), flush=True)
                    if err.startswith("account:"):
                        stop_reason = err
                else:
                    written += 1
                    if not row["raw_parse_ok"]:
                        parse_fail.append(sid)
        i += n
        _, account_usage = credits_fn()
        print("[%4d/%4d] written %d, failed %d, parse-fail %d, spent $%.4f "
              "(this run $%.4f, $%.4f/session)"
              % (i, len(work), written, len(failures), len(parse_fail),
                 spend.spent(account_usage), spend.local, spend.per_session()),
              flush=True)
        if stop_reason:
            break
    credits1, usage1 = credits_fn()
    return dict(requested=len(work), attempted=i, written=written,
                failures=failures, parse_failures=parse_fail,
                cost_this_run_local=round(spend.local, 4),
                account_usage_start=usage0, account_usage_end=usage1,
                account_delta=(None if usage0 is None or usage1 is None
                               else round(usage1 - usage0, 4)),
                spent_since_baseline=round(spend.spent(usage1), 4),
                stop_reason=stop_reason)


# ---------------------------------------------------------------- verify

def verify(corpus, out_path):
    """Every corpus session without a stored v1 on its transcript has exactly
    one row here with the current hashes."""
    rows = read_rows(out_path)
    by = {}
    for r in rows:
        by.setdefault(r["session_id"], []).append(r)
    targets = sorted(sid for sid, e in corpus.items() if e["v1"] is None)
    missing, dup, stale, parse_fail = [], [], [], []
    for sid in targets:
        e = corpus[sid]
        rs = by.get(sid, [])
        cur = [r for r in rs if r.get("transcript_hash") == e["transcript_hash"]
               and r.get("judge_view_hash") == e["view_hash"]]
        if not cur:
            (stale if rs else missing).append(sid)
        elif len(cur) > 1:
            dup.append(sid)
        if cur and not cur[0].get("raw_parse_ok"):
            parse_fail.append(sid)
    extra = sorted(set(by) - set(targets))
    return dict(targets=len(targets), rows=len(rows), missing=missing,
                duplicates=dup, stale=stale, parse_failures=parse_fail,
                rows_outside_targets=extra,
                ok=not (missing or dup or stale))


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--sessions-file", help="one session_id per line")
    ap.add_argument("--include-judged", action="store_true",
                    help="also judge sessions that already carry a stored v1 "
                         "score on this transcript (drift checks)")
    ap.add_argument("--purpose", default="backfill")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--cap-usd", type=float, default=30.0)
    ap.add_argument("--usage-baseline", type=float,
                    help="OpenRouter total_usage when the whole job began; "
                         "the cap counts from here (default: this run's start)")
    ap.add_argument("--check-every", type=int, default=100)
    ap.add_argument("--parse-retries", type=int, default=1)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--redo-failed", action="store_true",
                    help="drop raw_parse_ok=false rows for the selected "
                         "sessions and judge them again")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--summary-json", help="write the run summary here")
    args = ap.parse_args(argv)

    check_config()
    corpus = load_corpus()
    if args.verify:
        v = verify(corpus, args.out)
        print(json.dumps({k: (v[k] if not isinstance(v[k], list) or len(v[k]) < 40
                              else "%d items" % len(v[k])) for k in v}, indent=1))
        return 0 if v["ok"] else 1

    sessions = None
    if args.sessions_file:
        with open(args.sessions_file) as fh:
            sessions = [l.strip() for l in fh if l.strip()]
    if args.redo_failed:
        # --dry-run is honoured at line ~569, AFTER this block, so
        # --redo-failed --dry-run used to rewrite the output file and drop
        # rows before announcing it would do nothing. A dry run must not be
        # able to lose data: that is the one promise the flag makes.
        if args.dry_run:
            rows = read_rows(args.out)
            pick = set(sessions) if sessions is not None else None
            keep = [r for r in rows if r.get("raw_parse_ok")
                    or (pick is not None and r["session_id"] not in pick)]
            print("[dry-run] --redo-failed would drop %d parse-failure row(s) "
                  "from %s" % (len(rows) - len(keep), args.out))
        else:
            rows = read_rows(args.out)
            pick = set(sessions) if sessions is not None else None
            keep = [r for r in rows if r.get("raw_parse_ok")
                    or (pick is not None and r["session_id"] not in pick)]
            if len(keep) != len(rows):
                tmp = Path(args.out).with_suffix(".jsonl.tmp")
                with open(tmp, "w") as fh:
                    for r in keep:
                        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                tmp.replace(args.out)
                print("dropped %d parse-failure row(s)" % (len(rows) - len(keep)))
    work, skipped_done, skipped_v1 = select_work(
        corpus, args.out, sessions, include_judged=args.include_judged)
    if args.limit:
        work = work[:args.limit]
    print("corpus %d | stored v1 on current transcript %d | already in %s %d"
          " | to judge now %d"
          % (len(corpus), sum(1 for e in corpus.values() if e["v1"] is not None),
             Path(args.out).name, skipped_done, len(work)))
    print("judge %s | prompt %s | %r | purpose %s"
          % (LEGACY_MODEL, prompt_hash(), dict(JUDGE_CONFIG), args.purpose))
    if args.dry_run or not work:
        return 0
    summary = run(corpus, work, args.out, args.purpose, args.concurrency,
                  args.cap_usd, args.usage_baseline, args.check_every,
                  args.parse_retries)
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("failures", "parse_failures")}, indent=1))
    if summary["failures"]:
        print("failures:")
        for sid, err in summary["failures"]:
            print("  %s  %s" % (sid, err[:200]))
    if summary["parse_failures"]:
        print("parse failures: %s" % summary["parse_failures"])
    if args.summary_json:
        with open(args.summary_json, "w") as fh:
            json.dump(summary, fh, indent=1)
    return 0 if not summary["failures"] and not summary["stop_reason"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
