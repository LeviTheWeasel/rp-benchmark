"""hf_dataset/export.py: the round-4 overview and continuity tables, the
multi-turn arena path, the blind-judge keymap refusal, --drop-voter-ids, and
the live votes source (the site's public round-1 CSV, which has no voter ids).

Run by path from the repo root, offline (no network, no real secret):
    python -m unittest tests/test_hf_round4_export.py

The guard tests need only the standard library. The export tests need pyarrow
and are skipped without it; run them under an interpreter that has it, as a
script (that venv has its own `tests` package, which shadows this directory
under -m unittest):
    /home/levi/ml/.venv/bin/python tests/test_hf_round4_export.py
The overview and continuity tests read the tracked results/round4_*.json and
the tracked README.md; the network is always a fake.
"""
import ast
import csv
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import publication_guards as PG  # noqa: E402

ENV = "PLOTPOINTS_VOTER_HMAC_SECRET"
RESULTS = ROOT / "results"
KEYMAP = RESULTS / "judge_full_chatgpt" / "_manifest.json"
RAW_IDS = ("4b573b59-fb63-452a-91e2-00000000000a",
           "dd1a1cf8-21b8-4075-82d5-00000000000b")
# Throwaway key for these tests only; never export with it.
KEY = b"unit-test-throwaway-voter-key-not-for-export"


def _without_secret():
    env = {k: v for k, v in os.environ.items() if k != ENV}
    return mock.patch.dict(os.environ, env, clear=True)


def _load(name):
    with open(RESULTS / name) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Guards (standard library only)
# ---------------------------------------------------------------------------

class KeymapGuard(unittest.TestCase):
    def test_the_keymap_path_is_refused_wherever_it_sits(self):
        for p in (KEYMAP, Path("results/judge_full_chatgpt/_manifest.json"),
                  Path("judge_full_chatgpt/_manifest.json"),
                  RESULTS / "judge_full_chatgpt" / "merged" / "_manifest.json",
                  Path("/tmp/out/judge_full_chatgpt/app_pass/_MANIFEST.json")):
            with self.subTest(p=p):
                with self.assertRaisesRegex(PG.PublicationGuardError, "keymap"):
                    PG._guard_path(p)

    def test_refused_before_a_byte_is_read(self):
        missing = RESULTS / "judge_full_chatgpt" / "nowhere" / "_manifest.json"
        with self.assertRaises(PG.PublicationGuardError):
            PG._read_public_json(missing)          # not FileNotFoundError

    def test_tracked_manifests_and_public_files_pass(self):
        # Manifests of imported runs are tracked in the repo; only the pending
        # package's keymap is local-only.
        for p in (RESULTS / "judge_inc1_gemini" / "_manifest.json",
                  RESULTS / "external_judge_package" / "_manifest.json",
                  RESULTS / "judge_full_chatgpt" / "TASK.md",
                  RESULTS / "round4_overview.json",
                  Path("analysis/round4_continuity.json")):
            with self.subTest(p=p):
                PG._guard_path(p)

    def test_keymap_content_is_refused_under_any_name(self):
        for obj in ({"package": "x", "keymap": {"f001": "m::s"}},
                    {"wrap": [{"keymap": {}}]}):
            with self.subTest(obj=obj):
                with self.assertRaisesRegex(PG.PublicationGuardError, "keymap"):
                    PG._guard_keymap(obj, "analysis/renamed.json")
        PG._guard_keymap({"key_map_note": 1, "rows": [{"model": "m"}]}, "ok.json")

    @unittest.skipUnless(KEYMAP.exists(), "no local keymap in this checkout")
    def test_the_real_keymap_content_is_refused(self):
        with open(KEYMAP) as f:          # read here only to prove the guard
            doc = json.load(f)
        with self.assertRaises(PG.PublicationGuardError):
            PG._guard_keymap(doc, "anything.json")

    def test_the_keymap_stays_gitignored(self):
        lines = (ROOT / ".gitignore").read_text().splitlines()
        self.assertIn("results/judge_full_chatgpt/_manifest.json", lines)


