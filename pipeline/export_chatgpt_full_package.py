#!/usr/bin/env python3
"""Build the full-corpus blind package for a second judge family (ChatGPT),
to be run by hand, blind, in Codex on a ChatGPT subscription (where the full
pass, results/judge_full_chatgpt, ran; ROUND4_DESIGN 24).

The Sonnet 5 session judge scored every current craft session. The external
arms so far covered samples: 120 stratified sessions (judge_round2_*) and a
93-session increment (judge_inc1_*). This package covers everything else, so
the SUBJECTIVE block can carry a measured second family on every session
instead of one sampled offset.

What goes in:
  - every session in results/session_judge_v2.jsonl, taken from the same
    newest-wins source order the session judge used, failing closed if the
    two disagree on the session set or on any recorded transcript hash;
  - minus the sessions an earlier BLIND ChatGPT pass already scored on the
    same text (hash still matches, row still validates). Those rows are
    reused, not re-asked. The round-1 package is not reused: its ids leaked
    the model name (ROUND4_DESIGN 15c), and round 2 re-judged the same
    sessions blind;
  - plus a small BRIDGE: a seeded sample of those reusable sessions sent out
    again under fresh ids. ROUND4_DESIGN 18c found that how a judge is invoked
    moved Gemini by 0.39, as much as the vendor gap. The earlier ChatGPT rows
    came from other runs with other raters (each a coordinator handing parts
    to three clean-context raters; where they ran is not recorded); the
    bridge measures whether rows from this run can be pooled with them,
    instead of assuming it.

Blinding, as fixed after round 1 (ROUND4_DESIGN 15c, 15f):
  - opaque ids with a fresh prefix ("f"), the key held in the manifest on our
    side and never in a zip;
  - shuffled with a fixed seed BEFORE parts and chunks are cut, so no chunk
    or part groups by vendor;
  - every transcript is scanned for model and vendor names, model ids,
    self-identification and system-prompt echoes. Unambiguous tells are
    redacted in place; ambiguous words (a character called Sol, a "magnum
    opus") are counted and reported, not touched;
  - no hash, model name or scenario name travels in a zip.

Chunking: the earlier ChatGPT passes each finished 12 parts of 10 sessions
(about 2.8 MB) in one conversation and reported no limit. Chunks are cut to
at most that: <= 120 sessions and <= 3.0 MB, parts of 10 inside.

Usage (from the benchmark checkout):
    python pipeline/export_chatgpt_full_package.py            # build
    python pipeline/export_chatgpt_full_package.py --force    # rebuild (new ids!)
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import math
import random
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import harness.config as config
import harness.multiturn as multiturn
from lib.external_judge_schema import validate_row
from lib.transcript_hash import transcript_hash

PUBLIC_DIR = Path.home() / "Documents" / "rp-bench-chatgpt-judge"
MANIFEST_DIR = Path("results/judge_full_chatgpt")
JUDGE_FILE = Path("results/session_judge_v2.jsonl")
ID_PREFIX = "f"
PART = 10
# Earlier blind ChatGPT passes whose rows can be reused, oldest first. A
# session covered by two of them takes the later one.
PRIOR = (("results/judge_round2_chatgpt", "external_blind_pass"),
         ("results/judge_inc1_chatgpt", "external_blind_pass"))

# ---------------------------------------------------------------- blinding --
# Unambiguous tells: no ordinary English meaning, so any hit is a leak and is
# redacted. Built from the roster below plus the families' public names.
_STRICT_WORDS = [
    r"\banthropic\b", r"\bopen ?ai\b", r"\bchat ?gpt\b", r"\bgpt[- ]?\d[\w.\-]*",
    r"\bgpt\b", r"\bdeep ?seek[\w.\-]*", r"\bqwen[\w.\-]*", r"\balibaba cloud\b",
    r"\btongyi\b", r"\bmoonshot ai\b", r"\bkimi[- ]?k\d[\w.\-]*", r"\bzhipu\b",
    r"\bchatglm[\w.\-]*", r"\bglm[- ]?\d[\w.\-]*", r"\bx\.ai\b", r"\bxai\b",
    r"\bminimax[\w.\-]*", r"\bxiaomi\b", r"\btencent\b", r"\bhunyuan\b",
    r"\bsao10k\b", r"\bthedrummer\b", r"\bopenrouter\b", r"\bunslop ?nemo\b",
    r"\bdeepmind\b", r"\bllama[- ]?\d[\w.\-]*",
    r"\bclaude[- ](?:opus|sonnet|haiku|fable)[\w.\-]*(?:[- ]\d+(?:\.\d+)*)?",
    r"\b(?:opus|sonnet|haiku|fable)[- ][45](?:\.\d)?\b",
    r"\bgemini[- ]\d\.\d[\w.\-]*", r"\bgemma[- ]?\d[\w.\-]*", r"\bgrok[- ]\d[\w.\-]*",
    r"\bmistral[- ](?:small|large|medium|nemo|ai)\b", r"\bcommand[- ]a[- ]plus\b",
    r"\bmagnum[- ]v\d", r"\bcydonia[- ]\d", r"\bskyfall[- ]\d", r"\bmuse[- ]spark\b",
    r"\bmercury[- ]2\.5\b", r"\bember[- ]1\b", r"\baion[- ]\d", r"\bhemm?ingway[- ]\d",
    r"\bdolphin[- ]mistral\b", r"\bvenice[- ]edition\b",
    # Case-sensitive, first person only, and no names that are also ordinary
    # given names (Gemma, Kimi): "surprise as Gemma set the plate" is a
    # waitress, not a self-identification.
    r"(?-i:\b(?:I am|I'm|I’m) (?:an? )?(?:Claude|ChatGPT|Gemini|Grok|Llama|"
    r"Qwen|DeepSeek|MiniMax|MiMo|Hunyuan)\b)",
    r"\b(?:made|created|developed|trained|built) by (?:Anthropic|OpenAI|Google|"
    r"DeepMind|DeepSeek|Alibaba|Moonshot|Zhipu|xAI|Meta AI|Mistral AI|Cohere|"
    r"Xiaomi|MiniMax|Tencent|Inception|Fireworks)\b",
]
# Ordinary words that are also product or vendor names. Counted per vendor and
# reported; a word that concentrates in its own vendor's sessions is a tell,
# one spread across vendors is the scenario talking.
_AMBIGUOUS_WORDS = [
    "claude", "gemini", "gemma", "llama", "mistral", "grok", "cohere", "meta",
    "google", "command", "cydonia", "skyfall", "magnum", "dolphin", "venice",
    "aion", "ember", "hemingway", "hemmingway", "fable", "opus", "sonnet",
    "haiku", "astra", "luna", "sol", "mercury", "muse", "spark", "fireworks",
    "inception", "nova", "hermes", "mimo", "kimi", "anthracite", "euryale",
    "lunaris", "unslop", "drummer",
]
# Assistant voice and harness residue. Reported, never redacted: a character
# break or a leaked reasoning tag is part of the performance being judged,
# and the Sonnet pass saw it too.
_SELF_ID = [
    r"as an ai\b", r"\bi(?:'m| am) an ai\b", r"language model", r"\bai assistant\b",
    r"large language model",
    r"trained (?:by|on)\b", r"my training", r"knowledge cut-?off",
    r"content polic", r"usage polic",
    r"i can(?:'|’)?t (?:help (?:you )?with|assist|continue (?:this|the) (?:role|story|scene))",
    r"i cannot (?:help (?:you )?with|assist|continue this)", r"i(?:'m| am) not able to (?:help|assist|continue)",
    r"system prompt", r"<think>", r"</think>", r"<\|", r"\|>", r"\[/?inst\]",
    r"◁/?think▷", r"<start_of_turn>", r"<end_of_turn>", r"</?s>",
    r"you are roleplaying as", r"stay in character at all times",
    r"write in third-person past tense", r"they are controlled by the user",
    r"## your character",
]


def _roster_patterns(provider_ids):
    """Every roster key and provider id in the forms a transcript could carry
    them: claude_opus_4_6, claude-opus-4.6, anthropic/claude-opus-4.6. Taken
    from the config and from the ids the sessions actually recorded, since
    two roster entries have no config id."""
    out = set()
    for key, pid in list(config.TEST_MODELS.items()) + list(provider_ids.items()):
        out.add(re.escape(key))
        if pid:
            out.add(re.escape(pid))
            out.add(re.escape(pid.split("/", 1)[-1]))
    # One boundary check around the whole alternation: a lookbehind on each of
    # ~250 alternatives made the scan take minutes.
    return r"(?<![\w-])(?:%s)(?![\w-])" % "|".join(
        sorted(out, key=len, reverse=True))


def compile_scanners(provider_ids):
    # Exact roster ids first, so "anthropic/claude-opus-4.6" goes as one
    # match instead of "anthropic" plus a stranded "/claude-opus-4.6".
    strict = re.compile("|".join(["(?:%s)" % _roster_patterns(provider_ids)]
                                 + ["(?:%s)" % p for p in _STRICT_WORDS]),
                        re.I)
    ambig = re.compile(r"\b(%s)\b" % "|".join(_AMBIGUOUS_WORDS), re.I)
    self_id = re.compile("|".join("(?:%s)" % p for p in _SELF_ID), re.I)
    return strict, ambig, self_id


REDACTION = "[name removed]"
# Which vendor each ambiguous word would point at, for the concentration check.
OWN_VENDOR = {
    "claude": ("anthropic",), "fable": ("anthropic",), "opus": ("anthropic",),
    "sonnet": ("anthropic",), "haiku": ("anthropic",),
    "gemini": ("google",), "gemma": ("google",), "google": ("google",),
    "astra": ("openai",), "luna": ("openai",), "sol": ("openai",),
    "llama": ("meta-llama", "meta"), "meta": ("meta-llama", "meta"),
    "muse": ("meta",), "spark": ("meta",),
    "mistral": ("mistralai", "cognitivecomputations"), "grok": ("x-ai",),
    "cohere": ("cohere",), "command": ("cohere",),
    "cydonia": ("thedrummer",), "skyfall": ("thedrummer",),
    "unslop": ("thedrummer",), "drummer": ("thedrummer",),
    "magnum": ("anthracite-org",), "anthracite": ("anthracite-org",),
    "dolphin": ("cognitivecomputations",), "venice": ("cognitivecomputations",),
    "aion": ("aion-labs",), "ember": ("fireworks",), "fireworks": ("fireworks",),
    "hemingway": ("remote",), "hemmingway": ("remote",),
    "mercury": ("inception",), "inception": ("inception",),
    "mimo": ("xiaomi",), "kimi": ("moonshotai",),
    "euryale": ("sao10k",), "lunaris": ("sao10k",),
}


# ------------------------------------------------------------------ corpus --
def session_sources():
    """Newest craft run first, then the merged archive: the order every
    consumer in this repo dedupes with, first wins."""
    out = sorted(glob.glob("results/craft_baseline_*.json"), reverse=True)
    out.append("results/multiturn_merged_all_v2.json")
    return [p for p in out if Path(p).exists()]


def load_current():
    sessions, origin = {}, {}
    for src in session_sources():
        for s in json.load(open(src))["sessions"]:
            if "error" in s or "dialogue" not in s:
                continue
            sid = "%s::%s" % (s["test_model"], s["seed_id"])
            if sid in sessions:
                continue
            sessions[sid] = s
            origin[sid] = src
    return sessions, origin


def format_transcript(s):
    """Byte-for-byte the format the Sonnet session judge and the earlier
    external packages used."""
    return "".join("\n**%s** (turn %s):\n%s\n"
                   % (m.get("name"), m.get("turn"), m.get("content") or "")
                   for m in s["dialogue"])


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def reusable_rows(live_hash):
    """Sessions an earlier blind ChatGPT pass scored on the text now on disk,
    with a row that still passes the schema."""
    out = {}
    for pkg, sub in PRIOR:
        man = json.load(open(Path(pkg) / "_manifest.json"))
        rows = {}
        for f in sorted(glob.glob(str(Path(pkg) / sub / "external_part*.json"))):
            for r in json.load(open(f)):
                rows[r.get("session_id")] = (r, Path(f).name)
        for opaque, sid in man.get("keymap", {}).items():
            h = (man.get("transcript_hashes") or {}).get(sid)
            if not h or live_hash.get(sid) != h:
                continue
            if opaque not in rows or validate_row(rows[opaque][0]):
                continue
            out[sid] = {"package": pkg, "subdir": sub, "opaque": opaque,
                        "file": rows[opaque][1], "transcript_hash": h}
    return out


# ------------------------------------------------------------------- build --
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260926)
    ap.add_argument("--bridge", type=int, default=24,
                    help="reusable sessions to re-ask under fresh ids, to "
                         "measure the harness shift (0 to skip)")
    ap.add_argument("--max-sessions", type=int, default=120)
    ap.add_argument("--max-bytes", type=int, default=3_000_000)
    ap.add_argument("--public-dir", default=str(PUBLIC_DIR))
    ap.add_argument("--manifest-dir", default=str(MANIFEST_DIR))
    ap.add_argument("--exclude", help="file of session ids to leave out, one "
                                      "per line, optional reason after "
                                      "whitespace")
    ap.add_argument("--force", action="store_true",
                    help="rebuild over an existing package (new ids: returned "
                         "files from the old build become undecodable)")
    args = ap.parse_args()

    pub = Path(args.public_dir)
    mdir = Path(args.manifest_dir)
    man_path = mdir / "_manifest.json"
    returned = pub / "returned"
    if returned.exists() and any(returned.iterdir()):
        raise SystemExit("%s holds returned files. A rebuild re-draws every id "
                         "and would orphan them; import them first and move "
                         "them away." % returned)
    if man_path.exists() and not args.force:
        raise SystemExit("%s exists. Pass --force to rebuild (this re-draws "
                         "every id)." % man_path)

    # ---- the corpus, and the fail-closed agreement with the session judge
    sessions, origin = load_current()
    live_hash = {sid: transcript_hash(s) for sid, s in sessions.items()}
    judged = [json.loads(l) for l in open(JUDGE_FILE) if l.strip()]
    judged_ids = [r["session_id"] for r in judged]
    if len(set(judged_ids)) != len(judged_ids):
        raise SystemExit("duplicate session ids in %s" % JUDGE_FILE)
    if set(judged_ids) != set(sessions):
        raise SystemExit("the session judge and the files on disk disagree: "
                         "%d judged-not-on-disk, %d on-disk-not-judged"
                         % (len(set(judged_ids) - set(sessions)),
                            len(set(sessions) - set(judged_ids))))
    stale = [r["session_id"] for r in judged
             if r.get("transcript_hash")
             and r["transcript_hash"] != live_hash[r["session_id"]]]
    if stale:
        raise SystemExit("%d judged row(s) carry a hash that no longer matches "
                         "the transcript, e.g. %s. Re-judge those first."
                         % (len(stale), stale[0]))
    hashed = sum(1 for r in judged if r.get("transcript_hash"))
    provider_ids = {s["test_model"]: s.get("test_model_id")
                    for s in sessions.values()}
    vendor = {m: (pid.split("/", 1)[0] if pid and "/" in pid else m)
              for m, pid in provider_ids.items()}
    strict_rx, ambig_rx, self_rx = compile_scanners(provider_ids)

    excluded = {}
    if args.exclude:
        for line in open(args.exclude):
            line = line.strip()
            if line and not line.startswith("#"):
                sid, _, why = line.partition(" ")
                if sid not in sessions:
                    raise SystemExit("--exclude names %s, which is not a "
                                     "current craft session" % sid)
                excluded[sid] = why.strip() or "excluded by --exclude"

    # ---- reuse and bridge
    reuse = reusable_rows(live_hash)
    reuse = {k: v for k, v in reuse.items() if k not in excluded}
    rng_bridge = random.Random(args.seed + 2)
    bridge = sorted(rng_bridge.sample(sorted(reuse), min(args.bridge, len(reuse))))
    picked = sorted((set(sessions) - set(reuse) - set(excluded)) | set(bridge))

    # ---- blinding scan and redaction
    texts, redactions, ambig, self_id = {}, [], defaultdict(Counter), []
    for sid in picked:
        s = sessions[sid]
        for fld in ("character_name", "user_name"):
            if strict_rx.search(s[fld]):
                raise SystemExit("%s of %s carries a model or vendor name: %r"
                                 % (fld, sid, s[fld]))
        t = format_transcript(s)
        for m in strict_rx.finditer(t):
            redactions.append({"session": sid, "match": m.group(0),
                               "context": t[max(0, m.start() - 60):m.end() + 60]})
        if redactions and redactions[-1]["session"] == sid:
            t = strict_rx.sub(REDACTION, t)
        texts[sid] = t
        model = sid.split("::")[0]
        for m in ambig_rx.finditer(t):
            ambig[m.group(1).lower()][vendor[model]] += 1
        for m in self_rx.finditer(t):
            self_id.append({"session": sid, "match": m.group(0),
                            "context": t[max(0, m.start() - 60):m.end() + 60]})

    # ---- shuffle, ids, parts, chunks
    order = list(picked)
    random.Random(args.seed + 1).shuffle(order)
    width = max(4, len(str(len(order) - 1)))
    keymap, items = {}, []
    for i, sid in enumerate(order):
        opaque = "%s%0*d" % (ID_PREFIX, width, i)
        keymap[opaque] = sid
        s = sessions[sid]
        items.append({"session_id": opaque,
                      "character_name": s["character_name"],
                      "user_name": s["user_name"],
                      "num_turns": s["num_turns"],
                      "transcript": texts[sid]})
    parts = [items[i:i + PART] for i in range(0, len(items), PART)]
    size = lambda its: sum(len(json.dumps(it, ensure_ascii=False).encode())
                           for it in its)
    total = size(items)
    n_chunks = max(math.ceil(len(items) / args.max_sessions),
                   math.ceil(total / args.max_bytes))
    while True:
        base, extra = divmod(len(parts), n_chunks)
        chunks, k = [], 0
        for c in range(n_chunks):
            n = base + (1 if c < extra else 0)
            chunks.append(parts[k:k + n])
            k += n
        if all(sum(len(p) for p in ch) <= args.max_sessions
               and size([it for p in ch for it in p]) <= args.max_bytes
               for ch in chunks):
            break
        n_chunks += 1

    # ---- write the public side
    pub.mkdir(parents=True, exist_ok=True)
    for old in pub.glob("chunk_*.zip"):
        old.unlink()
    returned.mkdir(exist_ok=True)
    rubric = multiturn.SESSION_JUDGE_SYSTEM
    task = TASK_MD
    schema_src = Path("lib/external_judge_schema.py").read_text(encoding="utf-8")
    fixed_time = (2026, 1, 1, 0, 0, 0)      # no build time inside the zips
    chunk_meta = {}
    for c, ch in enumerate(chunks, 1):
        cn = "%02d" % c
        name = "chunk_%s" % cn
        out_name = "%s.out.json" % name
        part_ids = {"sessions_part%02d.json" % (j + 1): [it["session_id"] for it in p]
                    for j, p in enumerate(ch)}
        n_sess = sum(len(v) for v in part_ids.values())
        items_doc = {"chunk": cn, "chunks_total": len(chunks),
                     "output_file": out_name,
                     "report_file": "%s.report.md" % name,
                     "sessions": n_sess, "parts": part_ids}
        chunk_md = CHUNK_MD.format(cn=cn, total=len(chunks), n=n_sess,
                                   n_parts=len(ch), out=out_name,
                                   rep="%s.report.md" % name,
                                   first=ch[0][0]["session_id"],
                                   last=ch[-1][-1]["session_id"])
        files = [("TASK.md", task), ("CHUNK.md", chunk_md),
                 ("RUBRIC.md", rubric), ("validate_output.py", schema_src),
                 ("ITEMS.json", json.dumps(items_doc, indent=1))]
        for j, p in enumerate(ch):
            files.append(("sessions_part%02d.json" % (j + 1),
                          json.dumps(p, ensure_ascii=False, indent=1)))
        zp = pub / ("%s.zip" % name)
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for fname, body in files:
                zi = zipfile.ZipInfo("%s/%s" % (name, fname), date_time=fixed_time)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o644 << 16
                z.writestr(zi, body)
        chunk_meta[cn] = {
            "zip": zp.name, "zip_sha256": sha256_file(zp),
            "zip_bytes": zp.stat().st_size,
            "transcript_bytes": size([it for p in ch for it in p]),
            "sessions": n_sess, "output_file": out_name,
            "parts": part_ids,
        }
    (pub / "TASK.md").write_text(task, encoding="utf-8")

    # ---- the manifest, our side only
    mdir.mkdir(parents=True, exist_ok=True)
    (mdir / "RUBRIC.md").write_text(rubric, encoding="utf-8")
    (mdir / "TASK.md").write_text(task, encoding="utf-8")
    judge_sha = sha256_file(JUDGE_FILE)
    manifest = {
        "package": "judge_full_chatgpt",
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "seed": args.seed,
        "strata": None,
        "id_prefix": ID_PREFIX,
        "session_ids": order,
        "keymap": keymap,
        "transcript_hashes": {sid: live_hash[sid] for sid in order},
        "chunks": chunk_meta,
        "part_size": PART,
        "reused": reuse,
        "bridge": bridge,
        "excluded": excluded,
        "corpus": {
            "sessions": len(sessions),
            "judge_file": str(JUDGE_FILE), "judge_file_sha256": judge_sha,
            "judge_rows_with_hash": hashed,
            "sources": session_sources(),
            "rule": "newest craft_baseline_* first, then "
                    "multiturn_merged_all_v2.json; first occurrence wins",
        },
        "blinding": {
            "redaction_token": REDACTION,
            "redactions": redactions,
            "ambiguous_word_counts_by_vendor": {w: dict(c) for w, c in
                                                sorted(ambig.items())},
            "self_id_and_residue": self_id,
        },
        "public_dir": str(pub),
        "harness_note": "Returned rows come from ChatGPT, run blind in Codex "
                        "on a ChatGPT subscription. Reused rows came from the "
                        "earlier blind passes judge_round2_chatgpt / "
                        "judge_inc1_chatgpt, each a coordinator handing parts "
                        "to three clean-context raters (their METHOD.md); "
                        "where those ran is not recorded. The bridge sessions "
                        "are in both.",
    }
    json.dump(manifest, open(man_path, "w"), indent=1, ensure_ascii=False)

    # ---- README for Levi, written last so it can quote the real numbers
    readme = README_MD.format(
        n_chunks=len(chunks), n_sessions=len(order), n_new=len(order) - len(bridge),
        n_reused=len(reuse), n_bridge=len(bridge), n_total=len(sessions),
        n_round2=sum(1 for v in reuse.values() if "round2" in v["package"]),
        n_inc1=sum(1 for v in reuse.values() if "inc1" in v["package"]),
        sizes=", ".join("%d" % m["sessions"] for m in chunk_meta.values()),
        mb=total / 1e6, pub=pub, repo=Path.cwd(),
        last="%02d" % len(chunks))
    (pub / "LEVI_README.md").write_text(readme, encoding="utf-8")

    # ---- report
    vend = {sid: vendor[sid.split("::")[0]] for sid in order}
    print("full-corpus ChatGPT package -> %s" % pub)
    print("  corpus:     %d sessions (judge file agrees; %d rows carry a hash, "
          "all match)" % (len(sessions), hashed))
    print("  reused:     %d (round2 %d, inc1 %d)  bridge re-asked: %d"
          % (len(reuse),
             sum(1 for v in reuse.values() if "round2" in v["package"]),
             sum(1 for v in reuse.values() if "inc1" in v["package"]),
             len(bridge)))
    print("  excluded:   %d" % len(excluded))
    print("  in package: %d sessions, %.1f MB of transcript, %d parts, %d chunks"
          % (len(order), total / 1e6, len(parts), len(chunks)))
    for cn, m in chunk_meta.items():
        vc = Counter(vend[keymap[i]] for p in m["parts"].values() for i in p)
        print("    chunk_%s  %3d sessions  %4.2f MB text  %4d KB zip  "
              "anthropic %2d openai %2d google %2d"
              % (cn, m["sessions"], m["transcript_bytes"] / 1e6,
                 m["zip_bytes"] // 1024, vc["anthropic"], vc["openai"],
                 vc["google"]))
    print("  redacted:   %d strict tell(s)" % len(redactions))
    for r in redactions[:20]:
        print("      %-44s %r" % (r["session"], r["context"].replace("\n", " ")))
    # A product word that shows up mostly in its own vendor's sessions is a
    # tell; one spread in proportion to the package is the scenario talking.
    share = Counter(vend.values())
    print("  ambiguous words (hits: own-vendor hits / own-vendor share of package):")
    for w, c in sorted(ambig.items(), key=lambda kv: -sum(kv[1].values())):
        own = OWN_VENDOR.get(w)
        n = sum(c.values())
        mine = sum(c[v] for v in own) if own else 0
        exp = sum(share[v] for v in own) / len(order) if own else 0
        print("      %-12s %4d  own %4d (%.0f%% vs %.0f%% of sessions)  %s"
              % (w, n, mine, 100 * mine / n if n else 0, 100 * exp,
                 ", ".join("%s %d" % kv for kv in c.most_common(3))))
    print("  reported:   %d self-id/residue hit(s) in %d session(s)"
          % (len(self_id), len({x["session"] for x in self_id})))
    blank = [sid for sid in order
             if not any((m.get("content") or "").strip()
                        for m in sessions[sid]["dialogue"]
                        if m["role"] == "character" and m.get("turn"))]
    print("  sessions with no model text after turn 0: %d" % len(blank))
    print("  manifest:   %s  (keymap + hashes; never upload it)" % man_path)


# ------------------------------------------------------------------- texts --
TASK_MD = """# Independent session judging: blind pass, full corpus

