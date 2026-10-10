"""rounds/r4/export_plotpoints_round4.py and the generate_profile_cards_v2 split.

Run by path from the repo root:
    python -m unittest tests/test_plotpoints_export.py

Synthetic round-4 files cover the Track B, dedupe, allowlist, cap, exclude and
youth-screen rules. The card and markdown tests build from the HEAD copies of
the card inputs (git show into a temp dir), so a craft-baseline regeneration in
the working tree cannot make them flap; the real-data test reads the tracked
r4_full_*.json files and is skipped when they are absent.

Pair ids are keyed (PLOTPOINTS_PAIR_ID_SECRET). These tests never read that
variable: they pass KEY, a throwaway made up for this file, which must never be
used for a real export.
"""
import argparse
import ast
import contextlib
import hashlib
import hmac
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rounds.r4 import export_plotpoints_round4 as E  # noqa: E402
from pipeline import generate_profile_cards_v2 as G  # noqa: E402
from lib import publication_guards as PG  # noqa: E402
from lib.publication_guards import PublicationGuardError  # noqa: E402

# Throwaway keys for these tests only. Never export with either.
KEY = b"unit-test-throwaway-pair-key-0001-not-for-export"
KEY2 = b"unit-test-throwaway-pair-key-0002-not-for-export"
ENV = "PLOTPOINTS_PAIR_ID_SECRET"


def _without_key():
    env = {k: v for k, v in os.environ.items() if k != ENV}
    return mock.patch.dict(os.environ, env, clear=True)


def _msgs(seed, model, n_turns=4, ask_turns=(2,), ask_text=None, reply=None):
    """A dialogue shaped like r4_full: character at even indexes, the scripted
    asks at 2t - 1 with is_challenge, one trailing user line."""
    asks = {2 * t - 1 for t in ask_turns}
    out = []
    for i in range(2 * n_turns):
        role = "character" if i % 2 == 0 else "user"
        content = ("%s reply %d from %s" % (seed, i, model)) if role == "character" \
            else "user line %d" % i
        if i in asks:
            content = ask_text or "the ask at %d" % i
        if role == "character" and reply is not None and i == 2:
            content = reply
        m = {"turn": i, "role": role, "name": role, "content": content, "tokens": 5}
        if i >= 2:
            m["is_challenge"] = i in asks
        out.append(m)
    return out


def _session(model, seed, track="A", labelled=True, error=False, **kw):
    s = {"seed_id": seed, "test_model": model, "track": track,
         "character_name": "Char", "user_name": "User", "num_turns": 4,
         "dialogue": _msgs(seed, model, **kw)}
    if labelled:
        s["rung_labels"] = [{"rung": 1, "label": "engaged"}]
    if error:
        s["error"] = "timeout"
    return s


def _seed(sid, subtrack="intimacy", setting="Two adults, 30-year-olds."):
    return {"id": sid, "track": "A", "subtrack": subtrack,
            "failure_target": "over_refusal_%s" % subtrack,
            "character_setting": setting, "character_name": "Char",
            "user_name": "User", "user_setting": "",
            "content_flags": ["nsfw"] if subtrack == "intimacy" else ["graphic_violence"],
            "explicitness": "explicit" if subtrack == "intimacy" else "graphic",
            "challenge_turns": [{"turn": 2, "rung": 1, "user_input": "the ask at 3"}]}


def _write_run(d, name, sessions):
    p = Path(d) / name
    p.write_text(json.dumps({"run_id": name, "sessions": sessions}))
    return p


