"""Regressions that would silently lose questions or expose answers in an exam."""
import json
import re
import unittest
from pathlib import Path

import pymupdf

from scripts.build_papers import PAPERS, parse_paper, prepare
from scripts.check_papers import visible_question_numbers


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

    def test_hard_breaks_do_not_leave_literal_backslashes_in_fragments(self):
        questions = "\n\n".join(
            f"## {n}. Stem\\\n\nA. first B. second C. third D. fourth\\"
            if n <= 40 else f"## {n}. First line\\\nSecond line"
            for n in range(1, 48)
        )
        paper = parse_paper(questions, year="2024", metadata={})
        self.assertEqual(paper["questions"][0]["body"], "Stem")
        self.assertEqual(paper["questions"][0]["options"][-1], "fourth")
        self.assertEqual(paper["questions"][40]["body"], "First line  \nSecond line")

    def test_pdf_numbers_survive_word_merging_without_hiding_missing_numbers(self):
        with pymupdf.open() as doc:
            doc.new_page()
            page = doc.new_page()
            for number, y in ((41, 80), (43, 120)):
                page.insert_text((62.36, y), f"{number}.", fontsize=13)
                page.insert_text((82.2, y), "Question stem", fontsize=13)
            self.assertNotIn("41.", [word[4] for word in page.get_text("words")])
            self.assertEqual(visible_question_numbers(doc), [41, 43])

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
