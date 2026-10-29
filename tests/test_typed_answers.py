"""Keep each annual answer book complete and paired with its reviewed paper."""
import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

from scripts.typed_answers import ROOT, load_typed, walk, markdown_nodes
from scripts.paper_downloads import package_downloads
from unittest.mock import patch
from scripts.build_papers import prepare


class TypedAnswerTests(unittest.TestCase):
    def test_all_sixteen_sources_are_complete_paired_and_editable(self):
        reviews = json.loads((ROOT / 'typst/archive/scan-edition-2026-10-29/scan-reviews.json').read_text())
        for year, review in reviews.items():
            paper = prepare(year)
            answers = paper['answers']
            self.assertEqual([a['number'] for a in answers], list(range(1, 48)))
            self.assertEqual(''.join(a['choice'] for a in answers[:40]), review['choice_key'])
            self.assertEqual(sum(paper['essay_scores']), 70)
            self.assertNotIn('answer_scans', paper)
            for answer in answers:
                self.assertTrue(answer['nodes'])
                for node in walk(answer['nodes']):
                    if node['kind'] == 'image':
                        self.assertTrue(node['path'].endswith('.svg'))
            for number in (41, 47):
                self.assertTrue(answers[number - 1]['nodes'])
        self.assertEqual(len(reviews), 16)

    def test_pairing_rejects_changed_questions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'typst/answers').mkdir(parents=True)
            (root / 'typst/papers').mkdir()
            (root / 'typst/answers/2012.json').write_text((ROOT / 'typst/answers/2012.json').read_text())
            (root / 'typst/papers/2012.md').write_text('Changed option')
            with patch('scripts.typed_answers.ROOT', root):
                with self.assertRaisesRegex(ValueError, 'review answer pairing'):
                    load_typed('2012')

    def test_blank_lines_inside_code_survive_paragraph_conversion(self):
        nodes = markdown_nodes('第一段。\n\n```c\nint x = 0;\n\nreturn x;\n```\n\n下一段。')
        self.assertEqual([n['kind'] for n in nodes], ['markdown', 'code', 'markdown'])
        self.assertEqual(nodes[1]['value'], 'int x = 0;\n\nreturn x;')
        with self.assertRaisesRegex(ValueError, 'Unclosed'):
            markdown_nodes('```c\nint x;')

    def test_every_year_has_three_local_downloads(self):
        page = (ROOT / 'source/assignments/index.md').read_text()
        for year in range(2009, 2027):
            for kind in ('paper', 'answers', 'answer-sheet'):
                self.assertIn(f'<../_static/files/papers/{year}-408-{kind}.pdf>', page)

    def test_download_archive_contains_three_files_under_each_year(self):
        years = [str(y) for y in range(2009, 2027)]
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for year in years:
                for kind in ('paper', 'answers', 'answer-sheet'):
                    (folder / f'{year}-408-{kind}.pdf').write_bytes(b'%PDF-test')
            with zipfile.ZipFile(package_downloads(folder, years)) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(len(z.namelist()), 54)
                for year in years:
                    self.assertEqual(sum(n.startswith(year + '/') for n in z.namelist()), 3)