class Synthetic(unittest.TestCase):
    """A tiny round: two seeds, a few models, Track B rows with dialogue."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.seeds = {"r4_a_intimacy_01": _seed("r4_a_intimacy_01"),
                      "r4_a_gore_01": _seed("r4_a_gore_01", "gore")}
        self.models = ["m_a", "m_b", "m_c", "m_d", "m_e", "m_f"]

    def tearDown(self):
        self.tmp.cleanup()

    def _full_run(self, extra=()):
        rows = [_session(m, sid) for sid in self.seeds for m in self.models]
        # Track B rows carrying dialogue: none of this may reach an output.
        rows.append(_session("m_a", "r4_b_hard_b2_01", track="B-hard"))
        rows.append(_session("m_b", "r4_b_policy_01", track="B-policy"))
        rows.extend(extra)
        return _write_run(self.d, "r4_full_20990101_000000.json", rows)

    def export(self, paths, **kw):
        kw.setdefault("roster", self.models)
        kw.setdefault("secret", KEY)
        roster = kw.pop("roster")
        return E.build_sessions_export(paths, self.seeds, roster, **kw)

    def check(self, manifest, index, sessions, secret=KEY, matchings=4):
        return E.check_sessions_export(manifest, index, sessions, self.models,
                                       matchings, secret=secret)

    # -- Track B -----------------------------------------------------------

    def test_only_track_a_is_exported(self):
        manifest, index, sessions, _ = self.export([self._full_run()])
        self.assertEqual({s["seed_id"] for s in sessions.values()}, set(self.seeds))
        self.assertEqual(len(sessions), len(self.seeds) * len(self.models))
        blob = (E.manifest_json(manifest) + E.pair_index_json(index)
                + E.sessions_json(sessions))
        for needle in (b"r4_b_", b"B-hard", b"B-policy"):
            self.assertNotIn(needle, blob)
        problems, facts = self.check(manifest, index, sessions)
        self.assertEqual(problems, [])
        self.assertEqual(facts["track_b_ids"], 0)

    def test_guard_record_raises_if_a_track_b_record_reaches_output(self):
        manifest, index, sessions, _ = self.export([self._full_run()])
        leaked = dict(sessions)
        leaked["r4_b_hard_b2_01::m_a"] = {
            "seed_id": "r4_b_hard_b2_01", "test_model": "m_a",
            "dialogue": [{"role": "assistant", "content": "held the line"}]}
        with self.assertRaises(PublicationGuardError):
            PG._guard_record(leaked, "sessions.json")
        problems, _ = self.check(manifest, index, leaked)
        self.assertTrue(any("Track B record" in p for p in problems), problems)
        self.assertTrue(any("forbidden bytes" in p for p in problems), problems)

    def test_track_a_row_with_a_track_b_seed_id_fails(self):
        bad = _session("m_a", "r4_b_hard_b2_02", track="A")
        with self.assertRaises(E.ExportError):
            self.export([self._full_run(extra=[bad])])

    def test_private_paths_are_refused(self):
        for name in ("r4_trackb_transcripts__x.json",
                     "r4_trackb_transcripts__r4_full_20260925_125329.json",
                     "r4_full_20260101_000000_b1_age.json"):
            with self.subTest(name=name):
                with self.assertRaises(PublicationGuardError):
                    PG._guard_path(Path("results") / name)
        # A private file that matches the r4_full glob is refused on listing.
        (self.d / "r4_full_20990101_000000_b1_x.json").write_text("{}")
        with self.assertRaises(PublicationGuardError):
            E.r4_paths(self.d)
        with self.assertRaises(PublicationGuardError):
            PG._read_public_json(self.d / "r4_trackb_transcripts__x.json")

    # -- Dedupe --------------------------------------------------------------

    def test_newest_copy_wins(self):
        old = _write_run(self.d, "r4_full_20990101_000000.json",
                         [_session("m_a", "r4_a_gore_01", reply="OLD")])
        new = _write_run(self.d, "r4_full_20990102_000000.json",
                         [_session("m_a", "r4_a_gore_01", reply="NEW")])
        paths = E.r4_paths(self.d)
        self.assertEqual([p.name for p in paths], [new.name, old.name])
        kept, origin, _, stats = E.dedupe_track_a(paths)
        self.assertEqual(kept[("m_a", "r4_a_gore_01")]["dialogue"][2]["content"], "NEW")
        self.assertEqual(origin[("m_a", "r4_a_gore_01")], new.name)
        self.assertEqual(stats["superseded"], 1)

    def test_error_rows_are_skipped_before_claiming(self):
        _write_run(self.d, "r4_full_20990101_000000.json",
                   [_session("m_a", "r4_a_gore_01", reply="GOOD")])
        _write_run(self.d, "r4_full_20990102_000000.json",
                   [_session("m_a", "r4_a_gore_01", error=True, reply="ERR")])
        kept, _, _, stats = E.dedupe_track_a(E.r4_paths(self.d))
        self.assertEqual(kept[("m_a", "r4_a_gore_01")]["dialogue"][2]["content"], "GOOD")
        self.assertEqual(stats["error_rows"], 1)
        self.assertEqual(stats["superseded"], 0)

    def test_unlabelled_newest_copy_drops_with_no_fallback(self):
        _write_run(self.d, "r4_full_20990101_000000.json",
                   [_session("m_a", "r4_a_gore_01", reply="LABELLED")])
        _write_run(self.d, "r4_full_20990102_000000.json",
                   [_session("m_a", "r4_a_gore_01", labelled=False)])
        kept, _, unlabelled, stats = E.dedupe_track_a(E.r4_paths(self.d))
        self.assertNotIn(("m_a", "r4_a_gore_01"), kept)
        self.assertEqual(stats["unlabelled"], 1)
        self.assertEqual(stats["superseded"], 1)
        self.assertEqual([u[:2] for u in unlabelled], [("m_a", "r4_a_gore_01")])

    def test_track_b_claims_do_not_touch_track_a(self):
        # Same model and seed name space, different track: A must survive.
        _write_run(self.d, "r4_full_20990102_000000.json",
                   [_session("m_a", "r4_a_gore_01", track="B-hard")])
        _write_run(self.d, "r4_full_20990101_000000.json",
                   [_session("m_a", "r4_a_gore_01")])
        kept, _, _, _ = E.dedupe_track_a(E.r4_paths(self.d))
        self.assertIn(("m_a", "r4_a_gore_01"), kept)

    # -- Blind pairs -----------------------------------------------------------

    def test_manifest_is_blind_and_the_index_resolves_it(self):
        manifest, index, sessions, _ = self.export([self._full_run()])
        self.assertIs(manifest["blind"], True)
        self.assertEqual(index["export_id"], manifest["export_id"])
        self.assertEqual([p["id"] for p in manifest["pairs"]], list(index["pairs"]))
        for p in manifest["pairs"]:
            self.assertEqual(set(p), {"id", "seed_id"})
            self.assertRegex(p["id"], E.PAIR_ID_RE)
            e = index["pairs"][p["id"]]
            self.assertEqual(e["seed_id"], p["seed_id"])
            self.assertEqual(p["id"], E.pair_id(KEY, manifest["export_id"],
                                                p["seed_id"], e["model_a"],
                                                e["model_b"]))
            self.assertEqual(E.pair_sides(KEY, p["id"], e["model_b"], e["model_a"]),
                             (e["model_a"], e["model_b"]))
            for side in ("model_a", "model_b"):
                self.assertIn("%s::%s" % (p["seed_id"], e[side]), sessions)
        # No model id, and no model key, anywhere in the browser's copy.
        blob = E.manifest_json(manifest).decode()
        for m in self.models:
            self.assertNotIn('"%s"' % m, blob)
        for k in ("model_a", "model_b", "test_model", "mt_"):
            self.assertNotIn(k, blob)

    def test_pair_ids_are_hmac_under_the_key(self):
        msg = b"r4a-x|r4_a_gore_01|m_a|m_b"
        want = "p_" + hmac.new(KEY, msg, hashlib.sha256).hexdigest()[:12]
        self.assertEqual(E.pair_id(KEY, "r4a-x", "r4_a_gore_01", "m_a", "m_b"), want)
        self.assertEqual(E.pair_id(KEY, "r4a-x", "r4_a_gore_01", "m_b", "m_a"), want)
        # Not the bare sha256 anyone could recompute from the roster.
        self.assertNotEqual(want, "p_" + hashlib.sha256(msg).hexdigest()[:12])
        self.assertEqual(E._unkeyed_pair_id("r4a-x", "r4_a_gore_01", "m_a", "m_b"),
                         "p_" + hashlib.sha256(msg).hexdigest()[:12])
        self.assertNotEqual(E.pair_id(KEY2, "r4a-x", "r4_a_gore_01", "m_a", "m_b"),
                            want)
        self.assertNotEqual(E.pair_id(KEY, "r4a-y", "r4_a_gore_01", "m_a", "m_b"),
                            want)
        self.assertNotEqual(E.pair_id(KEY, "r4a-x", "r4_a_gore_02", "m_a", "m_b"),
                            want)
        # The side coin is keyed the same way.
        coin = hmac.new(KEY, ("sides|" + want).encode(), hashlib.sha256).digest()[0] & 1
        self.assertEqual(E.pair_sides(KEY, want, "m_b", "m_a"),
                         ("m_b", "m_a") if coin else ("m_a", "m_b"))
        # A field holding the separator could alias another pair: refused.
        with self.assertRaises(E.ExportError):
            E.pair_id(KEY, "r4a-x", "r4_a_gore_01", "m|a", "m_b")

    def test_no_key_no_pairs(self):
        for bad in (None, b"", b"short", "a str key of forty characters, not bytes"):
            with self.subTest(key=bad):
                with self.assertRaises(E.PairIdSecretError):
                    E.pair_id(bad, "r4a-x", "r4_a_gore_01", "m_a", "m_b")
                with self.assertRaises(E.PairIdSecretError):
                    E.pair_sides(bad, "p_000000000000", "m_a", "m_b")
                with self.assertRaises(E.PairIdSecretError):
                    self.export([self._full_run()], secret=bad)
        # The key is a required argument, with no default to fall back on.
        with self.assertRaises(TypeError):
            E.build_sessions_export([self._full_run()], self.seeds, self.models)
        manifest, index, sessions, _ = self.export([self._full_run()])
        with self.assertRaises(TypeError):
            E.check_sessions_export(manifest, index, sessions, self.models, 4)

    def test_manifest_withholds_the_design_and_provenance(self):
        run = self._full_run()
        manifest, index, sessions, _ = self.export([run], commit="c0ffee" * 6,
                                                   rng_seed=7)
        self.assertEqual(set(manifest), E.MANIFEST_KEYS)
        for gone in ("design", "rng_seed", "method", "source_commit",
                     "source_files", "matchings_per_seed"):
            self.assertNotIn(gone, set(E._all_keys(manifest)))
        blob = E.manifest_json(manifest).decode()
        for gone in ("c0ffee", run.name, "r4_full_", "Hamiltonian",
                     "balanced_matchings"):
            self.assertNotIn(gone, blob)
        # They moved to the server-only index.
        self.assertEqual(set(index), E.PAIR_INDEX_KEYS)
        self.assertEqual(index["source_commit"], "c0ffee" * 6)
        self.assertEqual(index["source_files"], [run.name])
        self.assertEqual(index["design"], {
            "kind": "balanced_matchings", "matchings_per_seed": 4, "rng_seed": 7,
            "method": E.DESIGN_METHOD})
        # Kept: the ballot's export_id and the seed context.
        self.assertRegex(manifest["export_id"], r"^r4a-20990101-[0-9a-f]{7}$")
        self.assertEqual(set(manifest["seeds"]), set(self.seeds))
        # Pairs sit in id order, not the design's seed-then-alphabet order.
        ids = [p["id"] for p in manifest["pairs"]]
        self.assertEqual(ids, sorted(ids))
        design_order = [E.pair_id(KEY, manifest["export_id"], s, a, b)
                        for s, a, b in sorted((e["seed_id"],
                                               *sorted((e["model_a"], e["model_b"])))
                                              for e in index["pairs"].values())]
        self.assertNotEqual(ids, design_order)
        self.assertEqual(sorted(design_order), ids)
        self.assertNotEqual([p["seed_id"] for p in manifest["pairs"]],
                            sorted(p["seed_id"] for p in manifest["pairs"]))

    def test_the_key_reaches_no_output(self):
        manifest, index, sessions, _ = self.export([self._full_run()])
        dest = self.d / "round-4-ladder"
        E.write_sessions_export(dest, manifest, index, sessions)
        for p in dest.iterdir():
            blob = p.read_bytes()
            for form in (KEY, KEY.hex().encode()):
                self.assertNotIn(form, blob, p.name)
        # And the check says so if it ever did.
        m = json.loads(json.dumps(manifest))
        m["label"] = KEY.decode()
        self.assertIn("manifest.json carries the pair-id key",
                      self.check(m, index, sessions)[0])
        i = json.loads(json.dumps(index))
        i["design"]["method"] = KEY.hex()
        self.assertIn("pair-index.json carries the pair-id key",
                      self.check(manifest, i, sessions)[0])

    def test_check_catches_every_break_of_the_blind_format(self):
        manifest, index, sessions, _ = self.export([self._full_run()])
        pid = manifest["pairs"][0]["id"]

        def problems(m, i, secret=KEY):
            return self.check(m, i, sessions, secret=secret)[0]

        def has(text, m, i, secret=KEY):
            got = problems(m, i, secret)
            return any(text in p for p in got) or got

        def copy():
            return json.loads(json.dumps(manifest)), json.loads(json.dumps(index))

        self.assertEqual(problems(manifest, index), [])
        m, i = copy()
        m["pairs"][0]["model_a"] = i["pairs"][pid]["model_a"]
        self.assertIs(has("unexpected ['model_a']", m, i), True)
        self.assertIs(has("names models", m, i), True)
        m, i = copy()
        e = i["pairs"][pid]
        e["model_a"], e["model_b"] = e["model_b"], e["model_a"]
        self.assertIs(has("sides are not", m, i), True)
        m, i = copy()
        del i["pairs"][pid]
        self.assertIs(has("ids differ", m, i), True)
        m, i = copy()
        i["export_id"] = "r4a-other"
        self.assertIs(has("export_id", m, i), True)
        m, i = copy()
        m["blind"] = False
        self.assertIs(has("blind is not true", m, i), True)
        m, i = copy()
        m["label"] = "m_c"
        self.assertIs(has("names models", m, i), True)
        m, i = copy()
        i["pairs"][pid]["model_b"] = "m_zz"
        self.assertIs(has("does not hash", m, i), True)
        m, i = copy()
        del i["pairs"][pid]["model_b"]
        self.assertIs(has("missing ['model_b']", m, i), True)
        # Order: the design's order (or any other) is a tell.
        m, i = copy()
        m["pairs"].reverse()
        self.assertIs(has("not in id order", m, i), True)
        # Design and provenance back in the served copy, at any depth.
        for extra in ({"design": index["design"]},
                      {"source_commit": "c0ffee"},
                      {"source_files": index["source_files"]}):
            with self.subTest(extra=sorted(extra)):
                m, i = copy()
                m.update(extra)
                self.assertIs(has("unexpected %s" % sorted(extra), m, i), True)
                self.assertIs(has("pair-index.json only", m, i), True)
        m, i = copy()
        m["seeds"]["r4_a_gore_01"]["rng_seed"] = 4
        self.assertIs(has("pair-index.json only): ['rng_seed']", m, i), True)
        # Checked under another key, every id fails.
        got = problems(manifest, index, secret=KEY2)
        self.assertEqual(sum("does not hash from its fields under this key" in p
                             for p in got), len(manifest["pairs"]))
        # An export built with the old unkeyed formula is named as such.
        m, i = copy()
        eid = m["export_id"]
        rebuilt = {}
        for p in m["pairs"]:
            e = i["pairs"][p["id"]]
            p["id"] = E._unkeyed_pair_id(eid, e["seed_id"], e["model_a"], e["model_b"])
            rebuilt[p["id"]] = e
        m["pairs"].sort(key=lambda p: p["id"])
        i["pairs"] = rebuilt
        self.assertIs(has("%d pair ids are the unkeyed sha256" % len(rebuilt), m, i),
                      True)
        # The index's own design block is checked too.
        m, i = copy()
        del i["design"]["rng_seed"]
        self.assertIs(has("pair-index.design: missing ['rng_seed']", m, i), True)
        m, i = copy()
        i["source_files"] = ["r4_trackb_transcripts__x.json"]
        self.assertIs(has("source_files is not a list of r4_full", m, i), True)
        got = self.check(manifest, index, sessions, matchings=6)[0]
        self.assertTrue(any("checked against 6" in p for p in got), got)

    def test_write_places_three_files_and_freezes_pair_ids(self):
        manifest, index, sessions, _ = self.export([self._full_run()])
        dest = self.d / "site" / "round-4-ladder"
        E.write_sessions_export(dest, manifest, index, sessions)
        self.assertEqual(sorted(p.name for p in dest.iterdir()),
                         ["manifest.json", "pair-index.json", "sessions.json"])
        self.assertEqual(json.loads((dest / "pair-index.json").read_text()), index)
        self.assertEqual(json.loads((dest / "manifest.json").read_text()), manifest)
        # The same export again is fine.
        E.write_sessions_export(dest, manifest, index, sessions)
        before = {p.name: p.read_bytes() for p in dest.iterdir()}
        # The same sessions under another key: sessions.json is identical
        # but every id changes, so the index refuses, naming the key.
        m_k2, i_k2, s_k2, _ = self.export([self._full_run()], secret=KEY2)
        self.assertEqual(E.sessions_json(s_k2), before["sessions.json"])
        self.assertFalse(set(i_k2["pairs"]) & set(index["pairs"]))
        with self.assertRaisesRegex(E.ExportError, "none survive: is "
                                    "PLOTPOINTS_PAIR_ID_SECRET the key"):
            E.write_sessions_export(dest, m_k2, i_k2, s_k2)
        self.assertEqual({p.name: p.read_bytes() for p in dest.iterdir()}, before)
        # Dropping a session changes sessions.json and every id: refused,
        # and nothing is touched.
        m2, i2, s2, _ = self.export([self._full_run()], roster=self.models[:5])
        with self.assertRaisesRegex(E.ExportError, "frozen"):
            E.write_sessions_export(dest, m2, i2, s2)
        self.assertEqual({p.name: p.read_bytes() for p in dest.iterdir()}, before)
        # An index that would lose ids is refused even if sessions.json
        # is untouched; --replace (before launch) overrides.
        (dest / "sessions.json").write_bytes(E.sessions_json(s2))
        with self.assertRaisesRegex(E.ExportError, "pair ids would change"):
            E.write_sessions_export(dest, m2, i2, s2)
        E.write_sessions_export(dest, m2, i2, s2, replace=True)
        self.assertEqual(json.loads((dest / "pair-index.json").read_text()), i2)

    def test_a_larger_design_under_the_same_key_only_adds_ids(self):
        manifest, index, sessions, _ = self.export([self._full_run()])
        dest = self.d / "round-4-ladder"
        E.write_sessions_export(dest, manifest, index, sessions)
        m5, i5, s5, _ = self.export([self._full_run()], matchings=5)
        self.assertTrue(set(index["pairs"]) < set(i5["pairs"]))
        self.assertTrue(all(i5["pairs"][k] == v for k, v in index["pairs"].items()))
        self.assertEqual(self.check(m5, i5, s5, matchings=5)[0], [])
        E.write_sessions_export(dest, m5, i5, s5)
        self.assertEqual(json.loads((dest / "pair-index.json").read_text()), i5)
        # Back down would drop ids: refused.
        with self.assertRaisesRegex(E.ExportError, "would change or vanish"):
            E.write_sessions_export(dest, manifest, index, sessions)

    def test_write_refuses_to_drop_the_old_non_blind_ids(self):
        manifest, index, sessions, _ = self.export([self._full_run()])
        dest = self.d / "round-4-ladder"
        dest.mkdir()
        (dest / "manifest.json").write_text(json.dumps({"pairs": [
            {"id": "mt_r4_a_gore_01_m_a_vs_m_b", "seed_id": "r4_a_gore_01",
             "model_a": "m_a", "model_b": "m_b"}]}))
        with self.assertRaisesRegex(E.ExportError, "would vanish"):
            E.write_sessions_export(dest, manifest, index, sessions)
        E.write_sessions_export(dest, manifest, index, sessions, replace=True)
        with self.assertRaisesRegex(E.ExportError, "round-4-<track>"):
            E.write_sessions_export(self.d / "ladder", manifest, index, sessions)

    # -- Allowlist, roles, cap --------------------------------------------

    def test_session_and_dialogue_keys_are_the_allowlist(self):
        manifest, index, sessions, _ = self.export([self._full_run()])
        for key, s in sessions.items():
            self.assertEqual(set(s), E.SESSION_KEYS, key)
            for m in s["dialogue"]:
                self.assertEqual(set(m), E.DIALOGUE_KEYS)
                self.assertIn(m["role"], ("user", "assistant"))
        self.assertEqual(set(manifest), E.MANIFEST_KEYS)
        for seed in manifest["seeds"].values():
            self.assertEqual(set(seed), E.SEED_KEYS)
        for p in manifest["pairs"]:
            self.assertEqual(set(p), E.PAIR_KEYS)
        self.assertEqual(set(index), E.PAIR_INDEX_KEYS)
        self.assertEqual(set(index["design"]), E.DESIGN_KEYS)
        for e in index["pairs"].values():
            self.assertEqual(set(e), E.PAIR_INDEX_ENTRY_KEYS)
        # Dropped: labels, ladder bookkeeping, per-message metadata.
        blob = E.sessions_json(sessions).decode()
        for gone in ("rung_labels", "is_challenge", "tokens", "test_model_id",
                     "\"name\"", "\"track\"", "\"turn\""):
            self.assertNotIn(gone, blob)
        extra = dict(next(iter(sessions.values())))
        extra["rung_labels"] = []
        problems, _ = self.check(manifest, index,
                                 {**sessions, "r4_a_gore_01::m_a": extra})
        self.assertTrue(any("unexpected ['rung_labels']" in p for p in problems))

    def test_empty_and_none_replies_stay_as_empty_strings(self):
        s = _session("m_a", "r4_a_gore_01")
        s["dialogue"][2]["content"] = None
        s["dialogue"][4]["content"] = ""
        out = E.export_session(s, self.seeds["r4_a_gore_01"])
        self.assertEqual(out["dialogue"][2], {"role": "assistant", "content": ""})
        self.assertEqual(out["dialogue"][4], {"role": "assistant", "content": ""})
        self.assertEqual(len(out["dialogue"]), len(s["dialogue"]))

    def test_long_messages_are_cut_with_a_marker(self):
        s = _session("m_a", "r4_a_gore_01", reply="x" * 20000)
        out = E.export_session(s, self.seeds["r4_a_gore_01"])
        m = out["dialogue"][2]
        self.assertEqual(len(m["content"]), E.MESSAGE_CAP)
        self.assertEqual(m["cut_from_chars"], 20000)
        # UTF-16 units, as the site's .length counts them: an astral
        # character is two units and is never split.
        text = "\U0001F600" * 7000
        cut, n = E.cap_text(text)
        self.assertEqual(n, 14000)
        self.assertLessEqual(E.utf16_len(cut), E.MESSAGE_CAP)
        self.assertEqual(cut, "\U0001F600" * 6000)
        self.assertEqual(E.cap_text("short"), ("short", None))

    def test_hashes(self):
        s = _session("m_a", "r4_a_gore_01")
        a = E.export_session(s, self.seeds["r4_a_gore_01"])
        s2 = json.loads(json.dumps(s))
        s2["dialogue"][3]["content"] = "a different simulator line"
        b = E.export_session(s2, self.seeds["r4_a_gore_01"])
        # transcript_hash covers the model's turns only; export_hash covers
        # everything the voter sees (gaps 11).
        self.assertEqual(a["transcript_hash"], b["transcript_hash"])
        self.assertNotEqual(a["export_hash"], b["export_hash"])

    def test_ask_markers_are_verified(self):
        manifest, _, sessions, _ = self.export([self._full_run()])
        self.assertEqual(manifest["seeds"]["r4_a_gore_01"]["ask_turns"], [2])
        self.assertEqual(manifest["seeds"]["r4_a_gore_01"]["ask_message_indexes"], [3])
        moved = _session("m_a", "r4_a_gore_01", ask_turns=(3,), ask_text="the ask at 3")
        with self.assertRaisesRegex(E.ExportError, "ask markers"):
            self.export([_write_run(self.d, "r4_full_20990105_000000.json", [moved])])

    def test_roster_filters_models(self):
        manifest, _, sessions, report = self.export([self._full_run()],
                                                    roster=self.models[:4])
        self.assertEqual({s["test_model"] for s in sessions.values()},
                         set(self.models[:4]))
        self.assertEqual(report["dedupe"]["outside_roster"], 2 * len(self.seeds))

    def test_leaderboard_count_mismatch_is_reported(self):
        counts = {m: 2 for m in self.models}
        counts["m_a"] = 1
        _, _, _, report = self.export([self._full_run()], lb_counts=counts)
        self.assertEqual(len(report["problems"]), 1)
        self.assertIn("m_a", report["problems"][0])

    # -- Exclude list --------------------------------------------------------

    def test_exclude_list_is_honoured(self):
        path = self.d / "exclude.txt"
        path.write_text("# reviewed 2099-01-01\n\n"
                        "r4_a_gore_01::m_c   reads as a minor in turn 6\n")
        exclude = E.load_exclude(path)
        manifest, index, sessions, _ = self.export([self._full_run()], exclude=exclude)
        self.assertNotIn("r4_a_gore_01::m_c", sessions)
        self.assertIn("r4_a_intimacy_01::m_c", sessions)
        self.assertFalse(any(p["seed_id"] == "r4_a_gore_01"
                             and "m_c" in (p["model_a"], p["model_b"])
                             for p in index["pairs"].values()))
        # Served: the seed and a code. The model and the reviewer's words
        # stay in the server-only index.
        self.assertEqual(manifest["excluded"], [
            {"seed_id": "r4_a_gore_01", "reason": "content_review"}])
        self.assertEqual(index["excluded"], [{
            "key": "r4_a_gore_01::m_c", "seed_id": "r4_a_gore_01", "model": "m_c",
            "code": "content_review", "reason": "reads as a minor in turn 6"}])
        blob = E.manifest_json(manifest).decode()
        for gone in ("m_c", "reads as a minor", "turn 6", "::"):
            self.assertNotIn(gone, blob)
        problems, _ = self.check(manifest, index, sessions)
        self.assertEqual(problems, [])

    def test_check_holds_served_exclusions_to_seed_and_code(self):
        path = self.d / "exclude.txt"
        path.write_text("r4_a_gore_01::m_c   reads as a minor in turn 6\n")
        manifest, index, sessions, _ = self.export(
            [self._full_run()], exclude=E.load_exclude(path))

        def has(text, m, i):
            got = self.check(m, i, sessions)[0]
            return any(text in p for p in got) or got

        def copy():
            return json.loads(json.dumps(manifest)), json.loads(json.dumps(index))

        m, i = copy()
        m["excluded"][0]["model"] = "m_c"
        self.assertIs(has("unexpected ['model']", m, i), True)
        self.assertIs(has("names models", m, i), True)
        self.assertIs(has("pair-index.json only): ['model']", m, i), True)
        m, i = copy()
        m["excluded"][0]["reason"] = "reads as a minor in turn 6"
        self.assertIs(has("is not a reason code", m, i), True)
        m, i = copy()
        m["excluded"] = []
        self.assertIs(has("not pair-index.excluded reduced", m, i), True)
        m, i = copy()
        i["excluded"][0]["code"] = "whatever"
        self.assertIs(has("code 'whatever'", m, i), True)
        m, i = copy()
        i["excluded"][0]["key"] = "r4_a_gore_01::m_d"
        self.assertIs(has("key does not match", m, i), True)
        self.assertIs(has("still in sessions.json", m, i), True)
        m, i = copy()
        del i["excluded"]
        self.assertIs(has("pair-index.excluded is not a list", m, i), True)

    def test_exclude_list_rejects_unknown_keys_and_missing_reasons(self):
        path = self.d / "exclude.txt"
        path.write_text("r4_a_gore_01::nobody  typo\n")
        with self.assertRaisesRegex(E.ExportError, "not in the export"):
            self.export([self._full_run()], exclude=E.load_exclude(path))
        path.write_text("r4_a_gore_01::m_c\n")
        with self.assertRaisesRegex(E.ExportError, "no reason"):
            E.load_exclude(path)
        path.write_text("r4_a_gore_01:m_c  one colon\n")
        with self.assertRaisesRegex(E.ExportError, "want <seed_id>::<model>"):
            E.load_exclude(path)

    def test_unlabelled_roster_sessions_are_recorded_as_excluded(self):
        newest = _write_run(self.d, "r4_full_20990109_000000.json",
                            [_session("m_b", "r4_a_gore_01", labelled=False)])
        manifest, index, sessions, _ = self.export([newest, self._full_run()])
        self.assertNotIn("r4_a_gore_01::m_b", sessions)
        self.assertEqual(manifest["excluded"],
                         [{"seed_id": "r4_a_gore_01", "reason": "not_scored"}])
        self.assertEqual([(e["key"], e["code"]) for e in index["excluded"]],
                         [("r4_a_gore_01::m_b", "not_scored")])
        self.assertEqual(index["excluded"][0]["reason"], E.NOT_SCORED_REASON)
        self.assertEqual(self.check(manifest, index, sessions)[0], [])

    def test_served_exclusions_do_not_order_by_model(self):
        path = self.d / "exclude.txt"
        path.write_text("r4_a_gore_01::m_f  one\nr4_a_gore_01::m_a  two\n")
        newest = _write_run(self.d, "r4_full_20990109_000000.json",
                            [_session("m_c", "r4_a_gore_01", labelled=False)])
        manifest, index, sessions, _ = self.export(
            [newest, self._full_run()], exclude=E.load_exclude(path))
        self.assertEqual(manifest["excluded"], [
            {"seed_id": "r4_a_gore_01", "reason": "content_review"},
            {"seed_id": "r4_a_gore_01", "reason": "content_review"},
            {"seed_id": "r4_a_gore_01", "reason": "not_scored"}])
        self.assertEqual([e["key"] for e in index["excluded"]],
                         ["r4_a_gore_01::m_a", "r4_a_gore_01::m_c",
                          "r4_a_gore_01::m_f"])
        self.assertEqual(self.check(manifest, index, sessions)[0], [])

    # -- Youth screen ----------------------------------------------------------

    def test_youth_screen_needs_no_key(self):
        with _without_key():
            sessions, excluded, seeds_meta, used, _ = E.collect_sessions(
                [self._full_run()], self.seeds, self.models)
        # The same sessions and seed context the keyed export serves.
        manifest, _, keyed_sessions, _ = self.export([self._full_run()])
        self.assertEqual(sessions, keyed_sessions)
        self.assertEqual(seeds_meta, manifest["seeds"])
        self.assertEqual(len(sessions), len(self.seeds) * len(self.models))

    def test_youth_screen_lists_hits_with_bounded_context(self):
        s = _session("m_a", "r4_a_intimacy_01",
                     reply=("word " * 100) + "like a teenager again" + (" word" * 100))
        run = _write_run(self.d, "r4_full_20990101_000000.json", [s])
        manifest, _, sessions, _ = self.export([run], roster=["m_a"])
        hits = E.youth_screen(sessions, manifest["seeds"], self.seeds)
        h = [x for x in hits if x["term"] == "teenager"]
        self.assertEqual(len(h), 1)
        self.assertEqual((h[0]["key"], h[0]["message_index"], h[0]["role"],
                          h[0]["tier"]),
                         ("r4_a_intimacy_01::m_a", 2, "assistant", "minor_term"))
        self.assertLessEqual(len(h[0]["context"]), E.CONTEXT_CHARS)
        self.assertIn("teenager", h[0]["context"])
        ages = [x for x in hits if x["tier"] == "age"]
        self.assertEqual(ages, [])  # "30-year-olds" in the seed is not a minor

    def _terms(self, text, tier):
        return [E._term(mo) for t, mo in E.text_hits(text) if t == tier]

    def test_compound_adult_ages_are_not_minor_ages(self):
        for text in ("She is thirty-four years old.", "Thirty four years old.",
                     "a twenty-one-year-old soldier", "Forty-seven years old",
                     "a tree a hundred and four years old"):
            with self.subTest(text=text):
                self.assertEqual(self._terms(text, "age"), [])
        self.assertEqual(self._terms("she was four years old", "age"),
                         ["four years old"])
        self.assertEqual(self._terms("a fourteen-year-old", "age"),
                         ["fourteen-year-old"])
        self.assertEqual(self._terms("aged fifteen, at the age of twelve", "age"),
                         ["aged fifteen", "age of twelve"])

    def _seed_tiers(self, setting, user_setting):
        seed = _seed("r4_a_gore_01", "gore", setting=setting)
        seed["user_setting"] = user_setting
        meta = {"setting_summary": setting, "character_name": "Char",
                "user_name": "User", "subtrack": "gore"}
        hits = E.youth_screen({}, {"r4_a_gore_01": meta}, {"r4_a_gore_01": seed})
        return sorted((h["tier"], h["message_index"]) for h in hits
                      if h["tier"].startswith("seed_"))

    def test_seed_check_accepts_is_nn_and_checks_each_person(self):
        self.assertEqual(self._seed_tiers("Nadia is 30, met the user at a bar.",
                                          "Sam is 33, met Nadia tonight."), [])
        self.assertEqual(self._seed_tiers("Sasha is a 29-year-old woman.",
                                          "Devin is Sasha's 31-year-old partner."), [])
        # gore_01: the character's age is stated, the user's is not.
        self.assertEqual(
            self._seed_tiers("Wrack is a veteran sellsword in her forties.",
                             "Corvin is a younger sellsword, two years in."),
            [("seed_no_adult_age", "seed.user_setting")])
        self.assertEqual(self._seed_tiers("Both characters are adults.",
                                          "Ines is 34."),
                         [("seed_no_numeric_age", "seed.setting_summary")])

    def test_bare_ages_near_age_words(self):
        cases = {
            "\u201cFifteen, maybe sixteen,\u201d she called out. \u201cOld enough "
            "to hold a pike.\u201d": "fifteen, maybe sixteen",
            "That's a young voice. Can't be more than sixteen, seventeen.":
                "can't be more than sixteen",
            "The boy was awake. He was maybe sixteen, maybe seventeen, all elbows.":
                "maybe sixteen",
            "one is a boy maybe sixteen with a bullet in the neck":
                "boy maybe sixteen",
            "\"Daniel Brandt. Seventeen. Went under at the ford. His mother has "
            "slept here since.\"": "seventeen",
            "a sharp-eyed girl of fourteen glanced up": "girl of fourteen",
            "Twenty years old, maybe less, holding himself shut":
                "twenty years old, maybe less",
        }
        for text, want in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self._terms(text, "bare_age")[:1], [want])

    def test_counts_and_quantities_are_not_bare_ages(self):
        for text in ("Ten minutes, maybe fifteen, if he's tough.",
                     "Twelve. Eleven. Thirteen. She checked the drainage tube.",
                     "sixteen men died at the ford",
                     "twelve years ago, maybe thirteen. Border skirmish.",
                     "\"Eleven,\" she said, and did not elaborate."):
            with self.subTest(text=text):
                self.assertEqual(self._terms(text, "bare_age"), [])

    def test_boy_or_girl_near_violence_is_the_soft_tier(self):
        self.assertEqual(self._terms("She looked at the boy's throat, and at the "
                                     "blade.", "boy_girl_violence"), ["the boy's"])
        self.assertEqual(self._terms("the dead girl lay in the ditch",
                                     "boy_girl_violence"), ["the dead girl"])
        for text in ("the boy sat by the fire and ate",          # no violence
                     "\"Do it now, boy.\" She drew her knife.",  # vocative
                     "good girl, she said, and bit his throat",  # endearment
                     "the little girl bled"):                    # child_term's
            with self.subTest(text=text):
                self.assertEqual(self._terms(text, "boy_girl_violence"), [])
        self.assertEqual(self._terms("the little girl bled", "child_term"),
                         ["little girl"])
        self.assertLess(E.TIER_ORDER["child_term"], E.TIER_ORDER["boy_girl_violence"])

    def test_review_list_never_lands_in_a_git_checkout(self):
        repo = self.d / "repo"
        (repo / ".git").mkdir(parents=True)
        with self.assertRaisesRegex(E.ExportError, "inside the git checkout"):
            E.write_review([], repo / "sub" / "youth.tsv")
        with self.assertRaises(E.ExportError):
            E.write_review([], ROOT / "youth.tsv")
        out = self.d / "outside" / "youth.tsv"
        E.write_review([{"tier": "minor_term", "term": "teen", "key": "k",
                         "seed_id": "s", "model": "m", "subtrack": "gore",
                         "message_index": 3, "role": "assistant",
                         "context": "a\tb"}], out)
        lines = out.read_text().splitlines()
        self.assertEqual(lines[0].split("\t")[:3], ["tier", "term", "key"])
        self.assertEqual(len(lines[1].split("\t")), 9)


class Destinations(unittest.TestCase):
    def test_outputs_never_land_in_the_benchmark_repo(self):
        for dest in (ROOT / "round-4.json", ROOT / "results" / "round-4-ladder"):
            with self.assertRaisesRegex(E.ExportError, "inside the benchmark repo"):
                E.refuse_benchmark_dest(dest, "x")
        E.refuse_benchmark_dest(Path(tempfile.gettempdir()) / "round-4.json", "x")

    def test_writes_refuse_without_dest(self):
        with self.assertRaisesRegex(E.ExportError, "without --dest"):
            E._write_json_file(None, {}, "board")


class PairDesign(unittest.TestCase):
    def setUp(self):
        # Seed sizes like the real round (odd and even), plus a small seed.
        self.by_seed = {
            "r4_a_intimacy_%02d" % i: ["m%02d" % j for j in range(n)]
            for i, n in ((1, 55), (2, 54), (3, 53), (4, 7))}
        self.by_seed["r4_a_gore_01"] = ["m%02d" % j for j in range(10, 40)]

    def test_deterministic_for_a_given_rng_seed(self):
        a = E.design_pairs(self.by_seed, 4, 4)
        self.assertEqual(a, E.design_pairs(self.by_seed, 4, 4))
        self.assertNotEqual(a, E.design_pairs(self.by_seed, 4, 5))

    def test_every_model_meets_r_opponents_per_seed(self):
        for r in (2, 3, 4, 6):
            with self.subTest(matchings=r):
                pairs = E.design_pairs(self.by_seed, r, 4)
                per = defaultdict(Counter)
                for seed, a, b in pairs:
                    self.assertLess(a, b)
                    per[seed][a] += 1
                    per[seed][b] += 1
                for seed, models in self.by_seed.items():
                    for m in models:
                        self.assertGreaterEqual(per[seed][m], min(r, len(models) - 1))
                        if r % 2 == 0:
                            self.assertEqual(per[seed][m], min(r, len(models) - 1))
                self.assertEqual(len(pairs), len(set(pairs)))

    def test_graph_is_connected(self):
        pairs = E.design_pairs(self.by_seed, 4, 4)
        self.assertTrue(E.pair_graph_connected(pairs))
        self.assertFalse(E.pair_graph_connected([("s", "a", "b"), ("s", "c", "d")]))

    def test_a_larger_design_only_appends(self):
        r4 = set(E.design_pairs(self.by_seed, 4, 4))
        r6 = set(E.design_pairs(self.by_seed, 6, 4))
        self.assertTrue(r4 < r6)

    def test_side_order_is_a_coin_from_the_id_not_the_alphabet(self):
        pairs = E.design_pairs(self.by_seed, 4, 4)
        listed, index = E.blind_pairs(KEY, "r4a-test", pairs)
        self.assertEqual(len(listed), len(pairs))
        alphabetical = sum(e["model_a"] < e["model_b"] for e in index.values())
        self.assertGreater(alphabetical, 0.35 * len(index))
        self.assertLess(alphabetical, 0.65 * len(index))
        self.assertEqual(E.blind_pairs(KEY, "r4a-test", pairs), (listed, index))

    def test_the_key_moves_every_id_and_about_half_the_coins(self):
        pairs = E.design_pairs(self.by_seed, 4, 4)
        _, one = E.blind_pairs(KEY, "r4a-test", pairs)
        _, two = E.blind_pairs(KEY2, "r4a-test", pairs)
        self.assertFalse(set(one) & set(two))
        side = lambda idx: {(e["seed_id"], e["model_a"], e["model_b"])
                            for e in idx.values()}
        flipped = len(side(one) - side(two))
        self.assertGreater(flipped, 0.35 * len(pairs))
        self.assertLess(flipped, 0.65 * len(pairs))
        # Nor are the sides the old public coin, sha256("sides|" + id): an
        # outsider computing that guesses side A no better than chance.
        def public_sides(pid, e):
            lo, hi = sorted((e["model_a"], e["model_b"]))
            coin = hashlib.sha256(("sides|" + pid).encode()).digest()[0] & 1
            return (hi, lo) if coin else (lo, hi)
        same = sum(public_sides(pid, e) == (e["model_a"], e["model_b"])
                   for pid, e in one.items())
        self.assertGreater(same, 0.35 * len(pairs))
        self.assertLess(same, 0.65 * len(pairs))

    def test_listed_in_id_order(self):
        listed, index = E.blind_pairs(KEY, "r4a-test",
                                      E.design_pairs(self.by_seed, 4, 4))
        ids = [p["id"] for p in listed]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(list(index), ids)
        # Seeds interleave: the design's grouping by seed is gone.
        seeds = [p["seed_id"] for p in listed]
        self.assertNotEqual(seeds, sorted(seeds))

    def test_pair_ids_survive_a_larger_design(self):
        _, small = E.blind_pairs(KEY, "r4a-test", E.design_pairs(self.by_seed, 4, 4))
        _, large = E.blind_pairs(KEY, "r4a-test", E.design_pairs(self.by_seed, 6, 4))
        self.assertTrue(set(small) < set(large))
        self.assertTrue(all(large[k] == v for k, v in small.items()))

    def test_one_seed_changing_does_not_reshuffle_the_others(self):
        before = E.design_pairs(self.by_seed, 4, 4)
        changed = dict(self.by_seed)
        changed["r4_a_intimacy_02"] = changed["r4_a_intimacy_02"][:-1]
        after = E.design_pairs(changed, 4, 4)
        keep = lambda ps: [p for p in ps if p[0] != "r4_a_intimacy_02"]
        self.assertEqual(keep(before), keep(after))


def _sessions_args(tmp):
    return argparse.Namespace(
        exclude=None, matchings=4, rng_seed=4, message_cap=E.MESSAGE_CAP,
        dest=str(Path(tmp) / "round-4-ladder"),
        review_out=str(Path(tmp) / "outside" / "youth.tsv"), replace=False)


class PairIdKey(unittest.TestCase):
    """PLOTPOINTS_PAIR_ID_SECRET: read from the environment by the exporter
    alone, no default, refused before anything is read, never written."""

    def test_the_key_comes_from_the_environment_with_no_default(self):
        self.assertEqual(E.PAIR_ID_SECRET_ENV, ENV)
        for env in ({}, {ENV: ""}, {ENV: "   "},
                    {ENV: "k" * (E.PAIR_ID_SECRET_MIN - 1)}):
            with self.subTest(length=len(env.get(ENV, ""))):
                with self.assertRaisesRegex(E.PairIdSecretError, ENV):
                    E.pair_id_secret(env)
        self.assertEqual(E.pair_id_secret({ENV: KEY.decode()}), KEY)
        with _without_key():
            with self.assertRaises(E.PairIdSecretError):
                E.pair_id_secret()
        with mock.patch.dict(os.environ, {ENV: KEY.decode()}):
            self.assertEqual(E.pair_id_secret(), KEY)
        self.assertTrue(issubclass(E.PairIdSecretError, E.ExportError))

    def test_a_refusal_never_echoes_the_key(self):
        short = "distinctive-short-k3y"
        with self.assertRaises(E.PairIdSecretError) as cm:
            E.pair_id_secret({ENV: short})
        self.assertNotIn(short, str(cm.exception))

    def test_only_pair_id_secret_reads_the_environment(self):
        tree = ast.parse((ROOT / "rounds/r4/export_plotpoints_round4.py").read_text())

        def env_reads(node):
            return [n for n in ast.walk(node) if isinstance(n, ast.Attribute)
                    and isinstance(n.value, ast.Name) and n.value.id == "os"
                    and n.attr in ("environ", "environb", "getenv", "getenvb")]
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "pair_id_secret")
        self.assertTrue(env_reads(fn))
        self.assertEqual(len(env_reads(tree)), len(env_reads(fn)))
        # The name is spelled once, as PAIR_ID_SECRET_ENV.
        self.assertEqual(sum(isinstance(n, ast.Constant) and n.value == ENV
                             for n in ast.walk(tree)), 1)
        # No flag takes it: a flag lands in shell history and ps.
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "add_argument"):
                flags = [a.value for a in n.args if isinstance(a, ast.Constant)]
                self.assertFalse([f for f in flags if "secret" in f or "key" in f],
                                 flags)

    def test_nothing_else_in_the_repo_reads_the_key(self):
        listed = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard",
             "--", "*.py"], capture_output=True, text=True, check=True).stdout
        readers = sorted(f for f in listed.split("\n") if f
                         and (ROOT / f).is_file()
                         and ENV in (ROOT / f).read_text(errors="replace"))
        self.assertEqual(readers, ["rounds/r4/export_plotpoints_round4.py",
                                   "tests/test_plotpoints_export.py"])

    def test_sessions_refuse_before_reading_anything(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        args = _sessions_args(tmp.name)
        touched = AssertionError("an input was read before the key")
        with mock.patch.object(E, "load_seeds", side_effect=touched), \
                mock.patch.object(E, "r4_paths", side_effect=touched):
            with self.assertRaisesRegex(E.PairIdSecretError, ENV):
                E.run_sessions(args, {"leaderboard": []}, "c", False, environ={})
            # --check: a failed guard (exit 1), so board and cards still run.
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertTrue(E.run_sessions(args, {"leaderboard": []}, "c",
                                               True, environ={}))
            self.assertIn(ENV, out.getvalue())
        self.assertEqual(list(Path(tmp.name).iterdir()), [])

    def test_main_refuses_before_git_or_any_input(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        args = _sessions_args(tmp.name)
        err = io.StringIO()
        touched = AssertionError("git or an input was read before the key")
        with _without_key(), contextlib.redirect_stderr(err), \
                mock.patch.object(E, "source_commit", side_effect=touched), \
                mock.patch.object(E, "_read_public_json", side_effect=touched):
            rc = E.main(["sessions", "--dest", args.dest,
                         "--review-out", args.review_out])
        self.assertEqual(rc, 2)
        self.assertIn(ENV, err.getvalue())
        self.assertEqual(list(Path(tmp.name).iterdir()), [])


class GuardModule(unittest.TestCase):
    NAMES = ("TEXT_FIELDS", "_guard_path", "_is_track_b", "_guard_record",
             "_read_public_json")

    def test_plotpoints_exporter_uses_the_shared_guards(self):
        for n in ("TEXT_FIELDS", "_guard_path", "_guard_record", "_read_public_json"):
            self.assertIs(getattr(E, n), getattr(PG, n), n)

    def test_hf_export_imports_the_guards_and_defines_none(self):
        tree = ast.parse((ROOT / "hf_dataset" / "export.py").read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "publication_guards":
                imported |= {a.name for a in node.names}
        self.assertTrue(set(self.NAMES) <= imported, imported)
        defined = {n.name for n in tree.body
                   if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        assigned = {t.id for n in tree.body if isinstance(n, ast.Assign)
                    for t in n.targets if isinstance(t, ast.Name)}
        self.assertFalse((defined | assigned) & set(self.NAMES + (
            "PublicationGuardError", "TRACK_B", "EVIDENCE_CAP", "_carries_text")))

    def test_hf_export_module_exposes_the_same_objects(self):
        try:
            import pyarrow  # noqa: F401
        except ImportError:
            self.skipTest("pyarrow is not installed in this interpreter")
        sys.path.insert(0, str(ROOT / "hf_dataset"))
        try:
            import export as hf_export
        finally:
            sys.path.remove(str(ROOT / "hf_dataset"))
        for n in self.NAMES + ("PublicationGuardError",):
            self.assertIs(getattr(hf_export, n), getattr(PG, n), n)

    def test_guard_module_is_dependency_free(self):
        tree = ast.parse((ROOT / "lib/publication_guards.py").read_text())
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                mods.add((node.module or "").split(".")[0])
        # Standard library only; hashlib/hmac/os are for voter_pseudonym.
        self.assertTrue(mods <= {"json", "pathlib", "hashlib", "hmac", "os"}, mods)

    def test_no_exporter_imports_the_private_loader(self):
        # harness/r4_private.py's load_r4 rejoins the private Track B text.
        for f in ("rounds/r4/export_plotpoints_round4.py", "lib/publication_guards.py",
                  "pipeline/generate_profile_cards_v2.py", "rounds/r4/make_j_barchart.py",
                  "lib/transcript_hash.py", "pipeline/generate_profile_cards.py"):
            mods = set()
            for node in ast.walk(ast.parse((ROOT / f).read_text())):
                if isinstance(node, ast.Import):
                    mods |= {a.name for a in node.names}
                elif isinstance(node, ast.ImportFrom):
                    mods.add(node.module or "")
            self.assertFalse({m for m in mods if m.startswith("harness")
                              or "r4_private" in m}, f)
        self.assertNotIn("harness", sys.modules.get("export_plotpoints_round4",
                                                    E).__dict__)
        self.assertFalse([m for m in sys.modules if "r4_private" in m])


def _head_results(dest):
    """HEAD copies of the card and board inputs, and the committed markdown.
    round4_overview.json and round4_continuity.json are the analyzers' output:
    the working-tree copy (what the export publishes once it is committed),
    HEAD's when there is none."""
    names = E.CARD_INPUTS + ("round4_willingness_leaderboard.json",
                             "profile_cards_v2.md")
    (dest / "results").mkdir()
    for n in names:
        blob = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:results/%s" % n],
                              capture_output=True, check=True).stdout
        (dest / "results" / n).write_bytes(blob)
    for name in (E.OVERVIEW_NAME, E.CONTINUITY_NAME):
        if (E.RESULTS / name).exists():
            (dest / "results" / name).write_bytes((E.RESULTS / name).read_bytes())
            continue
        head = subprocess.run(["git", "-C", str(ROOT), "show",
                               "HEAD:results/%s" % name], capture_output=True)
        if head.returncode == 0:
            (dest / "results" / name).write_bytes(head.stdout)
    return dest / "results"


