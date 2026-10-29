"""Synthetic fixtures: no third-party exam content or network requests in tests."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from scripts.collect_beokayy import (
    BASE, AccessBlocked, Fetcher, block, discover_papers, parse_knowledge,
    parse_paper, public_url, render_paper, soup_of, write_file, write_json,
)


def card(qid="2020-01", answer="答案：B"):
    options = "".join(
        f'<button class="choice-option"><span class="choice-letter">{letter}</span>'
        f'<span class="choice-text"><p>示例 {letter}</p></span></button>' for letter in "ABCD"
    )
    return f'''<article class="question-card" id="{qid}">
      <span class="question-kicker">数据结构</span>
      <div class="question-meta"><span>选择题</span><span>2<!-- --> 分</span></div>
      <div class="question-body"><p>示例题干<img src="/content-images/example.svg"></p></div>
      {options}<div class="answer-placeholder" hidden><div class="answer-content"><p>{answer}</p></div></div>
      <div class="mini-program-entry"><img src="/unrelated-qr.png"></div>
    </article>'''


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.paper = {"year": 2020, "url": BASE + "paper/2020", "expected_questions": 1, "expected_score": 2}
        self.meta = {"fetched_at": "2026-10-29T00:00:00Z", "sha256": "sample"}

    def test_discovers_years_from_cards_not_other_links(self):
        source = '''<a href="/paper/1900">unrelated</a><a class="archive-year-card" href="/paper/2020">
        <dl><div><dt>题目</dt><dd>47 道</dd></div><div><dt>总分</dt><dd>150 分</dd></div>
        <div><dt>答案</dt><dd>47 份</dd></div></dl></a>'''
        papers = discover_papers(source)
        self.assertEqual(list(papers), [2020])
        self.assertEqual(papers[2020]["expected_questions"], 47)

    def test_extracts_hidden_public_answer_without_qr_or_ui(self):
        q = parse_paper(card(), self.paper, self.meta)[0]
        self.assertEqual(q["answer_choice"], "B")
        self.assertEqual(q["score"], 2)
        self.assertEqual(q["stem"]["image_urls"], [BASE + "content-images/example.svg"])
        self.assertNotIn("unrelated-qr", json.dumps(q))
        self.assertEqual(q["source"]["page_sha256"], "sample")

    def test_duplicate_missing_and_wrong_year_fail(self):
        for source in (card() + card(), "<main></main>", card("2021-01")):
            with self.subTest(source=source[:40]), self.assertRaises(ValueError):
                parse_paper(source, self.paper, self.meta)

    def test_bad_scores_and_missing_options_fail(self):
        for source in (card().replace("2<!-- -->", "3<!-- -->"), card().replace('>D</span>', '>A</span>')):
            with self.assertRaises(ValueError):
                parse_paper(source, self.paper, self.meta)

    def test_missing_answer_is_not_invented(self):
        q = parse_paper(card(answer=""), self.paper, self.meta)[0]
        self.assertIsNone(q["answer_choice"])
        self.assertEqual(q["answer"]["text"], "")

    def test_subject_names_match_knowledge_index_but_keep_source_label(self):
        q = parse_paper(card().replace("数据结构", "组成原理"), self.paper, self.meta)[0]
        self.assertEqual(q["subject"], "计算机组成原理")
        self.assertEqual(q["source"]["subject"], "组成原理")

    def test_code_tables_and_fraction_survive_and_scripts_do_not(self):
        source = '''<div><pre><code>if (a &lt; b) {\n  a++;\n}</code></pre>
        <table><tr><td rowspan="2">0xFF</td><td>16</td></tr></table>
        <span class="markdown-math-fraction"><span class="markdown-math-numerator">1</span>
        <span class="markdown-math-denominator">n</span></span>
        <img src="/content-images/a.svg" onerror="bad()"><script>bad()</script>
        <a href="javascript:bad()">unsafe</a></div>'''
        result = block(soup_of(source).div, self.paper["url"])
        self.assertIn("if (a < b) {\n  a++;\n}", result["text"])
        self.assertIn("(1)/(n)", result["text"])
        self.assertIn('rowspan="2"', result["html"])
        self.assertIn("markdown-math-fraction", result["html"])
        self.assertNotIn("bad()", result["html"])

    def test_knowledge_tags_deduplicate_links_and_keep_empty_points(self):
        source = '''<h2>数据结构</h2><article class="knowledge-chapter-card"><h3>树</h3>
        <div class="knowledge-point-entry" id="point-ds-01"><span class="knowledge-point-label">二叉树</span>
        <div class="knowledge-question-links"><a href="/question/2020-01?point=ds-01">one</a>
        <a href="/question/2020-01?point=ds-01">again</a></div></div>
        <div class="knowledge-point-entry" id="point-ds-02"><span class="knowledge-point-label">空专题</span></div></article>'''
        points = parse_knowledge(source, BASE + "knowledge")
        self.assertEqual(points[0]["question_ids"], ["2020-01"])
        self.assertEqual(points[0]["chapter"], "树")
        self.assertEqual(points[1]["question_ids"], [])

    def test_local_preview_rewrites_assets_and_does_not_hotlink_missing_images(self):
        questions = parse_paper(card(), self.paper, self.meta)
        result = render_paper(2020, questions, {BASE + "content-images/example.svg": {"path": "assets/example.svg"}})
        self.assertIn('src="../assets/example.svg"', result)
        self.assertIn("Content-Security-Policy", result)
        missing = render_paper(2020, questions, {})
        self.assertNotIn('<img', missing)
        self.assertIn("配图未下载", missing)

    def test_rejects_cross_origin_images_and_insecure_urls(self):
        for url in ("http://zhenti.beokayy.club/a", "https://example.org/a", "//example.org/a"):
            with self.assertRaises(ValueError):
                public_url(url)

    def test_offline_cache_integrity_and_no_network(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            url, data = BASE + "paper/2020", b"cached"
            key = hashlib.sha256(url.encode()).hexdigest()
            raw = output / "raw" / (key + ".bin")
            write_file(raw, data)
            write_json(raw.with_suffix(".json"), {"url": url, "sha256": hashlib.sha256(data).hexdigest()})
            fetcher = Fetcher(output, offline=True)
            fetcher.opener = Mock()
            self.assertEqual(fetcher.get(url)[0], data)
            with self.assertRaises(FileNotFoundError):
                fetcher.get(BASE + "missing")
            write_file(raw, b"corrupt")
            with self.assertRaisesRegex(ValueError, "缓存校验失败"):
                fetcher.get(url)
            fetcher.opener.open.assert_not_called()

    def test_access_denied_is_not_retried(self):
        with tempfile.TemporaryDirectory() as directory, patch("scripts.collect_beokayy.time.sleep"):
            fetcher = Fetcher(Path(directory))
            fetcher.opener = Mock()
            fetcher.opener.open.side_effect = HTTPError(BASE, 403, "Forbidden", {}, None)
            with self.assertRaises(AccessBlocked):
                fetcher.get(BASE)
            self.assertEqual(fetcher.opener.open.call_count, 1)

    def test_robots_404_allows_public_pages_but_disallow_stops_fetch(self):
        with tempfile.TemporaryDirectory() as directory, patch("scripts.collect_beokayy.time.sleep"):
            fetcher = Fetcher(Path(directory))
            fetcher.opener = Mock()
            fetcher.opener.open.side_effect = HTTPError(BASE + "robots.txt", 404, "Not Found", {}, None)
            self.assertEqual(fetcher.check_robots()["status"], 404)
            self.assertTrue(fetcher.robots.can_fetch("408-study-collector", BASE + "paper/2020"))
            fetcher.robots.parse(["User-agent: *", "Disallow: /paper/"])
            with self.assertRaises(AccessBlocked):
                fetcher.get(BASE + "paper/2020")
            self.assertEqual(fetcher.opener.open.call_count, 1)


if __name__ == "__main__":
    unittest.main()
