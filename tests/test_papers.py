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
        for year in range(2009, 2027):
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

    def test_code_fence_around_all_options_fails_before_it_hides_a_figure(self):
        questions = "\n\n".join(
            f"## {n}. Stem\n\n```c\nA. first B. second C. third D. fourth\n```\n\n![](assets/example.png)"
            if n <= 40 else f"## {n}. Stem"
            for n in range(1, 48)
        )
        with self.assertRaisesRegex(ValueError, "code fence crosses"):
            parse_paper(questions, year="2024", metadata={})

    def test_2023_q47_has_all_subquestions_without_the_unlabelled_answers(self):
        body = prepare("2023")["questions"][46]["body"]
        for number in range(1, 5):
            self.assertIn(f"({number})", body)
        for answer in ("控制连接是持久的；", "101 (1分)", "18102 (1分)",
                       "3MSS (1分)", "5MSS (1分)", "6个RTT=60ms", "2.4Mbps"):
            self.assertNotIn(answer, body)

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
        # The photographed paper combines the opcode and effective-address
        # questions as Q43(5); the recalled version split them into (5)/(6).
        self.assertIn("(5)", paper["questions"][42]["body"])
        self.assertIn("R[01H]=FFFF A2D0H", paper["questions"][42]["body"])
        self.assertIn("(5)", paper["questions"][46]["body"])

    def test_missing_or_changed_essay_score_fails(self):
        source = (PAPERS / "2023.md").read_text()
        metadata = json.loads((PAPERS / "manifest.json").read_text())["2023"]
        for replacement in ("", "(5分)"):
            with self.subTest(replacement=replacement):
                with self.assertRaisesRegex(ValueError, "score does not match"):
                    parse_paper(source.replace("## 46. (8分)", "## 46. " + replacement),
                                year="2023", metadata=metadata)

    def test_recalled_numbering_and_missing_options_do_not_return(self):
        paper = prepare("2023")
        for number, keyword in ((12, "1.5GHz"), (16, "OF"), (17, "通用寄存器编号"),
                                (28, "虚拟地址空间"), (29, "周转时间"),
                                (30, "共享数据"), (31, "关闭")):
            self.assertIn(keyword, paper["questions"][number - 1]["body"])
        for number in (19, 32):
            self.assertEqual(len(paper["questions"][number - 1]["options"]), 4)
        paper = prepare("2024")
        self.assertIn("VLAN", paper["questions"][34]["body"])
        self.assertIn("UDP", paper["questions"][38]["body"])
        for number in (19, 21, 22, 23):
            self.assertNotIn("选项略", str(paper["questions"][number - 1]))

    def test_2024_memory_rows_keep_address_separate_from_eight_bytes(self):
        body = prepare("2024")["questions"][43]["body"]
        rows = [line for line in body.splitlines() if line.startswith("| 0013")]
        self.assertEqual(len(rows), 4)
        for row in rows:
            cells = [cell.strip() for cell in row.strip("|").split("|")]
            self.assertEqual(len(cells), 9)
            self.assertRegex(cells[0], r"^0013 [DE][0-9A-F]{3}H$")
            for byte in cells[1:]:
                self.assertRegex(byte, r"^[0-9A-F]{2}$")

    def test_new_papers_have_complete_matching_answer_keys(self):
        expected = {
            "2025": "BDDBD CCCAD ADDDC BCBAA BADCC BDCCA CBBCC CBABA".replace(" ", ""),
            "2026": "ADCBD DBDBA ACABA DACAA DCCDD ACCDB DDBDB BBACD".replace(" ", ""),
        }
        for year in ("2025", "2026"):
            paper = prepare(year)
            self.assertEqual([q["number"] for q in paper["answers"]], list(range(1, 48)))
            self.assertTrue(all(q["body"] for q in paper["answers"][40:]))
            self.assertEqual(sum(paper["essay_scores"]), 70)
            self.assertEqual("".join(q["choice"] for q in paper["answers"][:40]), expected[year])

    def test_reviewed_conflicts_do_not_return(self):
        self.assertEqual(prepare("2012")["essay_scores"][2:4], [11, 12])
        self.assertEqual(prepare("2014")["essay_scores"][4:], [11, 7, 8])
        q = prepare("2024")["questions"][3]
        self.assertEqual([x.replace(" ", "").replace("，", ",") for x in q["options"]], ["0,2", "2,4", "2,5", "3,4"])
        code = prepare("2023")["questions"][43]["body"]
        self.assertIn("8B 45 F8", code)
        self.assertIn("C7 84 91", code)
        self.assertIn("malloc(100)", prepare("2025")["questions"][45]["body"])

    def test_stem_diagram_keeps_its_position_before_following_text(self):
        source = self.source.replace("## 1.", "## 1. ![](assets/example.png)\n\nText after diagram. ", 1)
        q = parse_paper(source, year="2022", metadata=self.metadata)["questions"][0]
        self.assertLess(q["body"].index("assets/example.png"), q["body"].index("Text after diagram"))


if __name__ == "__main__":
    unittest.main()