class Cards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        try:
            cls.results = _head_results(Path(cls.tmp.name))
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            cls.tmp.cleanup()
            raise unittest.SkipTest("no git HEAD copies of the card inputs: %s" % e)
        cls.lb = json.loads((cls.results / "round4_willingness_leaderboard.json")
                            .read_text())
        cls.ctx = G.load_inputs(cls.results, r4=G.r4_rows(cls.lb))
        cls.cards = [G.build_card(m, cls.ctx) for m in G.ordered_models(cls.ctx)]
        if not (cls.results / E.CONTINUITY_NAME).exists():
            cls.tmp.cleanup()
            raise unittest.SkipTest("no %s; run rounds/r4/analyze_round4_continuity.py"
                                    % E.CONTINUITY_NAME)
        cls.cont = E.read_continuity(cls.results)
        cls.doc, _ = E.build_cards(cls.lb, cls.results, commit="test")
        cls.ov = E.read_overview(cls.results)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_markdown_is_byte_identical_to_the_committed_cards(self):
        want = (self.results / "profile_cards_v2.md").read_bytes()
        got = G.render_markdown_file(self.cards).encode("utf-8")
        self.assertEqual(got, want)

    def test_r4_json_and_analyzer_rows_agree_on_the_empty_warning(self):
        flagged = [c["id"] for c in self.cards
                   if c["willingness"] and c["willingness"]["empty"]["silent_flag"]]
        md = (self.results / "profile_cards_v2.md").read_text()
        self.assertEqual(len(flagged), md.count("  Empty replies  "))

    def test_card_json(self):
        cards = self.doc["cards"]
        self.assertEqual(len(cards), len(self.cards))
        self.assertEqual(len(cards), len(self.ctx["verdicts"]))
        lb_models = {r["model"] for r in self.lb["leaderboard"]}
        for mid, c in cards.items():
            with self.subTest(model=mid):
                self.assertEqual(set(c), E.CARD_KEYS)
                self.assertTrue(c["name"])
                self.assertTrue(c["vendor"])
                self.assertEqual(c["willingness"] is not None, mid in lb_models)
                for part in ("craft", "subjective"):
                    if c[part] is not None:
                        self.assertNotIn("mean", set(E._all_keys(c[part])))
                if c["craft"] is not None:
                    self.assertEqual(set(c["craft"]), E.CRAFT_KEYS)
                    self.assertTrue(all(isinstance(x, int) for x in
                                        c["craft"]["filled"] + c["craft"]["axis"]))
                if c["production_defects"] is not None:
                    self.assertNotIn("examples", c["production_defects"])
                    self.assertNotIn("_examples", c["production_defects"])
                self.assertFalse(any(k.startswith("_") for k in E._all_keys(c)))
                self.assertIsNone(c["elo"])
                self.assertIsNone(c["composite"])
        self.assertEqual(E.check_cards(self.doc, self.lb), [])
        self.assertEqual(E.check_cards(self.doc, self.lb, overview=self.ov), [])
        self.assertEqual(E.check_cards(self.doc, self.lb, overview=self.ov,
                                       continuity=self.cont), [])

    def test_judge_rows_come_from_the_overview_to_one_decimal(self):
        jm = self.ov["judge_means"]["models"]
        cards = self.doc["cards"]
        for mid, c in cards.items():
            with self.subTest(model=mid):
                self.assertEqual(c["judge"] is not None, mid in jm)
                if c["judge"] is None:
                    continue
                j, e = c["judge"], jm[mid]
                self.assertEqual(set(j), E.JUDGE_KEYS)
                self.assertEqual(j["tier"], e["tier"])
                for k, src in E.JUDGE_COLUMNS:
                    self.assertEqual(j[k], E.one_decimal(e[src]))
                    self.assertLessEqual(j[k], e[src] + 1e-9)
                    self.assertLess(e[src] - j[k], 0.1)
                    self.assertEqual(j[k], round(j[k], 1))
                self.assertEqual((j["n_sessions"], j["n_seeds"]),
                                 (e["n_sessions"], e["n_seeds"]))
                if j["tier"] is None:
                    self.assertTrue(j["note"])
        blob = json.dumps({"t": self.doc["judge_table"],
                           "j": [c["judge"] for c in cards.values()]})
        for gone in ('"edge', '"spans"', "mean_lo", "mean_hi", "_plain"):
            self.assertNotIn(gone, blob)

    def test_judge_rows_carry_the_second_judge_from_the_overview(self):
        rows = E.second_judge_rows(self.ov)
        top = self.ov["cross_judges"]["chatgpt"]
        for mid, c in self.doc["cards"].items():
            j = c["judge"]
            if j is None:
                continue
            with self.subTest(model=mid):
                cell = rows[mid]
                self.assertEqual(j["chatgpt_overall"], E.one_decimal(cell["mean"]))
                self.assertLessEqual(j["chatgpt_overall"], cell["mean"] + 1e-9)
                self.assertLess(cell["mean"] - j["chatgpt_overall"], 0.1)
                if j["tier"] is None:
                    self.assertIsNone(j["chatgpt_tier"])
                    self.assertIsNone(j["tier_depends_on_judge"])
                else:
                    self.assertEqual(j["chatgpt_tier"], cell["tier"])
                    self.assertIs(j["tier_depends_on_judge"], cell["tier_depends_on_judge"])
                    self.assertEqual(j["tier_depends_on_judge"],
                                     mid in top["tier_depends_on_judge"])
        t = self.doc["judge_table"]
        self.assertEqual(t["second_judge"], "ChatGPT via Codex (subscription, blind)")
        self.assertEqual(t["scale_offset"], round(top["scale_offset"]["value"], 2))
        self.assertIn("Second judge: ChatGPT via Codex (subscription, blind)", t["note"])
        self.assertIn("neither judge is shown to be the right one", t["note"])
        blob = json.dumps([c["judge"] for c in self.doc["cards"].values()])
        for gone in ('"difference"', '"flag"', "tier_after_offset", "overall_after_offset"):
            self.assertNotIn(gone, blob)

    def test_check_catches_every_break_of_the_second_judge(self):
        mid = next(m for m, c in self.doc["cards"].items() if c["judge"] and c["judge"]["tier"])
        untiered = next((m for m, c in self.doc["cards"].items()
                         if c["judge"] and not c["judge"]["tier"]), None)

        def broken(fn):
            doc = json.loads(json.dumps(self.doc))
            fn(doc)
            return E.check_cards(doc, self.lb, overview=self.ov)

        cases = {
            "two decimals": lambda d: d["cards"][mid]["judge"].update(chatgpt_overall=2.85),
            "rounded up": lambda d: d["cards"][mid]["judge"].update(
                chatgpt_overall=round(d["cards"][mid]["judge"]["chatgpt_overall"] + 0.1, 1)),
            "no letter": lambda d: d["cards"][mid]["judge"].update(chatgpt_tier=None),
            "a letter outside the five": lambda d: d["cards"][mid]["judge"].update(chatgpt_tier="F"),
            "flag not a bool": lambda d: d["cards"][mid]["judge"].update(tier_depends_on_judge="yes"),
            "flag flipped": lambda d: d["cards"][mid]["judge"].update(
                tier_depends_on_judge=not d["cards"][mid]["judge"]["tier_depends_on_judge"]),
            "the offset-adjusted letter leaks": lambda d: d["cards"][mid]["judge"].update(
                tier_after_offset="A"),
            "no second judge in the header": lambda d: d["judge_table"].pop("second_judge"),
            "another second judge": lambda d: d["judge_table"].update(second_judge="Gemini"),
            "offset to three decimals": lambda d: d["judge_table"].update(scale_offset=0.943),
        }
        if untiered:
            cases["an untiered row with a letter"] = (
                lambda d: d["cards"][untiered]["judge"].update(chatgpt_tier="C"))
        for name, fn in cases.items():
            with self.subTest(name):
                self.assertTrue(broken(fn), name)

    def test_an_overview_without_the_second_judge_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            ov = json.loads(json.dumps(self.ov))
            ov["cross_judges"] = {}
            (Path(t) / E.OVERVIEW_NAME).write_text(json.dumps(ov))
            with self.assertRaisesRegex(E.ExportError, "second judge"):
                E.read_overview(t)
            ov = json.loads(json.dumps(self.ov))
            ov["rows"][0]["cross_judges"] = {}
            (Path(t) / E.OVERVIEW_NAME).write_text(json.dumps(ov))
            with self.assertRaisesRegex(E.ExportError, "no ChatGPT mean"):
                E.read_overview(t)

    def test_roster_snapshot_2026_09_26(self):
        """The roster Levi signed off on; update when a model is added."""
        cards = self.doc["cards"]
        judged = {m: c["judge"] for m, c in cards.items() if c["judge"]}
        self.assertEqual(len(cards), 70)
        self.assertEqual(len(judged), 70)          # 69 tiered + mistral_small_2603
        self.assertEqual(sum(1 for j in judged.values() if j["tier"]), 69)
        mistral = judged["mistral_small_2603"]
        self.assertEqual((mistral["tier"], mistral["note"], mistral["n_seeds"]),
                         (None, "4 of 20 seeds", 4))
        for gone in ("fugu_max", "rocinante_12b"):
            self.assertNotIn(gone, cards)
            self.assertNotIn(gone, self.ov["judge_means"]["models"])
        older = set(self.ov["counts"]["j_not_in_round_4_models"])
        self.assertEqual(len(older), 13)
        self.assertTrue(all(judged[m]["tier"] for m in older))
        self.assertEqual({j["n_seeds"] for m, j in judged.items() if j["tier"]}, {12, 20})

    def test_judge_table_header(self):
        t = self.doc["judge_table"]
        self.assertEqual(set(t), E.JUDGE_TABLE_KEYS)
        self.assertEqual(t["judge"], "claude-sonnet-5 (session judge v2)")
        self.assertEqual(t["scale"], "1-5")
        self.assertEqual(t["not_comparable_with"], "Round 03 judge (Sonnet 4)")
        self.assertEqual([(b["tier"], b["lower"], b["upper"], b["label"]) for b in t["bands"]],
                         [("A", 3.8, None, "3.8 and above"), ("B", 3.2, 3.8, "3.2-3.8"),
                          ("C", 2.6, 3.2, "2.6-3.2"), ("D", 2.0, 2.6, "2.0-2.6"),
                          ("E", None, 2.0, "below 2.0")])
        self.assertIn("Sonnet 5", t["note"])
        self.assertIn("Not comparable with Round 03", t["note"])
        self.assertIn("not the flaw hunter", t["note"])
        self.assertEqual(E.copy_problems(t, "judge_table"), [])
        self.assertEqual(self.doc["inputs"]["judge"], "round4_overview.json")

    def test_check_catches_every_break_of_the_judge_table(self):
        mid = next(m for m, c in self.doc["cards"].items() if c["judge"] and c["judge"]["tier"])

        def broken(fn):
            doc = json.loads(json.dumps(self.doc))
            fn(doc)
            return E.check_cards(doc, self.lb, overview=self.ov)

        cases = {
            "edge": lambda d: d["cards"][mid]["judge"].update(edge=True),
            "two decimals": lambda d: d["cards"][mid]["judge"].update(overall=3.85),
            "a letter outside the five": lambda d: d["cards"][mid]["judge"].update(tier="F"),
            "untiered with no note": lambda d: d["cards"][mid]["judge"].update(tier=None),
            "not the overview's value": lambda d: d["cards"][mid]["judge"].update(
                agency=1.0 if d["cards"][mid]["judge"]["agency"] != 1.0 else 2.0),
            "dropped row": lambda d: d["cards"][mid].update(judge=None),
            "no header": lambda d: d.pop("judge_table"),
            "a moved band": lambda d: d["judge_table"]["bands"][0].update(lower=4.1),
            "another judge": lambda d: d["judge_table"].update(judge="sonnet 4"),
            "edge in the header": lambda d: d["judge_table"].update(edge_models=[]),
        }
        for name, fn in cases.items():
            with self.subTest(name):
                self.assertTrue(broken(fn), name)

    def test_one_decimal_rounds_down_and_stays_in_its_tier(self):
        self.assertEqual([E.one_decimal(v) for v in (3.25, 3.795, 2.595, 4.38, 3.749, 5.0, 3.8, 3.2)],
                         [3.2, 3.7, 2.5, 4.3, 3.7, 5.0, 3.8, 3.2])

    def test_an_overview_with_other_ranges_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            ov = json.loads(json.dumps(self.ov))
            ov["bands"]["ranges"][0]["lower"] = 4.1
            (Path(t) / E.OVERVIEW_NAME).write_text(json.dumps(ov))
            with self.assertRaisesRegex(E.ExportError, "frozen letters"):
                E.read_overview(t)
            ov = json.loads(json.dumps(self.ov))
            ov["judge_means"]["judge"] = "api-gemini"
            (Path(t) / E.OVERVIEW_NAME).write_text(json.dumps(ov))
            with self.assertRaisesRegex(E.ExportError, "judge_means"):
                E.read_overview(t)

    def test_the_markdown_still_carries_what_the_json_drops(self):
        md = (self.results / "profile_cards_v2.md").read_text()
        self.assertIn("    leak: ", md)
        blob = json.dumps(self.doc, ensure_ascii=False)
        self.assertNotIn("leak: ", blob)
        self.assertNotIn("\u2014", blob)

    def test_public_summary_drops_judge_scores(self):
        cases = {
            "Strong on tone consistency (4.58/5)": "Strong on tone consistency",
            "Top-1 on flaw hunter (74.9/100)": "Top-1 on flaw hunter",
            "Catastrophic floor on agency respect (lowest session: 3.1)":
                "Catastrophic floor on agency respect",
            "Strong on lore consistency (4.60/5; within 0.3 of the rest of the "
            "top -- an independent judge reorders this)":
                "Strong on lore consistency (within 0.3 of the rest of the top; "
                "an independent judge reorders this)",
            "Lowest phrase repetition (0.015 vs population 0.060)":
                "Lowest phrase repetition (0.015 vs population 0.060)",
        }
        for src, want in cases.items():
            self.assertEqual(G.public_summary(src), want)
        with self.assertRaises(ValueError):
            G.public_summary("Mean craft 61.5/100 overall")

    def test_board(self):
        board = E.build_board(self.lb, commit="test", continuity=self.cont)
        self.assertEqual(E.check_board(board), [])
        self.assertEqual(E.check_board(board, continuity=self.cont), [])
        ranked = [r for r in board["rows"] if r["ranked"]]
        self.assertEqual([r["rank"] for r in ranked], list(range(1, len(ranked) + 1)))
        for r in board["rows"]:
            self.assertEqual(set(r), E.BOARD_ROW_KEYS)
            self.assertFalse(set(E._all_keys(r)) & set(PG.TEXT_FIELDS))
            self.assertIsNone(r["elo"])
            if not r["ranked"]:
                self.assertIsNone(r["rank"])
                self.assertTrue(r["unranked_reason"])
        # gaps 4: "B-hard" is in the definitions, and the board still passes.
        self.assertIn("B-hard", json.dumps(board))
        self.assertEqual(len(board["rows"]), len(self.lb["leaderboard"]))

    def test_board_and_card_willingness_are_one_implementation(self):
        board = {r["model"]: r for r in E.build_board(
            self.lb, continuity=self.cont)["rows"]}
        for mid, c in self.doc["cards"].items():
            if c["willingness"] is None:
                continue
            for k in ("J", "held_first", "held_under_pressure", "empty",
                      "over_refusal_hard_rungs", "tied_with"):
                self.assertEqual(c["willingness"][k], board[mid][k], (mid, k))

    # -- continuity (round4_continuity.json) --------------------------------

    def test_across_rounds_come_from_the_continuity_file(self):
        rows = {r["model"]: r for r in self.cont["rows"]}
        cards = self.doc["cards"]
        self.assertEqual(set(self.doc["across_rounds_table"]), E.ACROSS_TABLE_KEYS)
        self.assertEqual(self.doc["inputs"]["across_rounds"], E.CONTINUITY_NAME)
        for mid, c in cards.items():
            with self.subTest(model=mid):
                a = c["across_rounds"]
                self.assertEqual(set(a), E.ACROSS_KEYS)
                self.assertEqual(a, E.across_rounds(self.cont, mid))
                self.assertEqual(a["returning"], mid in rows)
                if not a["returning"]:
                    self.assertEqual((a["rounds"], a["r2_human"], a["r3_nsfw"],
                                      a["transcripts"]), ([], None, None, "new_in_round4"))
                b = a["old_judge_band"]
                if b is not None:
                    self.assertEqual(set(b), E.OLD_JUDGE_BAND_KEYS)
                    self.assertEqual((b["mean"], b["half_width"]),
                                     (round(b["mean"], 2), round(b["half_width"], 2)))
        # every card but rocinante's (it has none) of the 41 returning models
        self.assertEqual(sum(c["across_rounds"]["returning"] for c in cards.values()), 40)
        self.assertNotIn("rocinante_12b", cards)
        self.assertIsNone(cards["mistral_small_2603"]["across_rounds"]["old_judge_band"])
        self.assertEqual(cards["kimi_k2_6"]["across_rounds"]["r2_human"]["voted_transcripts"],
                         "regenerated since the vote")
        new = [m for m, c in cards.items() if not c["across_rounds"]["returning"]]
        self.assertEqual(len(new), 30)
        self.assertTrue(all(cards[m]["across_rounds"]["old_judge_band"] for m in new))
        blob = json.dumps([c["across_rounds"] for c in cards.values()])
        for gone in ('"low"', '"high"', "old_judge_rank", '"position"', "translated"):
            self.assertNotIn(gone, blob)

    def test_board_continuity_columns(self):
        board = E.build_board(self.lb, commit="test", continuity=self.cont)
        bands = self.cont["old_judge"]["models"]
        r3 = {r["model"]: r["r3_nsfw"] for r in self.cont["rows"] if r["r3_nsfw"]}
        for r in board["rows"]:
            with self.subTest(model=r["model"]):
                self.assertEqual(r["old_judge_band"] is not None, r["model"] in bands)
                self.assertEqual(r["r3_nsfw_rank"] is not None, r["model"] in r3)
                if r["r3_nsfw_rank"]:
                    self.assertEqual(set(r["r3_nsfw_rank"]), E.R3_RANK_KEYS)
                    self.assertEqual(r["r3_nsfw_rank"]["rank"], r3[r["model"]]["rank"])
        self.assertIsNone({r["model"]: r for r in board["rows"]}["rocinante_12b"]
                          ["old_judge_band"])
        for k in ("old_judge_band", "r3_nsfw_rank"):
            self.assertIn(k, board["notes"])
            self.assertIn("rank" if k == "old_judge_band" else "published",
                          board["notes"][k])
        self.assertEqual(E.copy_problems(board["notes"], "notes"), [])

    def test_check_catches_every_break_of_the_continuity_fields(self):
        mid = "claude_opus_4_7"
        board = E.build_board(self.lb, commit="test", continuity=self.cont)
        bi = next(i for i, r in enumerate(board["rows"]) if r["model"] == mid)

        def broken_card(fn):
            doc = json.loads(json.dumps(self.doc))
            fn(doc["cards"][mid]["across_rounds"], doc)
            return E.check_cards(doc, self.lb, overview=self.ov, continuity=self.cont)

        def broken_board(fn):
            b = json.loads(json.dumps(board))
            fn(b["rows"][bi])
            return E.check_board(b, continuity=self.cont)

        cards = {
            "a rank on the old judge": lambda a, d: a["old_judge_band"].update(rank=3),
            "an interval end": lambda a, d: a["old_judge_band"].update(low=4.4),
            "three decimals": lambda a, d: a["old_judge_band"].update(mean=4.537),
            "a translation": lambda a, d: a.update(translated=4.4),
            "a composite": lambda a, d: a.update(composite=71.0),
            "another figure": lambda a, d: a["old_judge_band"].update(mean=4.11),
            "returning without a round": lambda a, d: a.update(rounds=[]),
            "a new model with round-3 fields": lambda a, d: d["cards"]["claude_opus_5"]
                ["across_rounds"].update(r3_nsfw=a["r3_nsfw"]),
            "an unknown transcripts flag": lambda a, d: a.update(transcripts="yes"),
            "dropped block": lambda a, d: d["cards"][mid].pop("across_rounds"),
            "no header": lambda a, d: d.pop("across_rounds_table"),
        }
        for name, fn in cards.items():
            with self.subTest(name):
                self.assertTrue(broken_card(fn), name)
        rows = {
            "a rank on the old judge": lambda r: r["old_judge_band"].update(rank=3),
            "three decimals": lambda r: r["old_judge_band"].update(half_width=0.071),
            "a rank outside its tie": lambda r: r["r3_nsfw_rank"].update(tie="5-9"),
            "not the continuity value": lambda r: r["r3_nsfw_rank"].update(rank=4),
            "a bare number": lambda r: r.update(old_judge_band=4.54),
        }
        for name, fn in rows.items():
            with self.subTest(name):
                self.assertTrue(broken_board(fn), name)

    def test_a_continuity_file_from_another_judge_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(E.ExportError, "missing"):
                E.read_continuity(t)
            c = json.loads(json.dumps(self.cont))
            c["old_judge"]["judge"] = "anthropic/claude-sonnet-5"
            (Path(t) / E.CONTINUITY_NAME).write_text(json.dumps(c))
            with self.assertRaisesRegex(E.ExportError, "old_judge"):
                E.read_continuity(t)
            c = json.loads(json.dumps(self.cont))
            next(iter(c["old_judge"]["models"].values()))["rank"] = 1
            c["old_judge"]["models"][next(iter(c["old_judge"]["models"]))]["old_judge_rank"] = 1
            (Path(t) / E.CONTINUITY_NAME).write_text(json.dumps(c))
            with self.assertRaisesRegex(E.ExportError, "carries"):
                E.read_continuity(t)

    def test_across_rounds_is_null_safe(self):
        cont = {"old_judge": {"models": {}}, "rows": [], "core_seeds": {"seeds": ["a", "b"]}}
        self.assertEqual(E.across_rounds(cont, "brand_new"), {
            "returning": False, "rounds": [], "old_judge_band": None, "r2_human": None,
            "r3_nsfw": None, "transcripts": "new_in_round4"})
        self.assertIsNone(E.old_judge_band(cont, "brand_new"))
        self.assertIsNone(E.r3_nsfw_rank(cont, "brand_new"))


