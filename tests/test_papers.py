"""Regressions that would silently lose questions or expose answers in an exam."""
import json
import re
import unittest
from pathlib import Path

from scripts.build_papers import PAPERS, parse_paper, prepare


class PaperTests(unittest.TestCase):
    def setUp(self):
        self.source = (PAPERS / "2022.md").read_text()
        self.metadata = json.loads((PAPERS / "manifest.json").read_text())["2022"]

    def test_every_year_has_47_ordered_questions_and_portable_figures(self):
        for year in range(2009, 2025):
            with self.subTest(year=year):
                paper = prepare(str(year))
                self.assertEqual(len(paper["questions"]), 47)
                for q in paper["questions"][:40]:
                    if q["number"] not in paper["incomplete_questions"] and q["options"]:
                        self.assertEqual(len(set(q["options"])), 4, f"Q{q['number']} duplicated option")

    def test_a_missing_question_fails_instead_of_renumbering(self):
        broken = self.source.replace("## 25.", "25.")
        with self.assertRaisesRegex(ValueError, "expected questions"):
            parse_paper(broken, year="2022", metadata=self.metadata)

    def test_a_duplicate_question_fails(self):
        with self.assertRaisesRegex(ValueError, "expected questions"):
            parse_paper(self.source + "\n## 47. Duplicate", year="2022", metadata=self.metadata)

    def test_embedded_answer_fails(self):
        broken = self.source.replace("## 2.", "【答案】B\n\n## 2.")
        with self.assertRaisesRegex(ValueError, "answer or explanation"):
            parse_paper(broken, year="2022", metadata=self.metadata)

    def test_option_diagrams_belong_to_question_stem(self):
        source = self.source.replace("## 2.", "![](assets/example.png)\n\n## 2.")
        paper = parse_paper(source, year="2022", metadata=self.metadata)
        self.assertIn("assets/example.png", paper["questions"][0]["body"])
        self.assertNotIn("assets/example.png", paper["questions"][0]["options"][3])

    def test_sources_have_balanced_code_fences(self):
        for path in PAPERS.glob("*.md"):
            opened = False
            for line in path.read_text().splitlines():
                if not line.startswith("```"):
                    continue
                if opened:
                    self.assertEqual(line, "```", f"Nested code fence in {path.name}")
                opened = not opened
            self.assertFalse(opened, f"Unclosed code fence in {path.name}")

    def test_recovered_2024_questions_and_subquestions_survive(self):
        paper = prepare("2024")
        self.assertIn("uniquely", paper["questions"][40]["body"])
        self.assertIn("信号量", paper["questions"][45]["body"])
        self.assertIn("(6)", paper["questions"][42]["body"])


if __name__ == "__main__":
    unittest.main()
