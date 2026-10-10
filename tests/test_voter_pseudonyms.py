"""Voter ids: published raw by default; HMAC pseudonyms and no column are options.

Voter ids are random per-voter UUIDs that exist to catch vote stuffing, so the
exports publish them raw unless asked for HMAC-SHA256 pseudonyms
(--voter-ids hmac, PLOTPOINTS_VOTER_HMAC_SECRET) or no column (--voter-ids drop).

Run by path from the repo root, offline (no network, no real secret):
    python -m unittest tests/test_voter_pseudonyms.py

The helper tests need only the standard library. The hf_dataset/export.py
tests need pyarrow and are skipped without it; run them under an interpreter
that has it, e.g. /home/levi/ml/.venv/bin/python tests/test_voter_pseudonyms.py
"""
import ast
import csv
import hashlib
import hmac
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import publication_guards as PG  # noqa: E402

ENV = "PLOTPOINTS_VOTER_HMAC_SECRET"
RAW_IDS = ("4b573b59-fb63-452a-91e2-000000000001",
           "dd1a1cf8-21b8-4075-82d5-000000000002")


def _without_secret():
    env = {k: v for k, v in os.environ.items() if k != ENV}
    return mock.patch.dict(os.environ, env, clear=True)


class Helpers(unittest.TestCase):
    def test_the_secret_comes_from_the_environment_with_no_default(self):
        self.assertEqual(PG.VOTER_HMAC_ENV, ENV)
        for env in ({}, {ENV: ""}, {ENV: "   "}):
            with self.subTest(env=env):
                with self.assertRaisesRegex(PG.VoterSecretError, ENV):
                    PG.voter_secret(env)
        self.assertEqual(PG.voter_secret({ENV: "k3y"}), b"k3y")
        with _without_secret():
            with self.assertRaises(PG.VoterSecretError):
                PG.voter_secret()
        # A refusal is a publication-guard refusal.
        self.assertTrue(issubclass(PG.VoterSecretError, PG.PublicationGuardError))

    def test_pseudonym_is_hmac_sha256_of_the_raw_id(self):
        want = hmac.new(b"k3y", RAW_IDS[0].encode(), hashlib.sha256).hexdigest()
        self.assertEqual(PG.voter_pseudonym(b"k3y", RAW_IDS[0]), want)
        self.assertEqual(len(want), 64)
        self.assertNotEqual(PG.voter_pseudonym(b"other", RAW_IDS[0]), want)
        self.assertNotEqual(PG.voter_pseudonym(b"k3y", RAW_IDS[1]), want)
        # Not a bare hash: without the key, sha256(id) does not match.
        self.assertNotEqual(hashlib.sha256(RAW_IDS[0].encode()).hexdigest(), want)

    def test_missing_ids_stay_empty_and_an_empty_key_refuses(self):
        self.assertEqual(PG.voter_pseudonym(b"k3y", ""), "")
        self.assertEqual(PG.voter_pseudonym(b"k3y", None), "")
        with self.assertRaises(PG.VoterSecretError):
            PG.voter_pseudonym(b"", RAW_IDS[0])


class ExportSource(unittest.TestCase):
    """hf_dataset/export.py, read as source: runs without pyarrow."""

    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / "hf_dataset" / "export.py").read_text()
        cls.tree = ast.parse(cls.src)

    def _func(self, name):
        return next(n for n in self.tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == name)

    def test_every_pseudonymized_read_goes_through_voter_pseudonym(self):
        # In the hmac branch the raw id is only ever read inside voter_pseudonym.
        f = self._func("community_votes_table")
        calls = [n for n in ast.walk(f) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "voter_pseudonym"]
        self.assertEqual(len(calls), 1)

    def test_the_hmac_secret_is_checked_before_the_network(self):
        f = self._func("export_community_arena")
        calls = {}
        for node in ast.walk(f):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                calls.setdefault(name, node.lineno)
        self.assertLess(calls["voter_secret"], calls["urlopen"])
        # The variable is read in one place, publication_guards.voter_secret,
        # which has no default; this file never reads the environment.
        self.assertFalse([n for n in ast.walk(self.tree)
                          if isinstance(n, ast.Constant) and n.value == ENV])
        self.assertFalse([n for n in ast.walk(self.tree)
                          if isinstance(n, ast.Attribute) and n.attr == "environ"])


