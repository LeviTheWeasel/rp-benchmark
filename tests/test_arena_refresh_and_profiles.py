"""The 2026-09-27 cleanups: newest-wins Sonnet-4 profiles, and the round-2
multi-turn arena rebuilt from the site's public CSV without voter ids. And
the 2026-09-28 move off the old arena domain: the single-message votes come
from the site's public round-1 CSV (fetch_arena_votes.py), the scripts that
need voter ids refuse on it, and nothing links to or fetches from the old
domain.

Run by path from the repo root, offline (no network, no real secret):
    python -m unittest tests/test_arena_refresh_and_profiles.py
"""
import contextlib
import csv
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

import analyze_community_arena as C  # noqa: E402
import analyze_model_profiles as P  # noqa: E402
import analyze_multiturn_arena as A  # noqa: E402
import analyze_voter_quality as VQ  # noqa: E402
import fetch_arena_votes as F  # noqa: E402
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

    def test_the_provenance_note_is_the_tracked_readmes(self):
        # The tracked README is the template's output: the note on the legacy
        # rows reads the same in both, with no link to the old domain.
        tracked = (ROOT / "data" / "multiturn_arena_votes.README.md").read_text()
        start = tracked.index("`: ballots cast on ")
        note = tracked[start:tracked.index("keeps them unscored.", start)]
        with _in_tmp():
            self._refresh(CSV_HEAD + _csv_row(0) + _csv_row(1), self.PREVIOUS, {})
            readme = Path("data/multiturn_arena_votes.README.md").read_text()
        self.assertIn(note, readme)
        self.assertIn("no longer controls", note)
        self.assertNotIn("://", note)


# ---------------------------------------------------------------------------
# The single-message arena: the site's public round-1 CSV
# ---------------------------------------------------------------------------

SITE_URL = "https://plotlightstudios.com/api/plotpoints/raw?round=1&mode=arena"
SITE_COLUMNS = CSV_HEAD.strip().split(",")
RAW_VOTER = "4b573b59-fb63-452a-91e2-00000000000c"


def _arena_csv(rows, extra=()):
    """The site's round-1 arena export: one CSV row per dict of cells, over
    defaults. `extra` adds columns the public export does not have."""
    base = {"round": "1", "mode": "arena",
            "scenario_id": "completion_x_1_m1_vs_m2",
            "context": 'A scene, with "quotes",\nand a second line.',
            "model_a": "m1", "model_b": "m2", "winner": "A", "model": "",
            "scores": "", "notes": "", "is_catch": "false", "catch_correct": "",
            "source": "arena_round_01", "signed_in": "0",
            "client_timestamp": "2026-04-14T19:16:56.291+00:00",
            "created_at": "2026-04-14T19:16:56.758+00:00"}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=SITE_COLUMNS + list(extra),
                       lineterminator="\r\n")
    w.writeheader()
    for i, r in enumerate(rows):
        w.writerow({**base, "id": "v%d" % i, **r})
    return buf.getvalue().encode()


class _Site:
    """A stand-in for urllib.request.urlopen: serves one body, records URLs."""

    def __init__(self, body):
        self.body, self.asked = body, []

    def __call__(self, req, *a, **kw):
        self.asked.append((getattr(req, "full_url", req),
                           dict(getattr(req, "headers", {}))))
        return contextlib.closing(io.BytesIO(self.body))


def _no_network(*a, **kw):
    raise AssertionError("tried the network")