You are scoring roleplay transcripts against a fixed rubric. This zip is one
chunk of a larger package; `CHUNK.md` says which chunk, how many sessions it
holds and the exact name of the file to return. Other judges have scored these
transcripts. **You will not be shown their scores and must not try to infer
them.** The value of this pass is that it is independent; a judge aiming at an
expected answer measures nothing.

## Read this part carefully

**1. The ids are opaque on purpose, and model identity is off limits.**
Sessions are `f0000`, `f0001`, and so on. Do not try to identify the model or
the company behind any transcript, do not write a guess about it anywhere
(scores, rationales, notes or report), and do not let one influence a score.
If you find yourself thinking "this reads like model X", that is exactly the
thought this pass exists to exclude. A few words in the transcripts were
replaced with `[name removed]`; treat that as ordinary text and do not try to
reconstruct it.

**2. If you split the work across several agents, assign whole parts at
random.** An earlier pass handed out contiguous ranges, and the sample
happened to be ordered so that those ranges grouped by vendor; rater
calibration and vendor then became impossible to separate. The sessions in
this package are shuffled, so random assignment keeps it clean. Draw a seed
with `secrets.randbits(64)` before reading any transcript, shuffle the part
numbers with `random.Random(seed).shuffle`, deal them round-robin, and start
every helper with a clean context. **Report the seed and which agent scored
which parts.**