def _hf_export():
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        raise unittest.SkipTest("pyarrow is not installed in this interpreter")
    sys.path.insert(0, str(ROOT / "hf_dataset"))
    try:
        import export as hf_export
    finally:
        sys.path.remove(str(ROOT / "hf_dataset"))
    return hf_export


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _id_bearing_csv(votes):
    """The site's raw export format, with its voter_id column."""
    cols = ("id", "round", "mode", "scenario_id", "context", "model_a",
            "model_b", "winner", "model", "scores", "notes", "is_catch",
            "catch_correct", "source", "signed_in", "client_timestamp",
            "created_at", "voter_id")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\r\n")
    w.writeheader()
    for v in votes:
        w.writerow({"id": v["id"], "round": 1, "mode": v["mode"],
                    "scenario_id": v.get("scenario_id", ""), "context": "",
                    "model_a": v.get("model_a", ""), "model_b": v.get("model_b", ""),
                    "winner": v["winner"], "is_catch": "false", "source": "test",
                    "signed_in": "0",
                    "client_timestamp": "2026-01-01T00:00:00+00:00",
                    "created_at": "2026-01-01T00:00:01+00:00",
                    "voter_id": v.get("voter_id", "")})
    return buf.getvalue().encode()


class Export(unittest.TestCase):
    """The real export functions, offline: the network is a fake."""

    @classmethod
    def setUpClass(cls):
        cls.hf = _hf_export()
        import pyarrow.parquet as pq
        cls.pq = pq

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self._old_out = self.hf.OUT_DIR
        self.hf.OUT_DIR = self.out
        self.votes = [{"id": "v%d" % i, "voter_id": RAW_IDS[i % 2], "mode": "arena",
                       "timestamp": "2026-01-01", "scenario_id": "s", "model_a": "a",
                       "model_b": "b", "winner": "A"} for i in range(4)]
        self.votes.append({"id": "v9", "mode": "arena", "winner": "B"})  # no voter id

    def tearDown(self):
        self.hf.OUT_DIR = self._old_out
        self.tmp.cleanup()

    def _urlopen(self, *a, **kw):
        return _FakeResponse(_id_bearing_csv(self.votes))

    def test_raw_is_the_default_and_keeps_the_ids(self):
        rows = self.hf.community_votes_table(self.votes).to_pylist()
        self.assertEqual([r["voter_id"] for r in rows],
                         [RAW_IDS[i % 2] for i in range(4)] + [""])
        self.assertEqual(list(rows[0])[:2], ["vote_id", "voter_id"])

    def test_hmac_mode_carries_pseudonyms_only(self):
        rows = self.hf.community_votes_table(self.votes, "hmac", b"k3y").to_pylist()
        self.assertEqual([r["voter_id"] for r in rows],
                         [PG.voter_pseudonym(b"k3y", RAW_IDS[i % 2]) for i in range(4)]
                         + [""])
        self.assertFalse(set(RAW_IDS) & set(json.dumps(rows).split('"')))

    def test_drop_mode_has_no_voter_column(self):
        table = self.hf.community_votes_table(self.votes, "drop")
        self.assertNotIn("voter_id", table.column_names)

    def test_default_export_writes_raw_ids_without_a_secret(self):
        with _without_secret(), mock.patch("urllib.request.urlopen", self._urlopen):
            self.hf.export_community_arena(offline=False)
        p = self.out / "community_votes" / "train.parquet"
        ids = self.pq.read_table(p).column("voter_id").to_pylist()
        self.assertEqual(ids[:2], list(RAW_IDS))

    def test_hmac_export_refuses_without_a_secret_before_any_fetch(self):
        def no_network(*a, **kw):
            raise AssertionError("fetched votes without a secret")
        with _without_secret(), mock.patch("urllib.request.urlopen", no_network):
            with self.assertRaises(PG.VoterSecretError):
                self.hf.export_community_arena(offline=False, voter_ids="hmac")
        self.assertFalse((self.out / "community_votes").exists())
        # --offline fetches nothing and needs no secret.
        with _without_secret(), mock.patch("urllib.request.urlopen", no_network):
            self.hf.export_community_arena(offline=True, voter_ids="hmac")

    def test_hmac_export_writes_no_raw_ids(self):
        with mock.patch.dict(os.environ, {ENV: "k3y"}), \
                mock.patch("urllib.request.urlopen", self._urlopen):
            self.hf.export_community_arena(offline=False, voter_ids="hmac")
        p = self.out / "community_votes" / "train.parquet"
        ids = self.pq.read_table(p).column("voter_id").to_pylist()
        self.assertEqual(ids[:2], [PG.voter_pseudonym(b"k3y", r) for r in RAW_IDS])
        blob = p.read_bytes()
        for raw in RAW_IDS:
            self.assertNotIn(raw.encode(), blob)

    def test_main_hmac_refuses_before_writing_anything(self):
        dest = self.out / "staging"
        with _without_secret(), mock.patch.object(
                sys, "argv", ["export.py", "--out", str(dest), "--voter-ids", "hmac"]), \
                mock.patch("sys.stderr", io.StringIO()) as err:
            with self.assertRaises(SystemExit) as cm:
                self.hf.main()
        self.assertEqual(cm.exception.code, 2)
        self.assertIn(ENV, err.getvalue())
        self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