class ArenaVotesCsv(unittest.TestCase):
    STAMPS = (("2026-04-14T19:16:56.291+00:00", "2026-04-14T19:16:56.291Z"),
              ("2026-04-14T19:16:56.29+00:00", "2026-04-14T19:16:56.290Z"),
              ("2026-04-14T19:16:56+00:00", "2026-04-14T19:16:56.000Z"),
              ("2026-04-14T21:16:56.5+02:00", "2026-04-14T19:16:56.500Z"),
              ("2026-06-13T15:24:01.61933+00:00", "2026-06-13T15:24:01.619330Z"),
              ("", ""))

    def test_the_urls_are_the_sites_public_round1_export(self):
        self.assertEqual(F.ARENA_CSV_URL, SITE_URL)
        self.assertEqual(C.DEFAULT_URL, SITE_URL)

    def test_timestamps_become_the_arena_logs_utc_z_form(self):
        for raw, want in self.STAMPS:
            with self.subTest(raw=raw):
                self.assertEqual(F.iso_utc(raw), want)
        with self.assertRaises(ValueError):
            F.iso_utc("2026-04-14T19:16:56")        # no offset: not guessed

    def test_rows_map_to_the_arena_log_shape(self):
        rows = [{"client_timestamp": raw} for raw, _ in self.STAMPS]
        rows[1].update(winner="B", is_catch="true", catch_correct="false")
        rows[2].update(winner="tie", is_catch="true", catch_correct="true")
        votes = F.votes_from_csv(_arena_csv(rows))
        self.assertEqual([v["id"] for v in votes], ["v%d" % i for i in range(6)])
        self.assertEqual([v["timestamp"] for v in votes],
                         [want for _, want in self.STAMPS])
        self.assertEqual([v["winner"] for v in votes][:3], ["A", "B", "tie"])
        self.assertEqual([v["is_catch"] for v in votes][:3], [False, True, True])
        self.assertEqual([v["catch_correct"] for v in votes][:3],
                         [None, False, True])
        v = votes[0]
        self.assertEqual((v["mode"], v["round"], v["model_a"], v["model_b"]),
                         ("arena", 1, "m1", "m2"))
        self.assertEqual(v["server_timestamp"], "2026-04-14T19:16:56.758Z")
        self.assertEqual(v["context"], 'A scene, with "quotes",\nand a second line.')
        self.assertIs(v["signed_in"], False)
        self.assertFalse([v for v in votes if "voter_id" in v])
        self.assertFalse(F.carries_voter_ids(votes))

    def test_a_voter_id_column_is_passed_through(self):
        votes = F.votes_from_csv(_arena_csv(
            [{"voter_id": RAW_VOTER}, {"voter_id": ""}], extra=("voter_id",)))
        self.assertEqual(votes[0]["voter_id"], RAW_VOTER)
        self.assertNotIn("voter_id", votes[1])
        self.assertTrue(F.carries_voter_ids(votes))

    def test_refuses_what_is_not_the_export(self):
        bad = {"the old JSON api": b'{"votes": [{"id": "v0", "mode": "arena"}]}',
               "another round": _arena_csv([{}, {"round": "2"}]),
               "another mode": _arena_csv([{}, {"mode": "multiturn_arena"}]),
               "a winner outside A/B/tie": _arena_csv([{"winner": "C"}]),
               "a duplicate id": _arena_csv([{}, {"id": "v0"}]),
               "a flag that is not a boolean": _arena_csv([{"is_catch": "maybe"}])}
        for what, body in bad.items():
            with self.subTest(what=what):
                with self.assertRaises(SystemExit):
                    F.votes_from_csv(body)

    def test_main_reads_a_saved_copy_without_the_network(self):
        with _in_tmp(), mock.patch("urllib.request.urlopen", _no_network), \
                contextlib.redirect_stdout(io.StringIO()):
            Path("site.csv").write_bytes(_arena_csv([{}, {"winner": "B"}]))
            with mock.patch.object(sys, "argv", ["x", "--csv", "site.csv"]):
                F.main()
            rows = [json.loads(l) for l in
                    Path("web/data/votes.jsonl").read_text().splitlines()]
        self.assertEqual([r["winner"] for r in rows], ["A", "B"])
        self.assertFalse([r for r in rows if "voter_id" in r])

    def test_main_fetches_the_site_export_only(self):
        site = _Site(_arena_csv([{}]))
        with _in_tmp(), mock.patch("urllib.request.urlopen", site), \
                mock.patch.object(sys, "argv", ["x", "--out", "v.jsonl"]), \
                contextlib.redirect_stdout(io.StringIO()):
            F.main()
            self.assertEqual(len(Path("v.jsonl").read_text().splitlines()), 1)
        self.assertEqual([u for u, _ in site.asked], [SITE_URL])
        self.assertIn("User-agent", site.asked[0][1])