class VoterIdGuard(unittest.TestCase):
    def test_raw_ids_are_refused_pseudonyms_and_blanks_pass(self):
        ok = PG.voter_pseudonym(KEY, RAW_IDS[0])
        PG._guard_voter_ids([{"voter_id": ok}, {"voter_id": ""},
                             {"voter_id": None}, {"vote_id": RAW_IDS[0]}], "v")
        for bad in (RAW_IDS[0], ok.upper(), ok[:-1], 12345,
                    {"nested": [{"voter_id": RAW_IDS[1]}]}):
            with self.subTest(bad=bad):
                obj = bad if isinstance(bad, dict) else [{"voter_id": bad}]
                with self.assertRaisesRegex(PG.PublicationGuardError, "voter_id"):
                    PG._guard_voter_ids(obj, "community_votes/train.parquet")

    def test_published_round4_json_carries_no_voter_id_or_keymap(self):
        for name in ("round4_overview.json", "round4_continuity.json",
                     "round4_judge_elo.json", "multiturn_arena_bayesian.json"):
            with self.subTest(name=name):
                doc = _load(name)
                PG._guard_voter_ids(doc, name)
                PG._guard_keymap(doc, name)
                PG._guard_record(doc, name)


class ExportSource(unittest.TestCase):
    """hf_dataset/export.py read as source: runs without pyarrow."""

    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse((ROOT / "hf_dataset" / "export.py").read_text())
        cls.funcs = {n.name: n for n in cls.tree.body
                     if isinstance(n, ast.FunctionDef)}

    def _constants(self, name):
        return {n.value for n in ast.walk(self.funcs[name])
                if isinstance(n, ast.Constant) and isinstance(n.value, str)}

    def test_the_drop_path_never_names_voter_id(self):
        for name in ("_vote_columns", "community_votes_table_without_voters"):
            with self.subTest(name=name):
                self.assertNotIn("voter_id", self._constants(name))

    def test_round4_exports_are_wired_in(self):
        body = ast.dump(self.funcs["export_round4"])
        for name in ("export_round4_overview", "export_round4_continuity"):
            self.assertIn("'%s'" % name, body)

    def test_the_multiturn_arena_is_on_the_analysis_whitelist(self):
        consts = self._constants("export_analysis_artifacts")
        self.assertIn("multiturn_arena_bayesian.json", consts)


class Card(unittest.TestCase):
    """hf_dataset/README.md lists the new configs and says what they are."""

    @classmethod
    def setUpClass(cls):
        cls.card = (ROOT / "hf_dataset" / "README.md").read_text()
        cls.front = cls.card.split("---", 2)[1]

    def test_new_configs_are_declared(self):
        for cfg in ("round4_overview", "round4_continuity"):
            with self.subTest(cfg=cfg):
                self.assertRegex(self.front, r"- config_name: %s\n  data_files:\n"
                                 r"  - split: train\n    path: %s/train.parquet"
                                 % (cfg, cfg))

    def test_every_declared_config_is_a_distinct_path(self):
        paths = re.findall(r"path: (\S+)", self.front)
        self.assertEqual(len(paths), len(set(paths)))

    def test_sections_and_the_votes_note(self):
        for heading in ("## Round 4 and earlier rounds",
                        "## Round 4 overview: judge tier, J, watch-out"):
            self.assertIn(heading, self.card)
        self.assertIn("`community_votes` has no voter id column", self.card)
        self.assertIn("There is no `voter_id` column", self.card)
        # The old judge is a band and the judge ELO is not a rank.
        self.assertIn("It is not a rank", self.card)
        self.assertIn("The judge ELO is not a rank", self.card)


# ---------------------------------------------------------------------------
# Export (pyarrow)
# ---------------------------------------------------------------------------

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


