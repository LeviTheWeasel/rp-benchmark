"""Round-4 Track B text: kept on disk, out of the public repo, rejoined on load.

docs/ROUND4_DESIGN.md sec 9: no Track B transcript is published, B-hard or
B-policy. A published artifact carries the label, a truncated evidence span and
the judge rationale only. Until 2026-09-25 the results files carried the full
text, so it went into the repo with them.

Every results file that holds Track B text is now two files:

  results/r4_full_X.json                          public, tracked
  results/r4_trackb_transcripts__r4_full_X.json   private, gitignored

The public file keeps everything the leaderboard is computed from: labels,
rungs, turns, votes, confidences, is_control, content_hits, disputed. What it
loses, for Track B only:

  sessions      `dialogue` is replaced by a pointer ("transcript": "private",
                "private_file", "transcript_hash", "dialogue_sha256"). Label
                text over EVIDENCE_CAP chars is cut on a word boundary and
                flagged "<field>_truncated": true.
  Jev rows      `reply` is replaced by "reply_sha256" + "private_file".
                `ask` and `desc` stay: they are the scripted probe and the
                seed's trap text, both already public in
                hf_dataset/_source/adversarial_seeds_r4_track_b.json.
  rung batches  (results/judge_raw/r4_rung_batches) `ai_reply` is replaced by
                "private_file"; `reply_sha` was already there. Verdict
                evidence is capped as above.

The private file for results/<rel path>.json is always
results/r4_trackb_transcripts__<rel path with / as __>.json, so the one ignore
rule covers every kind. Loading rejoins it exactly, and the hash is checked:
a rejoined transcript is byte-identical to the one that was split off, or the
load fails. When the private file is absent (a fresh clone), a load that only
needs labels works on the public file; anything that needs the text fails
loudly through PrivateTextMissing instead of seeing an empty transcript.

Saving always writes the split form, so the next run cannot put the text back.
Writes are atomic (temp file in the same directory, then os.replace): other
processes read these files while they are being rewritten.
"""
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
try:
    from transcript_hash import transcript_hash
except ImportError:  # imported from outside the repo root
    sys.path.insert(0, str(ROOT))
    from transcript_hash import transcript_hash

TRACK_B = ("B-hard", "B-policy")
PRIVATE_PREFIX = "r4_trackb_transcripts__"
# Sec 9's "truncated evidence span". 866 Track B labels existed when this was
# set; 53 of them quoted more than this.
EVIDENCE_CAP = 160
# Label fields that are enums or ids, never quoted text.
_NOT_TEXT = {"label", "route", "item_id"}
_POLICY = ("Track B text, internal only (docs/ROUND4_DESIGN.md sec 9). "
           "Gitignored. The public file next to it holds the labels.")


class PrivateTextMissing(RuntimeError):
    """A caller needs Track B text that is not on this disk."""


def is_track_b(track):
    return track in TRACK_B


# ---- paths and io ----------------------------------------------------------

def _results_root(path):
    for parent in path.parents:
        if parent.name == "results":
            return parent
    return None


def private_path(public_path):
    """Where the private companion of a public results file lives."""
    p = Path(public_path).absolute()
    root = _results_root(p)
    if root is None:
        return p.parent / (PRIVATE_PREFIX + p.stem + ".json")
    rel = p.relative_to(root)
    flat = "__".join(rel.parts[:-1] + (rel.name[:-len(".json")]
                                        if rel.name.endswith(".json")
                                        else rel.name,))
    return root / (PRIVATE_PREFIX + flat + ".json")