**3. Use only the files in this zip.** No web search, no connectors or apps,
no files or chats from other conversations, and nothing you may remember from
earlier conversations about this benchmark (scores, model names, rankings). If
you notice that such memory is available to you, say so in the report.

**4. Score every session in every part.** Read each transcript in full. Do
not sample, skim, or derive a score from length, keyword counts, another
session, or a template. Every row must come from reading that transcript.

## What you are given

- `CHUNK.md` and `ITEMS.json`: this chunk's number, its parts and the ids in
  each part, and the output file name.
- `RUBRIC.md`: the operative rubric, verbatim from the benchmark harness. It
  is the **only** source of dimensions and calibration.
- `sessions_part01.json`, `sessions_part02.json`, ...: the transcripts, 10 per
  part (the last part of the whole package may hold fewer). Each item has
  `session_id`, `character_name`, `user_name`, `num_turns`, `transcript`.
- `validate_output.py`: the checker your output file must pass. It is the
  same code that will accept or reject the file on our side.

## What you are scoring

An AI played `character_name`. A simulated user played `user_name`. Score
**the AI character's** performance across the whole session, never the
simulated user's. These are fictional roleplay transcripts written for a
writing-quality benchmark; some contain dark themes or violence. You are only
scoring the writing.

The transcript interleaves both sides as `**Name** (turn N)`.