class _OutDir(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hf = _hf_export()
        import pyarrow as pa
        import pyarrow.parquet as pq
        cls.pa, cls.pq = pa, pq

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self._old_out = self.hf.OUT_DIR
        self.hf.OUT_DIR = self.out

    def tearDown(self):
        self.hf.OUT_DIR = self._old_out
        self.tmp.cleanup()

    def rows(self, *parts):
        return self.pq.read_table(self.out.joinpath(*parts)).to_pylist()


class Overview(_OutDir):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ov = _load("round4_overview.json")
        cls.jm = cls.ov["judge_means"]["models"]
        cls.built = cls.hf.round4_overview_rows(cls.ov)

    def test_one_row_per_model_tiered_untiered_absent(self):
        rows = self.built
        models = [r["model"] for r in rows]
        self.assertEqual(len(models), len(set(models)))
        want = ({r["model"] for r in self.ov["rows"]}
                | {r["model"] for r in self.ov["unranked"]}
                | {r["model"] for r in self.ov["absent"]})
        self.assertEqual(set(models), want)
        tiered = [r for r in rows if r["listed_as"] == "tiered"]
        self.assertEqual(len(tiered), self.ov["counts"]["tiered"])
        sizes = {t: sum(1 for r in tiered if r["judge_tier"] == t) for t in "ABCDE"}
        self.assertEqual(sizes, self.ov["bands"]["sizes"])
        for r in rows:
            if r["listed_as"] != "tiered":
                self.assertIsNone(r["judge_tier"], r["model"])
                self.assertTrue(r["reason"], r["model"])

    def test_order_is_tier_then_name_never_a_score(self):
        tiered = [r for r in self.built if r["listed_as"] == "tiered"]
        self.assertEqual([(r["judge_tier"], r["model"]) for r in tiered],
                         sorted((r["judge_tier"], r["model"]) for r in tiered))
        kinds = [r["listed_as"] for r in self.built]
        self.assertEqual(kinds, sorted(kinds, key=["tiered", "untiered",
                                                   "absent"].index))

    def test_no_elo_no_rank_no_sum(self):
        cols = set(self.built[0])
        for c in cols:
            self.assertNotRegex(c.lower(), r"elo|position|composite|sum|total",
                                c)
            if "rank" in c.lower():
                self.assertEqual(c, "J_unranked_reason")
        elo = {m["model"]: m for m in _load("round4_judge_elo.json")["models"]}
        # Not even an ELO value hiding under another name.
        for r in self.built:
            if r["model"] in elo:
                vals = {v for v in r.values() if isinstance(v, float)}
                self.assertNotIn(elo[r["model"]]["elo"], vals, r["model"])

    def test_judge_means_as_published(self):
        for r in self.built:
            m = self.jm.get(r["model"])
            if m is None:
                self.assertEqual(r["listed_as"], "absent")
                continue
            for col, key in self.hf.OVERVIEW_JUDGE_MEANS:
                self.assertEqual(r[col], m[key], (r["model"], col))
                self.assertEqual(r[col + "_plain"], m[key + "_plain"])
            self.assertEqual(r["judge_tier"], m["tier"])
            self.assertEqual(r["judge_n_sessions"], m["n_sessions"])
            if r["judge_tier"]:
                band = next(b for b in self.ov["bands"]["ranges"]
                            if b["tier"] == r["judge_tier"])
                self.assertGreaterEqual(r["judge_overall"], band["lower"] or 0)
                if band["upper"] is not None:
                    self.assertLess(r["judge_overall"], band["upper"])

    def test_J_matches_the_willingness_leaderboard(self):
        lb = {r["model"]: r for r in
              _load("round4_willingness_leaderboard.json")["leaderboard"]}
        seen = 0
        for r in self.built:
            if r["J_status"] == "not in round 4":
                self.assertNotIn(r["model"], lb)
                self.assertIsNone(r["J"])
                continue
            if r["model"] in lb and r["J"] is not None:
                self.assertAlmostEqual(r["J"], lb[r["model"]]["J"], places=3)
                self.assertEqual(r["J_status"] == "ranked",
                                 bool(lb[r["model"]]["ranked"]), r["model"])
                seen += 1
        # Every model with a J value in the overview, ranked or not.
        with_j = [m for m in self.ov["rows"] + self.ov["unranked"] + self.ov["absent"]
                  if (m.get("J") or {}).get("value") is not None]
        self.assertEqual(seen, len(with_j))
        self.assertEqual(sum(1 for r in self.built if r["J_status"] == "ranked"),
                         self.ov["counts"]["j_ranked"])

    def test_watch_out_counts_as_published(self):
        src = {r["model"]: r for r in self.ov["rows"] + self.ov["unranked"]}
        for r in self.built:
            if r["model"] not in src:
                continue
            w = src[r["model"]]["watch_out"]
            for k in self.hf.OVERVIEW_WATCH_COUNTS:
                self.assertEqual(r["watch_" + k], w["counts"][k], (r["model"], k))
            self.assertEqual(r["watch_blank_scenes"], len(w["counts"]["blank_scenes"]))
            self.assertEqual(r["watch_partial_scenes"],
                             len(w["counts"]["partial_scenes"]))
            self.assertEqual(r["watch_out"].split(",") if r["watch_out"] else [],
                             [s["key"] for s in w["shown"]])
        # counts.watch_out_rows counts the tiered rows.
        shown = sum(1 for r in self.built if r["watch_out"] and r["listed_as"] == "tiered")
        self.assertEqual(shown, self.ov["counts"]["watch_out_rows"])

    def test_refusals(self):
        def bad(mutate):
            ov = json.loads(json.dumps(self.ov))
            mutate(ov)
            with self.assertRaises(SystemExit):
                self.hf.round4_overview_rows(ov)
        bad(lambda ov: ov["rows"][0].update(elo=1600.0))
        bad(lambda ov: ov["rows"][0].update(rank_lo=1))
        bad(lambda ov: ov["judge_means"].update(judge="someone-else"))
        bad(lambda ov: ov["rows"][0]["judge_tier"].update(tier="E"))
        bad(lambda ov: ov["rows"].append(ov["rows"][0]))

    def test_export_writes_json_as_is_and_the_table(self):
        with mock.patch("sys.stdout", io.StringIO()):
            self.hf.export_round4_overview()
        for name in ("round4_overview.json", "round4_judge_elo.json"):
            self.assertEqual((self.out / "analysis" / name).read_bytes(),
                             (RESULTS / name).read_bytes(), name)
        self.assertEqual(self.rows("round4_overview", "train.parquet"), self.built)
        with mock.patch("sys.stdout", io.StringIO()):
            self.hf.audit_output()


class Continuity(_OutDir):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cont = _load("round4_continuity.json")
        cls.built = cls.hf.round4_continuity_rows(cls.cont)

    def _readme_table(self):
        text = (ROOT / "README.md").read_text()
        start = text.index("| Model | R2 human ELO [95%] (votes) |")
        rows = []
        for line in text[start:].splitlines()[2:]:
            if not line.startswith("|"):
                break
            rows.append([c.strip() for c in line.strip("|").split("|")])
        return rows

    def test_one_row_per_returning_model_in_the_readme_order(self):
        readme = self._readme_table()
        self.assertEqual(len(self.built), self.cont["roster"]["returning"])
        self.assertEqual([r["model"] for r in self.built], [c[0] for c in readme])

    def test_cells_match_the_readme_table(self):
        readme = {c[0]: c for c in self._readme_table()}
        for r in self.built:
            with self.subTest(model=r["model"]):
                _, h, r3, ref, old, tier, j, tx = readme[r["model"]]
                if r["old_judge_is_band"]:
                    self.assertEqual(old, "%.2f ± %.2f" % (
                        r["old_judge_band_mean"], r["old_judge_band_half_width"]))
                else:
                    self.assertEqual(old, "n/a (%s)" % r["old_judge_missing"])
                self.assertEqual(tier, r["r4_tier"] or "")
                if r["J_ranked"]:
                    self.assertEqual(j, "%s (#%d)" % (r["J_display"], r["J_rank"]))
                if r["r2_human_elo"] is None:
                    self.assertEqual(h, "")
                else:
                    self.assertTrue(h.startswith("%d [%d, %d] (%d)" % (
                        round(r["r2_human_elo"]), round(r["r2_human_ci95_low"]),
                        round(r["r2_human_ci95_high"]), r["r2_human_n_votes"])), h)
                if r["r3_nsfw_rank"] is None:
                    self.assertEqual(r3, "")
                else:
                    self.assertTrue(r3.startswith("#%d (%.2f" % (
                        r["r3_nsfw_rank"], r["r3_nsfw_craft"])), r3)
                    self.assertEqual(ref, "%g" % r["r3_refusal_pct"])
                if r["r4_transcripts"] == "same":
                    self.assertEqual(tx, "same as R2 (%d)" % r["r4_sessions"])
                elif r["r4_transcripts"] == "regenerated":
                    self.assertTrue(tx.startswith("regen. %s" %
                                                  r["r4_transcripts_generated"]))

    def test_old_judge_is_a_band_and_never_a_rank(self):
        cols = set(self.built[0])
        self.assertFalse({"low", "high", "old_judge_rank", "rank_old_judge",
                          "position"} & cols)
        for c in cols:
            if c.startswith("old_judge"):
                self.assertNotIn("rank", c)
        for r in self.built:
            if r["old_judge_is_band"]:
                self.assertIsNone(r["old_judge_missing"])
                for k in ("old_judge_band_mean", "old_judge_band_half_width"):
                    self.assertEqual(round(r[k], 2), r[k])
                self.assertGreater(r["old_judge_band_half_width"], 0)
            else:
                self.assertIsNone(r["old_judge_band_mean"])
                self.assertTrue(r["old_judge_missing"])
        # The same band the site's cards publish.
        import export_plotpoints_round4 as E
        for r in self.built:
            b = E.old_judge_band(self.cont, r["model"])
            if b is None:
                self.assertFalse(r["old_judge_is_band"])
            else:
                self.assertEqual((b["mean"], b["half_width"], b["n_sessions"]),
                                 (r["old_judge_band_mean"],
                                  r["old_judge_band_half_width"],
                                  r["old_judge_band_n_sessions"]))
        self.assertFalse(E.ACROSS_BANNED & cols)

    def test_no_key_the_continuity_analyzer_forbids(self):
        try:
            import analyze_round4_continuity as C
        except ImportError as e:
            self.skipTest("analyze_round4_continuity needs %s" % e.name)
        self.assertFalse(C.FORBIDDEN_KEYS & set(self.built[0]))

    def test_refusals(self):
        cont = json.loads(json.dumps(self.cont))
        cont["old_judge"]["judge"] = "anthropic/claude-sonnet-5"
        with self.assertRaises(SystemExit):
            self.hf.round4_continuity_rows(cont)
        with self.assertRaises(SystemExit):
            self.hf.round4_continuity_rows(dict(self.cont, rows=[]))

    def test_export_writes_json_as_is_and_the_table(self):
        with mock.patch("sys.stdout", io.StringIO()):
            self.hf.export_round4_continuity()
        self.assertEqual((self.out / "analysis" / "round4_continuity.json").read_bytes(),
                         (RESULTS / "round4_continuity.json").read_bytes())
        self.assertEqual(self.rows("round4_continuity", "train.parquet"), self.built)
        with mock.patch("sys.stdout", io.StringIO()):
            self.hf.audit_output()


class MultiturnArena(_OutDir):
    def test_the_refreshed_arena_flows_through_the_analysis_copy(self):
        with mock.patch("sys.stdout", io.StringIO()):
            self.hf.export_analysis_artifacts()
        out = self.out / "analysis" / "multiturn_arena_bayesian.json"
        self.assertEqual(out.read_bytes(),
                         (RESULTS / "multiturn_arena_bayesian.json").read_bytes())
        doc = json.loads(out.read_text())
        self.assertEqual(doc["n_votes"], 1943)
        self.assertIsNone(doc["n_voters"])
        # The continuity rows read the same file.
        cont = _load("round4_continuity.json")
        self.assertEqual(cont["human_arena"]["votes"], doc["n_votes"])
        with mock.patch("sys.stdout", io.StringIO()):
            self.hf.audit_output()

    def test_the_vote_file_carries_no_voter_ids(self):
        with open(ROOT / "data" / "multiturn_arena_votes.jsonl") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        self.assertTrue(rows)
        self.assertFalse([r for r in rows if "voter_id" in r])


class KeymapInExport(_OutDir):
    def test_copy_refuses_the_keymap_before_writing(self):
        with self.assertRaises(PG.PublicationGuardError):
            self.hf._copy_public(KEYMAP, "analysis", "judge.json")
        self.assertFalse((self.out / "analysis" / "judge.json").exists())

    def test_audit_refuses_a_planted_keymap_by_path_or_content(self):
        planted = self.out / "judge_full_chatgpt" / "_manifest.json"
        planted.parent.mkdir(parents=True)
        planted.write_text("{}")
        with self.assertRaises(PG.PublicationGuardError):
            self.hf.audit_output()
        planted.unlink()
        (self.out / "analysis").mkdir()
        (self.out / "analysis" / "notes.json").write_text(
            json.dumps({"keymap": {"f0001": "model::seed"}}))
        with self.assertRaisesRegex(PG.PublicationGuardError, "keymap"):
            self.hf.audit_output()


# ---------------------------------------------------------------------------
# --drop-voter-ids
# ---------------------------------------------------------------------------

def _no_network(*a, **kw):
    raise AssertionError("fetched votes")


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


SITE_URL = "https://plotlightstudios.com/api/plotpoints/raw?round=1&mode=arena"
SITE_COLUMNS = ("id", "round", "mode", "scenario_id", "context", "model_a",
                "model_b", "winner", "model", "scores", "notes", "is_catch",
                "catch_correct", "source", "signed_in", "client_timestamp",
                "created_at")


def _site_csv(votes, extra=()):
    """The site's raw export (round 1, arena) of these votes: its public
    columns, plus `extra` ones an id-bearing export would add (voter_id,
    ip_hash). The public export has none of them."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(SITE_COLUMNS + tuple(extra))
    for v in votes:
        cc = v.get("catch_correct")
        w.writerow([v["id"], v.get("round", 1), v.get("mode", "arena"),
                    v["scenario_id"], 'A scene, "quoted", with a comma',
                    v["model_a"], v["model_b"], v["winner"], "", "", "",
                    "true" if v.get("is_catch") else "false",
                    "" if cc is None else str(cc).lower(), "arena_test", "0",
                    v["client_timestamp"], "2026-04-14T19:17:00.1+00:00"]
                   + [v.get(k, "") for k in extra])
    return buf.getvalue().encode()


class DropVoterIds(_OutDir):
    # (the CSV's client_timestamp, the published timestamp)
    STAMPS = (("2026-04-14T19:16:56.291+00:00", "2026-04-14T19:16:56.291Z"),
              ("2026-04-14T19:34:23.37+00:00", "2026-04-14T19:34:23.370Z"),
              ("2026-04-14T21:35:03+02:00", "2026-04-14T19:35:03.000Z"),
              ("2026-04-14T19:35:12.643+00:00", "2026-04-14T19:35:12.643Z"))

    def setUp(self):
        super().setUp()
        self.votes = [{"id": "v%d" % i, "voter_id": RAW_IDS[i % 2], "mode": "arena",
                       "client_timestamp": self.STAMPS[i][0],
                       "timestamp": self.STAMPS[i][1], "scenario_id": "s%d" % i,
                       "model_a": "a", "model_b": "b", "winner": "AB"[i % 2],
                       "is_catch": i == 3, "catch_correct": True if i == 3 else None,
                       "ip_hash": "iphash", "user_agent": "ua"} for i in range(4)]
        # What the site serves, and an id-bearing export of the same votes
        # (the worst case: drop mode must still write no id).
        self.public = _site_csv(self.votes)
        self.with_ids = _site_csv(self.votes, ("voter_id", "ip_hash", "user_agent"))
        self.body = self.with_ids
        self.asked = []

    def _urlopen(self, req, *a, **kw):
        self.asked.append(getattr(req, "full_url", req))
        return _FakeResponse(self.body)

    def _no_network(self, *a, **kw):
        raise AssertionError("fetched votes")

    def _assert_clean(self, p):
        t = self.pq.read_table(p)
        self.assertEqual(tuple(t.schema.names), self.hf.VOTE_FIELDS)
        self.assertNotIn("voter_id", t.schema.names)
        blob = p.read_bytes()
        for raw in RAW_IDS:
            self.assertNotIn(raw.encode(), blob)
        self.assertNotIn(b"iphash", blob)
        return t.to_pylist()

    def test_table_has_the_vote_fields_and_no_voter_column(self):
        t = self.hf.community_votes_table_without_voters(self.votes[:4])
        self.assertEqual(tuple(t.schema.names), self.hf.VOTE_FIELDS)
        with_ids = self.hf.community_votes_table(self.votes[:4], KEY)
        self.assertEqual(with_ids.drop(["voter_id"]).to_pylist(), t.to_pylist())

    def test_the_live_source_is_the_sites_public_csv(self):
        self.assertEqual(self.hf.VOTES_URL, SITE_URL)

    def test_live_fetch_without_a_secret(self):
        with _without_secret(), mock.patch("urllib.request.urlopen", self._urlopen), \
                mock.patch("sys.stdout", io.StringIO()):
            self.hf.export_community_arena(drop_voter_ids=True)
        self.assertEqual(self.asked, [SITE_URL])
        rows = self._assert_clean(self.out / "community_votes" / "train.parquet")
        self.assertEqual([r["vote_id"] for r in rows], ["v0", "v1", "v2", "v3"])
        self.assertEqual([r["timestamp"] for r in rows],
                         [want for _, want in self.STAMPS])
        self.assertEqual([r["winner"] for r in rows], ["A", "B", "A", "B"])
        self.assertEqual(rows[3]["catch_correct"], True)
        self.assertEqual([r["catch_correct"] for r in rows[:3]], [None] * 3)
        # The same rows as the dicts the table is built from.
        self.assertEqual(
            rows, self.hf.community_votes_table_without_voters(self.votes).to_pylist())
        self.assertTrue((self.out / "community_arena" / "train.parquet").exists())

    def test_the_public_export_gives_the_same_table(self):
        self.body = self.public
        with _without_secret(), mock.patch("urllib.request.urlopen", self._urlopen), \
                mock.patch("sys.stdout", io.StringIO()):
            self.hf.export_community_arena(drop_voter_ids=True)
        rows = self._assert_clean(self.out / "community_votes" / "train.parquet")
        self.assertEqual(
            rows, self.hf.community_votes_table_without_voters(self.votes).to_pylist())

    def test_a_secret_does_not_bring_the_column_back(self):
        with mock.patch.dict(os.environ, {ENV: "k3y"}), \
                mock.patch("urllib.request.urlopen", self._urlopen), \
                mock.patch("sys.stdout", io.StringIO()):
            self.hf.export_community_arena(drop_voter_ids=True)
        self._assert_clean(self.out / "community_votes" / "train.parquet")

    def test_hmac_mode_refuses_the_public_export_and_writes_nothing(self):
        # Nothing to pseudonymize: stop, and say how to publish without ids.
        self.body = self.public
        with mock.patch.dict(os.environ, {ENV: "k3y"}), \
                mock.patch("urllib.request.urlopen", self._urlopen), \
                mock.patch("sys.stdout", io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                self.hf.export_community_arena()
        self.assertIn("--drop-voter-ids", str(cm.exception.code))
        self.assertIn("NOT rebuilt", str(cm.exception.code))
        self.assertEqual(list(self.out.iterdir()), [])

    def test_a_body_that_is_not_the_export_stops_in_either_mode(self):
        bodies = {
            "the old arena's JSON": json.dumps({"votes": self.votes}).encode(),
            "a row of another mode": _site_csv(
                self.votes + [{**self.votes[0], "id": "mt1",
                               "mode": "multiturn_arena"}]),
            "a winner outside A/B/tie": _site_csv([{**self.votes[0], "winner": "C"}]),
        }
        for what, body in bodies.items():
            for env in ({}, {ENV: "k3y"}):
                with self.subTest(what=what, hmac=bool(env)):
                    self.body = body
                    clean = {k: v for k, v in os.environ.items() if k != ENV}
                    with mock.patch.dict(os.environ, {**clean, **env}, clear=True), \
                            mock.patch("urllib.request.urlopen", self._urlopen), \
                            mock.patch("sys.stdout", io.StringIO()):
                        with self.assertRaises(SystemExit):
                            self.hf.export_community_arena(drop_voter_ids=not env)
                    self.assertEqual(list(self.out.iterdir()), [])

    def test_failed_fetch_stops_and_writes_nothing(self):
        def down(*a, **kw):
            raise OSError("certificate verify failed")
        with _without_secret(), mock.patch("urllib.request.urlopen", down), \
                mock.patch("sys.stdout", io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                self.hf.export_community_arena(drop_voter_ids=True)
        self.assertIn("NOT rebuilt", str(cm.exception.code))
        self.assertEqual(list(self.out.iterdir()), [])

    def test_hmac_mode_still_skips_on_a_failed_fetch(self):
        def down(*a, **kw):
            raise OSError("down")
        with mock.patch.dict(os.environ, {ENV: "k3y"}), \
                mock.patch("urllib.request.urlopen", down), \
                mock.patch("sys.stdout", io.StringIO()):
            self.hf.export_community_arena()
        self.assertFalse((self.out / "community_votes").exists())

    def _source_parquet(self):
        """A community_votes file shaped like the one published before the
        rebuild: raw voter ids in a voter_id column."""
        src = self.out / "src" / "train.parquet"
        src.parent.mkdir()
        arena = [v for v in self.votes if v["mode"] == "arena"]
        cols = self.hf._vote_columns(arena)
        table = self.pa.table({"vote_id": cols.pop("vote_id"),
                               "voter_id": [v["voter_id"] for v in arena], **cols})
        self.pq.write_table(table, src)
        return src, table

    def test_votes_from_a_local_parquet_never_reads_voter_id(self):
        src, table = self._source_parquet()
        real = self.pq.read_table
        asked = []

        def spy(path, *a, columns=None, **kw):
            asked.append(columns)
            return real(path, *a, columns=columns, **kw)
        with _without_secret(), mock.patch("urllib.request.urlopen", self._no_network), \
                mock.patch.object(self.hf.pq, "read_table", spy), \
                mock.patch("sys.stdout", io.StringIO()):
            self.hf.export_community_arena(drop_voter_ids=True, votes_from=src)
        self.assertTrue(asked)
        self.assertTrue(all(c is not None and "voter_id" not in c for c in asked))
        rows = self._assert_clean(self.out / "community_votes" / "train.parquet")
        self.assertEqual(rows, table.drop(["voter_id"]).to_pylist())

    def test_votes_from_needs_drop_mode_and_a_votes_file(self):
        src, _ = self._source_parquet()
        with mock.patch.dict(os.environ, {ENV: "k3y"}):
            with self.assertRaises(ValueError):
                self.hf.export_community_arena(votes_from=src)
        other = self.out / "src" / "other.parquet"
        self.pq.write_table(self.pa.table({"model": ["m"]}), other)
        with self.assertRaises(SystemExit):
            self.hf.read_votes_parquet(other)

    def test_audit_refuses_a_raw_id_table_and_passes_the_rebuilt_one(self):
        src, _ = self._source_parquet()
        dest = self.out / "community_votes" / "train.parquet"
        dest.parent.mkdir()
        dest.write_bytes(src.read_bytes())
        src.unlink()
        with self.assertRaisesRegex(PG.PublicationGuardError, "voter_id"):
            self.hf.audit_output()
        with _without_secret(), mock.patch("sys.stdout", io.StringIO()):
            self.hf.export_community_arena(drop_voter_ids=True, votes_from=dest)
            self.hf.audit_output()


class PublishedVotes(_OutDir):
    """The tracked hf_dataset/community_votes/train.parquet, rebuilt with no
    voter column from the site's public CSV: the same 2,013 votes."""

    PATH = ROOT / "hf_dataset" / "community_votes" / "train.parquet"
    UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-"
                      r"[0-9a-f]{12}", re.I)

    def test_no_voter_column_and_only_vote_ids_look_like_uuids(self):
        t = self.pq.read_table(self.PATH)
        self.assertEqual(tuple(t.schema.names), self.hf.VOTE_FIELDS)
        self.assertEqual(t.num_rows, 2013)
        ids = t.column("vote_id").to_pylist()
        self.assertEqual(len(set(ids)), 2013)
        for name in t.schema.names:
            if name != "vote_id":
                with self.subTest(column=name):
                    self.assertFalse([v for v in t.column(name).to_pylist()
                                      if isinstance(v, str) and self.UUID.search(v)])
        self.assertEqual(set(t.column("winner").to_pylist()), {"A", "B", "tie"})
        self.assertEqual(sum(t.column("is_catch").to_pylist()), 80)
        PG._guard_voter_ids(t.to_pylist(), "community_votes/train.parquet")

    def test_a_votes_from_rebuild_reproduces_it(self):
        with _without_secret(), mock.patch("sys.stdout", io.StringIO()), \
                mock.patch("urllib.request.urlopen", _no_network):
            self.hf.export_community_arena(drop_voter_ids=True, votes_from=self.PATH)
        rebuilt = self.pq.read_table(self.out / "community_votes" / "train.parquet")
        self.assertTrue(rebuilt.equals(self.pq.read_table(self.PATH)))

    def test_the_bayesian_arena_script_refuses_it(self):
        try:
            import numpy  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            self.skipTest("numpy and pandas are not installed here")
        import analyze_bayesian_arena_elo as B
        old = os.getcwd()
        os.chdir(ROOT)
        try:
            with self.assertRaises(SystemExit) as cm:
                B.load_votes()
        finally:
            os.chdir(old)
        self.assertIn("no voter_id column", str(cm.exception.code))


