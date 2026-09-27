"""The 2026-09-27 cleanups: newest-wins Sonnet-4 profiles, and the round-2
multi-turn arena rebuilt from the site's public CSV without voter ids.

Run by path from the repo root, offline (no network, no real secret):
    python -m unittest tests/test_arena_refresh_and_profiles.py
"""
import contextlib
import hashlib
import hmac
import io
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import analyze_model_profiles as P  # noqa: E402
import analyze_multiturn_arena as A  # noqa: E402
import refresh_multiturn_arena_votes as R  # noqa: E402

ENV = "PLOTPOINTS_VOTER_HMAC_SECRET"


@contextlib.contextmanager
def _in_tmp():
    old = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        try:
            yield Path(d)
        finally:
            os.chdir(old)


def _session(model, seed, overall=None):
    s = {"test_model": model, "seed_id": seed,
         "dialogue": [{"role": "character", "turn": 1, "content": "x"}]}
    if overall is not None:
        s["judges"] = {"claude_sonnet": {"scores": {
            "overall": overall,
            "session_dimensions": {
                "S.3_narrative_momentum": {"score": overall}}}}}
    return s


class ProfilesNewestWins(unittest.TestCase):
    SEED = "adv_agency_bait_01"

    def _run(self, merged, baselines):
        Path("results").mkdir()
        Path("results/multiturn_merged_all_v2.json").write_text(
            json.dumps({"sessions": merged}))
        for name, sessions in baselines.items():
            Path("results/%s" % name).write_text(
                json.dumps({"sessions": sessions}))
        Path("results/community_arena_2000.json").write_text(
            json.dumps({"leaderboard": []}))
        with mock.patch.object(sys, "argv", ["analyze_model_profiles.py"]), \
                contextlib.redirect_stdout(io.StringIO()):
            P.main()
        return json.loads(Path("results/model_profiles.json").read_text())

    def test_a_regenerated_session_never_reuses_the_superseded_verdict(self):
        with _in_tmp():
            prof = self._run(
                merged=[_session("regen", self.SEED, 2.0),
                        _session("kept", self.SEED, 4.0)],
                baselines={"craft_baseline_20260924_000000.json":
                           [_session("regen", self.SEED)]})
        # The current transcript has no Sonnet-4 verdict: unscored, not 2.0.
        self.assertNotIn("regen", prof)
        self.assertEqual(prof["kept"]["multiturn_llm_judge"]["overall_mean"], 4.0)

    def test_the_newest_file_wins_among_craft_baselines(self):
        with _in_tmp():
            prof = self._run(
                merged=[],
                baselines={
                    "craft_baseline_20260921_000000.json":
                        [_session("m", self.SEED, 3.0)],
                    "craft_baseline_20260926_000000.json":
                        [_session("m", self.SEED, 5.0)],
                    # An errored newer copy does not displace a real one.
                    "craft_baseline_20260927_000000.json":
                        [{"test_model": "m", "seed_id": self.SEED,
                          "error": "timeout"}]})
        m = prof["m"]
        self.assertEqual(m["multiturn_llm_judge"],
                         {"overall_mean": 5.0, "n_sessions": 1})


class SpearmanFallback(unittest.TestCase):
    def test_matches_the_closed_form_t_test(self):
        # df = 2: two-sided p = 1 - |t| / sqrt(t^2 + 2); rho 0.8 gives 0.2.
        rho, p = A._spearmanr([1, 2, 3, 4], [1, 3, 2, 4])
        self.assertAlmostEqual(rho, 0.8, places=12)
        self.assertAlmostEqual(p, 0.2, places=12)
        # df = 1: p = 1 - (2/pi) atan(|t|).
        rho, p = A._spearmanr([1, 2, 3], [1, 3, 2])
        t = abs(rho) * math.sqrt(1 / (1 - rho * rho))
        self.assertAlmostEqual(p, 1 - 2 / math.pi * math.atan(t), places=12)

    def test_ties_get_average_ranks(self):
        rho, _ = A._spearmanr([1, 1, 2, 3], [1, 2, 3, 4])
        self.assertAlmostEqual(rho, 0.9486832980505138, places=12)


CSV_HEAD = ("id,round,mode,scenario_id,context,model_a,model_b,winner,model,"
            "scores,notes,is_catch,catch_correct,source,signed_in,"
            "client_timestamp,created_at\n")


