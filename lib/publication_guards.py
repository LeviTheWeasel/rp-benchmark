#!/usr/bin/env python3
"""Round-4 publication guards, shared by every exporter that publishes data.

docs/ROUND4_DESIGN.md sec 9: no Track B transcript is exported, B-hard or
B-policy. Published artifacts carry the label, a truncated evidence span and
the judge rationale only. The raw Track B text lives in gitignored
results/r4_trackb_transcripts__*.json companions (harness/r4_private.py); these
guards refuse to open them, and refuse to write any Track B record that
carries dialogue or reply text.

Moved here unchanged from hf_dataset/export.py so that exporters without
pyarrow (rounds/r4/export_plotpoints_round4.py) run the same checks instead of a copy
that drifts. This module must stay dependency-free: standard library only.
Never import harness/r4_private.py from here or from anything that uses it;
its load_r4 rejoins the private Track B text.

Voter ids: an arena voter id is a random per-browser UUID with no account,
IP or device data behind it. It exists to catch vote stuffing, so exports
publish it raw by default and the anti-stuffing analysis can be reproduced
from public data (Levi's decision, 2026-09-28; the same value is the site's
pp_voter_id cookie, which was accepted). voter_pseudonym() stays available
for an export that wants HMAC-SHA256(secret, voter_id) instead, with the
secret from PLOTPOINTS_VOTER_HMAC_SECRET and no default.

Blind-judge keymaps: results/judge_full_chatgpt/_manifest.json maps the
package's opaque session ids back to real sessions and models. It stayed local
(.gitignore) while the run was out, so a browsing judge could not de-blind
itself. The run is imported (2026-09-28), so the keymap may live on GitHub,
where it lets anyone re-check the import; it has no use in the dataset, so the
HF exports still refuse it: _guard_path by path (any _manifest.json under a
judge_full_chatgpt directory, merged/ included) and _guard_keymap by content
under any other name.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path

TRACK_B = ("B-hard", "B-policy")
TRACK_B_SEED_PREFIXES = ("r4_b_hard_", "r4_b_policy_")
# Fields that hold model or simulator text in the round-4 files. A Track B
# record may carry none of them; the split files put reply_sha256,
# private_file or "transcript": "private" in their place.
TEXT_FIELDS = ("dialogue", "reply", "ai_reply", "response", "messages",
               "content", "text", "turns", "transcript", "output", "completion")
# Sec 9's "truncated evidence span"; same cap as harness/r4_private.py.
EVIDENCE_CAP = 160


class PublicationGuardError(RuntimeError):
    """An export would publish round-4 Track B text, or read a private file."""


VOTER_HMAC_ENV = "PLOTPOINTS_VOTER_HMAC_SECRET"


class VoterSecretError(PublicationGuardError):
    """A votes export was asked for without PLOTPOINTS_VOTER_HMAC_SECRET."""


def voter_secret(environ=None) -> bytes:
    """The HMAC key for voter ids, from the environment. Unset or blank
    refuses: there is no default."""
    env = os.environ if environ is None else environ
    secret = env.get(VOTER_HMAC_ENV) or ""
    if not secret.strip():
        raise VoterSecretError(
            "refusing to export votes: %s is unset. Voter ids are published "
            "only as HMAC-SHA256(secret, voter_id), and there is no default "
            "secret" % VOTER_HMAC_ENV)
    return secret.encode("utf-8")


def voter_pseudonym(secret: bytes, voter_id) -> str:
    """HMAC-SHA256(secret, voter_id) as hex. A missing id stays "": the HMAC
    of "" would be one shared pseudonym tying every anonymous vote together."""
    if not secret:
        raise VoterSecretError("voter_pseudonym needs a non-empty secret")
    if voter_id is None or voter_id == "":
        return ""
    return hmac.new(secret, str(voter_id).encode("utf-8"),
                    hashlib.sha256).hexdigest()


# Blind-judge packages whose _manifest.json (the id keymap) never goes into an
# HF export. judge_full_chatgpt's run is imported and its keymap is no longer
# gitignored (GitHub only); the older manifests under results/judge_*/ were
# never refused.
BLIND_KEYMAP_DIRS = ("judge_full_chatgpt",)
KEYMAP_NAME = "_manifest.json"
_HEX = frozenset("0123456789abcdef")


def _guard_path(path: Path):
    """Refuse private inputs and outputs by name, before any byte is read."""
    p = Path(path)
    name = p.name.lower()
    if (name.startswith("r4_trackb_transcripts") or "trackb" in name
            or "_b1_" in name or "_private" in p.parts):
        raise PublicationGuardError(
            "refusing %s: private round-4 file (ROUND4_DESIGN sec 9, .gitignore)"
            % p)
    if name == KEYMAP_NAME and set(p.parts) & set(BLIND_KEYMAP_DIRS):
        raise PublicationGuardError(
            "refusing %s: blind-judge keymap; it stays on GitHub and out of the "
            "HF dataset" % p)


def _guard_keymap(obj, where: str, path: str = "$"):
    """Raise if anything carries a blind-judge keymap (a "keymap" key): the
    content of a _manifest.json copied under another name."""
    if isinstance(obj, dict):
        if "keymap" in obj:
            raise PublicationGuardError(
                "refusing to write %s: %s.keymap is a blind-judge id keymap"
                % (where, path))
        for k, v in obj.items():
            _guard_keymap(v, where, "%s.%s" % (path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _guard_keymap(v, where, "%s[%d]" % (path, i))


def _is_track_b(rec: dict) -> bool:
    if rec.get("track") in TRACK_B:
        return True
    for k in ("seed", "seed_id"):
        v = rec.get(k)
        if isinstance(v, str) and v.startswith(TRACK_B_SEED_PREFIXES):
            return True
    return False


def _carries_text(v) -> bool:
    if isinstance(v, str):
        return v.strip() not in ("", "private")
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return False


def _guard_record(obj, where: str, in_b: bool = False, path: str = "$"):
    """Raise if a Track B record, or anything nested in one, carries text.

    A seed file is not a transcript: its Track B records hold the authored,
    non-graphic probe (challenge_turns[].user_input), which is public, and no
    TEXT_FIELDS key. Evidence on a Track B record must be within the cap.
    """
    if isinstance(obj, dict):
        b = in_b or _is_track_b(obj)
        if b:
            for k in TEXT_FIELDS:
                if k in obj and _carries_text(obj[k]):
                    raise PublicationGuardError(
                        "refusing to write %s: Track B record at %s carries "
                        "'%s' text (ROUND4_DESIGN sec 9)" % (where, path, k))
            for k, v in obj.items():
                if ("evidence" in k and isinstance(v, str)
                        and len(v) > EVIDENCE_CAP):
                    raise PublicationGuardError(
                        "refusing to write %s: Track B evidence at %s.%s is %d "
                        "chars, over the %d cap" % (where, path, k, len(v),
                                                   EVIDENCE_CAP))
        for k, v in obj.items():
            _guard_record(v, where, b, "%s.%s" % (path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _guard_record(v, where, in_b, "%s[%d]" % (path, i))


def _read_public_json(path: Path):
    _guard_path(path)
    with open(path) as f:
        return json.load(f)