**Turn 0 is not the model's work.** It is a scripted opening written by the
benchmark authors, identical across every session sharing a scenario. Neither
credit nor penalise it.

## Rules

1. **Read `RUBRIC.md` in full first**, and score every dimension it lists. It
   contains `%(character_name)s`, `%(user_name)s`, `%(num_turns)s`
   placeholders; fill them from each item's own fields.
2. **The scale is 1-5.** Never 0, never above 5. Fractions are fine. The
   rubric's calibration is binding: 3 = adequate, 4 = strong, 5 = exceptional
   and rare; most decent models land 2.5-4.0.
3. **Score what is there.** Some sessions dropped out early and a few contain
   no model text at all beyond the scripted opening. Score them as written
   and say so in `overall_notes`. Do not award partial credit for absent text
   and do not invent penalties the rubric does not name.
4. **Every dimension gets a number.** A missing one makes the row unusable.
5. **Do not invent dimensions.** The rubric's keys are the only keys.
6. One sentence per `rationale`.
7. `overall` is your holistic judgement of the session on the same 1-5 scale;
   the rubric gives no formula for it.
8. `violation_count` (S.5): the rubric does not define the unit. Use the
   convention earlier passes of this judge adopted: count each separate
   unauthorized action, speech act, decision or attribution of an inner state
   to the user's character; a continuous related action counts once and
   re-describing it does not add to the count; an NPC's order on its own is
   not a violation; separate actions in one reply are not merged into one.