class Main(_OutDir):
    """The command line: which combinations refuse, and what drop mode runs."""

    def _main(self, *argv):
        with mock.patch.object(sys, "argv", ["export.py", *argv]), \
                mock.patch("sys.stderr", io.StringIO()) as err, \
                mock.patch("sys.stdout", io.StringIO()):
            try:
                self.hf.main()
            except SystemExit as e:
                return e.code, err.getvalue()
        return 0, err.getvalue()

    def test_conflicting_flags_refuse_before_writing(self):
        dest = self.out / "staging"
        src = self.out / "votes.parquet"
        self.pq.write_table(self.pa.table({"vote_id": ["v"]}), src)
        with _without_secret():
            for argv in (["--drop-voter-ids", "--offline"],
                         ["--drop-voter-ids", "--only", "round4"],
                         ["--votes-from", str(src)],
                         ["--drop-voter-ids", "--votes-from", str(self.out / "nope")]):
                with self.subTest(argv=argv):
                    code, err = self._main("--out", str(dest), *argv)
                    self.assertEqual(code, 2)
                    self.assertFalse(dest.exists())
            # No secret and no mode: refused, and the message names the way out.
            code, err = self._main("--out", str(dest))
            self.assertEqual(code, 2)
            self.assertIn("--drop-voter-ids", err)
            self.assertFalse(dest.exists())

    def test_drop_mode_needs_no_secret_and_runs_the_votes_first(self):
        dest = self.out / "staging"
        calls = []
        names = ("export_seeds", "export_adversarial_seeds", "export_rubric",
                 "export_results", "export_leaderboard", "export_elo",
                 "export_flaw_hunter_results", "export_community_arena",
                 "export_analysis_artifacts", "export_round4", "stage_card",
                 "audit_output")
        patches = [mock.patch.object(self.hf, n, side_effect=(
            lambda *a, _n=n, **kw: calls.append((_n, kw)))) for n in names]
        with _without_secret():
            for p in patches:
                p.start()
            try:
                code, err = self._main("--out", str(dest), "--drop-voter-ids")
            finally:
                for p in patches:
                    p.stop()
        self.assertEqual(code, 0, err)
        self.assertEqual(calls[0], ("export_community_arena",
                                    {"offline": False, "drop_voter_ids": True,
                                     "votes_from": None}))
        self.assertEqual([c[0] for c in calls][-3:],
                         ["export_round4", "stage_card", "audit_output"])


if __name__ == "__main__":
    unittest.main()