def _detect_indent(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            f.readline()
            line = f.readline()
    except OSError:
        return default
    n = len(line) - len(line.lstrip(" "))
    return n or default


def atomic_write_json(path, obj, indent=2, mode=None):
    """Write-then-rename in the target's own directory."""
    path = Path(path)
    text = json.dumps(obj, indent=indent, ensure_ascii=False)
    if mode is None:
        try:
            mode = path.stat().st_mode & 0o777
        except OSError:
            mode = 0o644
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix="." + path.name + ".",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_private(pp):
    if not pp.exists():
        return None
    with open(pp, encoding="utf-8") as f:
        return json.load(f)


def _write_private(pp, public_path, kind, payload):
    doc = {"type": "r4_trackb_private", "kind": kind,
           "public_file": Path(public_path).name, "policy": _POLICY}
    doc.update(payload)
    atomic_write_json(pp, doc, indent=1, mode=0o600)


def _missing(public_path, pp, what):
    return PrivateTextMissing(
        "%s: %s is not in the public file (docs/ROUND4_DESIGN.md sec 9) and "
        "its private companion %s is %s. That file is gitignored and exists "
        "only on the machine that generated the run. Nothing was classified "
        "or scored." % (Path(public_path).name, what, pp.name,
                        "missing" if not pp.exists() else "incomplete"))


# ---- label text ------------------------------------------------------------

def truncate_span(text, cap=EVIDENCE_CAP):
    """A verbatim prefix of at most `cap` chars, cut on a word boundary."""
    if len(text) <= cap:
        return text
    head = text[:cap + 1]
    cut = max((m.start() for m in re.finditer(r"\s", head)), default=-1)
    return (text[:cut] if cut >= cap // 2 else text[:cap]).rstrip()


def _cap_record(rec):
    """(public record, {field: full text}) with long text fields capped."""
    full = {k: v for k, v in rec.items()
            if k not in _NOT_TEXT and not k.endswith("_truncated")
            and isinstance(v, str) and len(v) > EVIDENCE_CAP}
    if not full:
        return rec, {}
    out = {}
    for k, v in rec.items():
        out[k] = truncate_span(v) if k in full else v
        if k in full:
            out[k + "_truncated"] = True
    return out, full


def _restore_record(rec, full):
    if not full:
        return rec
    ok = {k for k, v in full.items()
          if rec.get(k + "_truncated") and rec.get(k) == truncate_span(v)}
    if not ok:
        return rec
    return {k: (full[k] if k in ok else v) for k, v in rec.items()
            if not (k.endswith("_truncated") and k[:-len("_truncated")] in ok)}


def _dialogue_sha(dialogue):
    return hashlib.sha256(json.dumps(dialogue, ensure_ascii=False,
                                     sort_keys=True).encode("utf-8")).hexdigest()


def _reply_sha(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


# ---- session files: results/r4_full_*.json, results/r4_pilot_*.json --------

def _split_session(s, private_name):
    """(public session, dialogue_sha256 or None, private entry or None)."""
    has_text = "dialogue" in s
    sha = _dialogue_sha(s["dialogue"]) if has_text else s.get("dialogue_sha256")
    pub, texts = {}, {}
    for k, v in s.items():
        if k == "dialogue":
            pub["transcript"] = "private"
            pub["private_file"] = private_name
            pub["transcript_hash"] = transcript_hash(s)
            pub["dialogue_sha256"] = sha
        elif k == "rung_labels" and isinstance(v, list):
            labels = []
            for i, r in enumerate(v):
                r2, full = _cap_record(r)
                labels.append(r2)
                if full:
                    texts[str(i)] = full
            pub[k] = labels
        else:
            pub[k] = v
    entry = None
    if has_text or texts:
        entry = {"test_model": s.get("test_model"), "seed_id": s.get("seed_id"),
                 "track": s.get("track")}
        if has_text:
            entry["dialogue"] = s["dialogue"]
        if texts:
            entry["rung_label_text"] = texts
    return pub, sha, entry


def split_r4(data, public_path):
    """(public data, {dialogue_sha256: private entry}) for one results file."""
    name = private_path(public_path).name
    sessions, entries = [], {}
    for s in data.get("sessions") or []:
        if is_track_b(s.get("track")) and (
                "dialogue" in s or s.get("transcript") == "private"):
            pub, sha, entry = _split_session(s, name)
            if entry is not None:
                if sha is None:
                    raise ValueError("Track B session %s x %s has capped label "
                                     "text but no transcript pointer"
                                     % (s.get("test_model"), s.get("seed_id")))
                entries[sha] = entry
            sessions.append(pub)
        else:
            sessions.append(s)
    public = dict(data)
    if "sessions" in public:
        public["sessions"] = sessions
    return public, entries


def save_r4(path, data, indent=None):
    """Write a session results file in split form: public + private companion.

    Existing private entries are kept and updated, never dropped: a session
    loaded without its text (companion absent) passes through as a pointer, and
    whatever the companion held for it stays there.
    """
    path = Path(path)
    if indent is None:
        indent = _detect_indent(path, 2)
    pp = private_path(path)
    public, entries = split_r4(data, path)
    old = _read_private(pp)
    merged = dict((old or {}).get("sessions") or {})
    for sha, e in entries.items():
        # label text always follows the labels being written now; the
        # transcript is carried over when this save only had the pointer
        prev = merged.get(sha) or {}
        e = dict(e)
        if "dialogue" not in e and "dialogue" in prev:
            e["dialogue"] = prev["dialogue"]
        merged[sha] = e
    if merged or old is not None:
        # private first: a public pointer must never name an entry that is
        # not on disk yet
        _write_private(pp, path, "sessions", {"sessions": merged})
    atomic_write_json(path, public, indent=indent)


def _rejoin_session(pub, entries, need_text, public_path, pp):
    sha = pub.get("dialogue_sha256")
    e = (entries or {}).get(sha)
    if e is None or "dialogue" not in e:
        if need_text:
            raise _missing(public_path, pp, "the transcript of %s x %s (%s)"
                           % (pub.get("test_model"), pub.get("seed_id"),
                              pub.get("track")))
        return pub
    if (_dialogue_sha(e["dialogue"]) != sha
            or (e.get("test_model"), e.get("seed_id"), e.get("track"))
            != (pub.get("test_model"), pub.get("seed_id"), pub.get("track"))):
        raise PrivateTextMissing(
            "%s: private entry for %s x %s does not match its public pointer "
            "(hash or key differs). Refusing to attach text to the wrong "
            "session." % (Path(public_path).name, pub.get("test_model"),
                          pub.get("seed_id")))
    texts = e.get("rung_label_text") or {}
    out = {}
    for k, v in pub.items():
        if k == "transcript":
            out["dialogue"] = e["dialogue"]
        elif k in ("private_file", "transcript_hash", "dialogue_sha256"):
            continue
        elif k == "rung_labels" and isinstance(v, list):
            out[k] = [_restore_record(r, texts.get(str(i)))
                      for i, r in enumerate(v)]
        else:
            out[k] = v
    return out


def load_r4(path, need_text=False):
    """Load a session results file, rejoining Track B text when it is on disk.

    need_text=True: raise PrivateTextMissing unless every Track B transcript
    in the file could be rejoined. need_text=False: sessions whose text is not
    on disk come back as pointers (no `dialogue` key); use dialogue_of() to
    reach a transcript, which raises for those.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    sessions = data.get("sessions") or []
    if not any(s.get("transcript") == "private" for s in sessions):
        return data
    pp = private_path(path)
    doc = _read_private(pp)
    entries = doc.get("sessions") if doc else None
    if entries is None and need_text:
        raise _missing(path, pp, "Track B text")
    data["sessions"] = [
        _rejoin_session(s, entries, need_text, path, pp)
        if s.get("transcript") == "private" else s for s in sessions]
    return data


def dialogue_of(session):
    """A session's transcript, or a clear error when it is private and absent."""
    if "dialogue" in session:
        return session["dialogue"]
    if session.get("transcript") == "private":
        raise PrivateTextMissing(
            "%s x %s (%s): the transcript is Track B text kept in %s, which "
            "was not on disk when this file was loaded (docs/ROUND4_DESIGN.md "
            "sec 9). Nothing was classified or scored."
            % (session.get("test_model"), session.get("seed_id"),
               session.get("track"), session.get("private_file")))
    raise KeyError("dialogue")


# ---- Jev rows: results/jev_vs_sonnet_r4*.json ------------------------------

def _row_key(r, sha):
    return "%s::%s::%s::t%s::%s" % (r.get("track"), r.get("model"),
                                     r.get("seed"), r.get("turn"), sha)


def save_jev(path, res, indent=None):
    """Write a Jev-vs-Sonnet file with Track B replies split off."""
    path = Path(path)
    if indent is None:
        indent = _detect_indent(path, 2)
    pp = private_path(path)
    old = _read_private(pp)
    rows_priv = dict((old or {}).get("rows") or {})
    rows = []
    for r in res.get("rows") or []:
        if is_track_b(r.get("track")) and "reply" in r:
            sha = _reply_sha(r["reply"])
            pub = {}
            for k, v in r.items():
                if k == "reply":
                    pub["reply_sha256"] = sha
                    pub["private_file"] = pp.name
                else:
                    pub[k] = v
            rows_priv[_row_key(r, sha)] = {
                "track": r.get("track"), "model": r.get("model"),
                "seed": r.get("seed"), "turn": r.get("turn"),
                "wave": res.get("wave"), "reply": r["reply"]}
            rows.append(pub)
        else:
            rows.append(r)
    public = dict(res)
    if "rows" in public:
        public["rows"] = rows
    if rows_priv or old is not None:
        _write_private(pp, path, "jev_rows", {"wave": res.get("wave"),
                                              "rows": rows_priv})
    atomic_write_json(path, public, indent=indent)


def load_jev(path, need_text=False):
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        res = json.load(f)
    rows = res.get("rows") or []
    if not any("reply_sha256" in r for r in rows):
        return res
    pp = private_path(path)
    doc = _read_private(pp)
    priv = doc.get("rows") if doc else None
    out = []
    for r in rows:
        if "reply_sha256" not in r:
            out.append(r)
            continue
        e = (priv or {}).get(_row_key(r, r["reply_sha256"]))
        if e is None or _reply_sha(e["reply"]) != r["reply_sha256"]:
            if need_text:
                raise _missing(path, pp, "the reply for %s x %s turn %s"
                               % (r.get("model"), r.get("seed"), r.get("turn")))
            out.append(r)
            continue
        out.append({("reply" if k == "reply_sha256" else k):
                    (e["reply"] if k == "reply_sha256" else v)
                    for k, v in r.items() if k != "private_file"})
    res["rows"] = out
    return res


# ---- rung batches: results/judge_raw/r4_rung_batches/ ----------------------

def _seed_tracks():
    from harness.multiturn import load_seeds
    return {s["id"]: s["track"] for s in load_seeds(round4="all")}


def save_batch(path, rows, indent=1, tracks=None):
    """Archive a rung batch (items) or its verdicts (*.out.json), split.

    Items: Track B `ai_reply` goes private. Verdicts: Track B text fields are
    capped at EVIDENCE_CAP, the full quote goes private. A verdict row names
    its exchange only by item_id (model::seed::tN), so its track is read from
    the seed files.
    """
    path = Path(path)
    pp = private_path(path)
    old = _read_private(pp)
    priv = dict((old or {}).get("items") or {})
    tracks = tracks if tracks is not None else _seed_tracks()
    out = []
    for r in rows:
        track = r.get("track")
        if track is None and r.get("item_id"):
            parts = r["item_id"].split("::")
            track = tracks.get(parts[1]) if len(parts) == 3 else None
        if not is_track_b(track):
            out.append(r)
            continue
        if "ai_reply" in r:
            sha = r.get("reply_sha") or _reply_sha(r["ai_reply"])[:12]
            pub = {}
            for k, v in r.items():
                if k == "ai_reply":
                    pub["private_file"] = pp.name
                else:
                    pub[k] = v
            if "reply_sha" not in pub:
                pub["reply_sha"] = sha
            priv["%s::%s" % (r["item_id"], sha)] = {"ai_reply": r["ai_reply"]}
            out.append(pub)
        else:
            pub, full = _cap_record(r)
            if full:
                priv["%s::verdict" % r["item_id"]] = full
            out.append(pub)
    if priv or old is not None:
        _write_private(pp, path, "rung_batch", {"items": priv})
    atomic_write_json(path, out, indent=indent)


def load_batch(path, need_text=False):
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    pp = private_path(path)
    doc = _read_private(pp)
    priv = (doc or {}).get("items") or {}
    out = []
    for r in rows:
        if r.get("private_file") and "ai_reply" not in r:
            e = priv.get("%s::%s" % (r["item_id"], r.get("reply_sha")))
            if e is None or _reply_sha(e["ai_reply"])[:12] != r.get("reply_sha"):
                if need_text:
                    raise _missing(path, pp, "the reply for %s" % r["item_id"])
                out.append(r)
                continue
            out.append({("ai_reply" if k == "private_file" else k):
                        (e["ai_reply"] if k == "private_file" else v)
                        for k, v in r.items()})
        elif any(k.endswith("_truncated") for k in r):
            out.append(_restore_record(r, priv.get("%s::verdict" % r.get("item_id"))))
        else:
            out.append(r)
    return out