## Output

**One file for the whole chunk**, named exactly as `CHUNK.md` says (for
example `chunk_01.out.json`), delivered as a downloadable file: a single JSON
array with one object per session, in the order the ids appear in
`ITEMS.json`, each object in exactly the rubric's output shape plus
`session_id`. Plain JSON, no fences, no commentary inside the file.

```json
[{
  "session_id": "f0000",
  "session_dimensions": {
    "S.1_consistency_over_time":   {"score": 0.0, "rationale": ""},
    "S.2_degradation_resistance":  {"score": 0.0, "rationale": ""},
    "S.3_narrative_momentum":      {"score": 0.0, "rationale": ""},
    "S.4_adaptive_responsiveness": {"score": 0.0, "rationale": ""},
    "S.5_agency_respect_session":  {"score": 0.0, "rationale": "", "violation_count": 0},
    "S.6_temporal_reasoning":      {"score": 0.0, "rationale": "", "contradictions": []}
  },
  "standard_dimensions": {
    "2.1_anti_purple_prose": {"score": 0.0, "rationale": ""},
    "2.2_anti_repetition":   {"score": 0.0, "rationale": ""},
    "2.5_show_dont_tell":    {"score": 0.0, "rationale": ""},
    "2.6_subtext":           {"score": 0.0, "rationale": ""},
    "2.7_pacing":            {"score": 0.0, "rationale": ""}
  },
  "quality_trajectory": {
    "early_quality": 0.0, "mid_quality": 0.0, "late_quality": 0.0,
    "degradation_detected": false
  },
  "overall": 0.0,
  "overall_notes": "one or two sentences"
}]
```