def _csv_row(i, a="m1", b="m2", rnd="2", mode="multiturn_arena",
             source="native"):
    ts = "2026-05-0%dT00:00:00+00:00" % (i + 1)
    return ("%s,%s,%s,mt_s_%s_vs_%s,ctx,%s,%s,A,,,,false,,%s,0,%s,%s\n"
            % ("v%d" % i, rnd, mode, a, b, a, b, source, ts, ts))


class ArenaRefresh(unittest.TestCase):
    def _refresh(self, csv_text, previous, env):
        Path("data").mkdir(exist_ok=True)
        Path("site.csv").write_text(csv_text)
        if previous is not None:
            Path("data/multiturn_arena_votes.jsonl").write_text(
                "".join(json.dumps(r) + "\n" for r in previous))
        clean = {k: v for k, v in os.environ.items() if k != ENV}
        clean.update(env)
        with mock.patch.dict(os.environ, clean, clear=True), \
                mock.patch.object(R, "ARCHIVE_VOTES", 2), \
                mock.patch.object(R, "ARCHIVE_PAIRS", 1), \
                mock.patch.object(sys, "argv", ["x", "--csv", "site.csv",
                                                "--fetched-at", "T"]), \
                contextlib.redirect_stdout(io.StringIO()):
            R.main()
        return [json.loads(l) for l in
                open("data/multiturn_arena_votes.jsonl") if l.strip()]

    PREVIOUS = [
        {"id": "v0", "model_a": "m1", "model_b": "m2", "winner": "A",
         "voter_id": "4b573b59-fb63-452a-91e2-000000000001",
         "source": "native", "server_timestamp": "2026-05-01T00:00:00Z"},
        {"id": "old", "model_a": "m1", "model_b": "m2", "winner": "B",
         "voter_id": "4b573b59-fb63-452a-91e2-000000000002",
         "source": "arena_l3vi4th4n_only",
         "server_timestamp": "2026-04-30T11:32:14.995Z"},
    ]

    def test_no_voter_id_is_written_without_the_secret(self):
        with _in_tmp():
            rows = self._refresh(CSV_HEAD + _csv_row(0) + _csv_row(1),
                                 self.PREVIOUS, {})
            readme = Path("data/multiturn_arena_votes.README.md").read_text()
        self.assertEqual([r["id"] for r in rows], ["old", "v0", "v1"])
        self.assertFalse(any("voter_id" in r for r in rows))
        self.assertIn("sha256", readme)
        self.assertIn(R.URL, readme)

    def test_known_raw_ids_become_hmac_pseudonyms_with_the_secret(self):
        with _in_tmp():
            rows = self._refresh(CSV_HEAD + _csv_row(0) + _csv_row(1),
                                 self.PREVIOUS, {ENV: "k3y"})
        by_id = {r["id"]: r for r in rows}
        want = hmac.new(b"k3y", self.PREVIOUS[0]["voter_id"].encode(),
                        hashlib.sha256).hexdigest()
        self.assertEqual(by_id["v0"]["voter_id"], want)
        self.assertNotIn("voter_id", by_id["v1"])     # the CSV has none
        self.assertEqual(len(by_id["old"]["voter_id"]), 64)
        blob = json.dumps(rows)
        for r in self.PREVIOUS:
            self.assertNotIn(r["voter_id"], blob)

    def test_refuses_rows_from_another_round_or_mode(self):
        for bad in (_csv_row(1, rnd="3"), _csv_row(1, mode="arena")):
            with self.subTest(bad=bad), _in_tmp():
                with self.assertRaises(SystemExit):
                    self._refresh(CSV_HEAD + _csv_row(0) + bad, None, {})

    def test_the_analyzer_leaves_legacy_only_rows_unscored(self):
        with _in_tmp():
            self._refresh(CSV_HEAD + _csv_row(0) + _csv_row(1),
                          self.PREVIOUS, {})
            with mock.patch.object(A, "VOTES_FILE",
                                   Path("data/multiturn_arena_votes.jsonl")):
                ids = [r["id"] for r in A.load_rows()]
        self.assertEqual(ids, ["v0", "v1"])


if __name__ == "__main__":
    unittest.main()
