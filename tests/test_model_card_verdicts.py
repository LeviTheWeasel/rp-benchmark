import json
from pathlib import Path
import re
import tempfile
import unittest

from pipeline.generate_profile_cards_v2 import format_verdict, load_verdicts


ROOT = Path(__file__).resolve().parents[1]


class ModelCardVerdictsTest(unittest.TestCase):
    def test_all_current_cards_have_matching_short_verdicts(self):
        verdicts = load_verdicts(ROOT / "results/model_card_verdicts.json")
        cards = (ROOT / "results/profile_cards_v2.md").read_text(encoding="utf-8")
        sections = re.split(r"^### (\S+)\n", cards, flags=re.M)
        names = sections[1::2]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), set(verdicts))
        for name, card in zip(names, sections[2::2]):
            with self.subTest(model=name):
                verdict = verdicts[name]
                self.assertLessEqual(len(verdict.split()), 55)
                self.assertIn(len(re.split(r"(?<=[.!?])\s+", verdict)), (1, 2))
                self.assertEqual(card.count("Verdict: "), 1)
                self.assertIn("\n" + format_verdict(name, verdicts) + "\n", card)

    def test_wrapping_preserves_text(self):
        text = "A short editorial sentence with a longer explanation. " * 3
        rendered = format_verdict("model", {"model": text.strip()})
        self.assertEqual(" ".join(rendered.split()), "Verdict: " + text.strip())
        self.assertTrue(all(len(line) <= 78 for line in rendered.splitlines()))

    def test_missing_model_fails_explicitly(self):
        with self.assertRaisesRegex(ValueError, "Missing editorial verdict"):
            format_verdict("new_model", {})

    def test_invalid_copy_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "verdicts.json"
            for value in ("", "two\nlines", None):
                with self.subTest(value=value):
                    path.write_text(json.dumps({"models": {"model": value}}))
                    with self.assertRaisesRegex(ValueError, "Invalid editorial verdict"):
                        load_verdicts(path)


if __name__ == "__main__":
    unittest.main()