Before returning, run `python validate_output.py <your file>` from the
unzipped chunk folder and fix every problem it reports. Do not return a file
that fails it.

**If you must stop before the end**, stop at a part boundary, return the file
with the parts you finished, and say in the report which parts remain. When
asked to continue, finish the remaining parts and return the **complete** file
again (every part, including the ones delivered before) under the same name.

## Report back

Also return a short report as `chunk_NN.report.md` (the name is in
`CHUNK.md`), covering:

- Which parts you completed, and **which agent scored which parts** (with the
  seed) if you split the work.
- min / median / max of `overall`.
- Anything the rubric cannot express. Earlier passes' most useful output was
  their own list of these, not their scores.
- Any session where the rubric forced a score you disagreed with.
- Anything you noticed that might compromise the independence of this pass.

## One thing worth knowing

Disagreement with the other judges is not failure. If the passes diverge, that
is a finding about the instrument, and it is why this task exists. Score the
way the rubric says and let the numbers fall where they do.
"""

CHUNK_MD = """# Chunk {cn} of {total}

- Sessions in this chunk: **{n}**, in {n_parts} parts (`sessions_part01.json`
  ... `sessions_part{n_parts:02d}.json`).
- Ids: `{first}` to `{last}`; `ITEMS.json` lists exactly which ids are in
  which part.