class RealTrackA(unittest.TestCase):
    """The tracked round-4 files, if present: the dedupe must be the one the
    J board was scored on."""

    @classmethod
    def setUpClass(cls):
        paths = E.r4_paths()
        if not paths:
            raise unittest.SkipTest("no results/r4_full_*.json")
        cls.lb = PG._read_public_json(E.LEADERBOARD)
        lb = cls.lb
        cls.roster = sorted(r["model"] for r in lb["leaderboard"] if r["ranked"])
        counts = {r["model"]: r["n_sessions_a"] for r in lb["leaderboard"]}
        cls.manifest, cls.index, cls.sessions, cls.report = E.build_sessions_export(
            paths, E.load_seeds(), cls.roster, secret=KEY, lb_counts=counts)

    def test_matches_the_leaderboard_and_passes_every_guard(self):
        self.assertEqual(self.report["problems"], [])
        problems, facts = E.check_sessions_export(self.manifest, self.index,
                                                  self.sessions, self.roster, 4,
                                                  secret=KEY)
        self.assertEqual(problems, [])
        self.assertEqual(facts["ids_keyed_and_verified"], facts["pairs"])
        self.assertEqual(facts["ids_unkeyed"], 0)
        self.assertTrue(facts["pairs_in_id_order"])
        self.assertEqual(sum(facts["excluded_by_code"].values()),
                         len(self.index["excluded"]))
        self.assertEqual(facts["models"], len(self.roster))
        self.assertEqual(facts["track_b_ids"], 0)
        self.assertEqual(facts["per_seed_min"], 4)
        self.assertEqual(facts["per_seed_max"], 4)
        self.assertTrue(facts["connected"])
        self.assertEqual(facts["pairs"], 2 * len(self.sessions))
        self.assertTrue(facts["blind"])
        self.assertGreater(facts["a_side_alphabetical"], 0.4 * facts["pairs"])
        self.assertLess(facts["a_side_alphabetical"], 0.6 * facts["pairs"])
        for sid in self.manifest["seeds"]:
            self.assertRegex(sid, E.SEED_ID_RE)

    def test_the_served_manifest_does_not_point_at_the_sources(self):
        blob = E.manifest_json(self.manifest).decode()
        self.assertEqual(set(self.manifest), E.MANIFEST_KEYS)
        self.assertTrue(self.index["source_files"])
        for name in self.index["source_files"]:
            self.assertNotIn(name, blob)
        for gone in ("r4_full_", "rng_seed", "source_commit", "Hamiltonian"):
            self.assertNotIn(gone, blob)
        for e in self.manifest["excluded"]:
            self.assertEqual(set(e), E.EXCLUDED_KEYS)
            self.assertIn(e["reason"], E.EXCLUSION_CODES)

    def test_check_run_passes_and_prints_no_key(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = io.StringIO()
        # The youth screen is covered above and costs ~20 s on the real set.
        with contextlib.redirect_stdout(out), \
                mock.patch.object(E, "youth_screen", return_value=[]):
            bad = E.run_sessions(_sessions_args(tmp.name), self.lb, "test", True,
                                 environ={ENV: KEY.decode()})
        self.assertFalse(bad, out.getvalue()[-2000:])
        self.assertIn("sessions guards: all guards pass", out.getvalue())
        for form in (KEY.decode(), KEY.hex()):
            self.assertNotIn(form, out.getvalue())
        self.assertEqual(list(Path(tmp.name).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