class ArenaScriptsNeedVoterIds(unittest.TestCase):
    """The public CSV has no voter ids; the per-voter scripts stop on it."""

    def test_community_arena_refuses_the_public_export_and_writes_nothing(self):
        site = _Site(_arena_csv([{}, {"is_catch": "true", "catch_correct": "true"}]))
        with _in_tmp(), mock.patch("urllib.request.urlopen", site), \
                mock.patch.object(sys, "argv", ["x", "--out", "out.json"]), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                C.main()
            self.assertFalse(Path("out.json").exists())
        self.assertIn("voter id", str(cm.exception.code))
        self.assertEqual([u for u, _ in site.asked], [SITE_URL])

    def test_community_arena_still_runs_on_a_log_with_voter_ids(self):
        rows = [{"voter_id": "p%d" % (i % 2), "winner": "AB"[i % 2]}
                for i in range(4)]
        rows.append({"voter_id": "p0", "is_catch": "true",
                     "catch_correct": "true", "scenario_id": "catch_x"})
        with _in_tmp(), mock.patch("urllib.request.urlopen", _no_network), \
                contextlib.redirect_stdout(io.StringIO()):
            Path("ids.csv").write_bytes(_arena_csv(rows, extra=("voter_id",)))
            with mock.patch.object(sys, "argv", ["x", "--file", "ids.csv",
                                                 "--out", "out.json"]):
                C.main()
            out = json.loads(Path("out.json").read_text())
        self.assertEqual((out["total_arena_votes"], out["unique_voters"],
                          out["catch_votes"]), (5, 2, 1))

    def test_voter_quality_refuses_a_log_with_no_voter_ids(self):
        with _in_tmp(), contextlib.redirect_stdout(io.StringIO()):
            with open("votes.jsonl", "w") as f:
                for v in F.votes_from_csv(_arena_csv([{}, {"is_catch": "true"}])):
                    f.write(json.dumps(v) + "\n")
            with mock.patch.object(sys, "argv", ["x", "votes.jsonl"]):
                with self.assertRaises(SystemExit) as cm:
                    VQ.main()
        self.assertIn("voter id", str(cm.exception.code))


class OldArenaDomain(unittest.TestCase):
    """The old arena domain (HOST) is no longer the project's: it serves a
    third party's certificate. No file links to it or fetches from it, as a
    URL or a percent-encoded badge URL; a bare, unlinked mention in a
    provenance note and the data labels that carry its name are fine."""

    HOST = "arena.l3vi4th4n.ai"
    SUFFIXES = {".py", ".md", ".toml", ".cfg", ".ini", ".txt", ".json",
                ".jsonl", ".csv", ".yml", ".yaml", ".html", ".js", ".mjs",
                ".ts", ".tsx"}
    SKIP_DIRS = {".git", "__pycache__", "node_modules", "results", ".next"}

    def test_nothing_links_to_or_fetches_from_it(self):
        needles = ("://" + self.HOST, "%2F%2F" + self.HOST, "%2f%2f" + self.HOST)
        hits = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in self.SKIP_DIRS
                           and (not d.startswith(".") or d == ".github")]
            for name in filenames:
                p = Path(dirpath) / name
                if p.suffix not in self.SUFFIXES:
                    continue
                text = p.read_text(errors="replace")
                hits += ["%s: %s" % (p.relative_to(ROOT), n)
                         for n in needles if n in text]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