- Return: **`{out}`** (all {n} rows, one JSON array) and **`{rep}`**.
- Check: `python validate_output.py {out}` must print `OK`.

Read `TASK.md` first; it has the rules. Score every session.
"""

README_MD = """# Прогон ChatGPT по всему корпусу craft (подписка, вручную)

Здесь всё, что нужно загрузить в ChatGPT. Ключ к id (какая модель за каким
`f0000`) и хеши лежат **не здесь**, а в репозитории:
`{repo}/results/judge_full_chatgpt/_manifest.json`. Этот файл никуда не
загружать.

## Что в пакете

- `chunk_01.zip` ... `chunk_{last}.zip`: {n_chunks} архивов, в них по порядку
  {sizes} сессий. Внутри каждого: `TASK.md` (задание для ChatGPT),
  `CHUNK.md` (номер чанка и имя файла ответа), `RUBRIC.md`, `ITEMS.json`
  (список id по частям), `validate_output.py` (проверка ответа) и
  `sessions_partNN.json` по 10 сессий.
- `TASK.md`: то же задание отдельным файлом, чтобы можно было прочитать. В
  ChatGPT его отдельно грузить не нужно, он уже в каждом архиве.
- `returned/`: сюда складывать ответы ChatGPT.

Всего в корпусе {n_total} сессий. В пакете {n_sessions}: {n_new} новых и
{n_bridge} "мостовых". {n_reused} сессий уже оценены прошлыми слепыми
прогонами ChatGPT на том же тексте (round2: {n_round2}, inc1: {n_inc1}), их
оценки переиспользуются. Мостовые: {n_bridge} из этих {n_reused}, отправленных
ещё раз под новыми id. По ним видно, совпадает ли этот прогон с прошлыми
(другой запуск и другие оценщики: там координатор раздавал части трём
помощникам с чистым контекстом, а где шли те прогоны, не записано). В 18c
тот же Gemini в двух разных оболочках разошёлся на 0.39, примерно столько
же, сколько разные семейства. Текста около {mb:.0f} МБ.

Только craft. 12 gore-сессий раунда 4 с несовершеннолетними, которые ты
убрал, относятся к ladder (`r4_a_gore_*`); в этом пакете их нет и не было.
`mistral_small_2603` здесь с 4 сессиями из 20: когда догенерируешь
остальные, импорт покажет их как "not in this package", им нужен отдельный
маленький пакет.

## Один раз перед началом

1. **Модель и режим такие же, как в прошлые разы.** ROUND4_DESIGN §15
   записывает первый прогон как "ChatGPT (Astra)". Отчёты round2 и inc1
   показывают тот же режим: ChatGPT сам запускал трёх помощников с чистым
   контекстом (`fork_turns=none`, агенты `/root/judge_a` и т.д.) и гонял
   Python. Какой именно пункт меню ты тогда выбирал, в файлах не записано.
   Выбери тот же. В режиме без помощников и без Python чанк на 100-110
   сессий за один заход не пройдёт, придётся несколько раз писать
   "продолжи" (см. ниже).
2. **Выключи память на время прогона**: в Settings → Personalization
   (названия пунктов могут чуть отличаться) выключить "Reference saved
   memories" и "Reference chat history". В прошлых
   чатах были названия моделей и оценки, а судья должен быть слепым. Custom
   instructions лучше тоже временно убрать.
3. **Никаких коннекторов** (GitHub, Drive и т.п.) в этих чатах. В
   репозитории лежит манифест с ключом.

## Для каждого чанка (01 ... {last})

1. Открыть **новый** чат. Один чанк = один чат, чанки не смешивать.
2. Прикрепить `chunk_NN.zip` из этой папки. Больше ничего не прикреплять.
3. Вставить этот текст как есть:

   ```
   Attached is one chunk of a blind judging package. Unzip it, read TASK.md in full, then CHUNK.md and RUBRIC.md, and follow TASK.md exactly: score every session in every part, never try to identify or guess the model behind any transcript, and use only the files in the zip. Return the two files named in CHUNK.md: the .out.json (it must pass validate_output.py) and the .report.md.
   ```

4. Дождаться двух файлов: `chunk_NN.out.json` и `chunk_NN.report.md`.
5. Скачать и положить в
   `{pub}/returned/`
   под этими же именами, например `returned/chunk_01.out.json` и
   `returned/chunk_01.report.md`.
6. (Можно сразу) запустить импорт, см. ниже. Он скажет, всё ли в порядке с
   этим чанком.

**Если ChatGPT остановился на середине**, в том же чате написать:

```
Continue with the parts that are not done yet, then return the complete .out.json again (all parts, including the ones already delivered) under the same name, plus the updated report.
```

Скачать новый файл поверх старого.

**Если ChatGPT отказывается** или пишет что-то про модели ("похоже на X"),
ничего не исправлять руками. Сохранить что есть и сказать мне. Импорт покажет,
каких id не хватает.

Чанки независимы: их можно гонять в нескольких чатах параллельно и в любом
порядке. Если подписка упёрлась в лимит, продолжить позже, ничего не теряется.

## Сколько времени

Сколько шли прошлые прогоны, нигде не записано. Между коммитом пакета и
коммитом результатов прошло около получаса и для round2 (120 сессий), и для
inc1 (93); это ориентир, а не замер. Закладывай 30-90 минут работы ChatGPT на чанк и 5-10 минут
твоих рук (создать чат, загрузить, скачать). {n_chunks} чанков: примерно
вечер-два, если гонять по 2-3 чата одновременно.

## Импорт (одна команда)

```
cd {repo} && python pipeline/import_chatgpt_full_judge.py
```

Команду можно запускать сколько угодно раз, в том числе после каждого чанка.
Файлы в `returned/` она не трогает. Что она делает:

- проверяет каждый файл: все id чанка на месте, нет чужих и повторов, все поля
  по схеме, все оценки в [1, 5], текст транскрипта не менялся с момента сборки
  пакета (хеш);
- пишет строки туда, где лежат прошлые внешние оценки, в том же формате:
  `results/judge_full_chatgpt/app_pass/external_partNN.json` (NN = номер
  чанка) и сводный вид по всему корпусу `results/judge_full_chatgpt/merged/`
  (новые строки плюс {n_reused} переиспользованных);
- печатает покрытие, что не прошло проверку и сравнение по мостовым сессиям.

Потом сравнение с Sonnet:

```
python pipeline/compare_external_judge.py results/judge_full_chatgpt/merged
```

## Не делать

- Не пересобирать пакет (`pipeline/export_chatgpt_full_package.py --force`), пока
  ответы не импортированы: пересборка заново раздаёт id, и старые ответы уже не
  расшифровать.
- Не загружать `_manifest.json` и ничего из репозитория.
- Манифест пока не закоммичен и лежит в worktree `r4-site`. Не удаляй этот
  worktree, пока манифест не закоммичен или не скопирован: без него ответы не
  расшифровать.
"""


if __name__ == "__main__":
    main()
