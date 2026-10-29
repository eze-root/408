"""Synthetic semantic HTML to Typst data tests; no copied exam content."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_collected_papers import Converter, corrected_html, notices


class TypesettingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "assets.json").write_text("[]")
        self.converter = Converter(self.root, self.root / "export")

    def test_inline_spacing_superscript_and_overline_survive(self):
        nodes = self.converter.content('<span>x</span> <span class="markdown-math-overline">y<sub>1</sub></span><sup>2</sup>')
        self.assertEqual(nodes[1], {"kind":"text", "value":" "})
        self.assertEqual(nodes[2]["kind"], "overline")
        self.assertEqual(nodes[2]["children"][1]["kind"], "sub")
        self.assertEqual(nodes[3]["kind"], "sup")

    def test_fraction_is_structured_and_not_flattened(self):
        nodes = self.converter.content('<span class="markdown-math-fraction"><span class="markdown-math-numerator">a+b</span><span class="markdown-math-denominator">c</span></span>')
        self.assertEqual(nodes[0]["kind"], "fraction")
        self.assertEqual(nodes[0]["top"][0]["value"], "a+b")

    def test_matrix_retains_rows_and_columns(self):
        nodes = self.converter.content('<table class="markdown-matrix-grid"><tr><td>1</td><td>2</td></tr><tr><td>3</td><td>4</td></tr></table>')
        self.assertEqual(nodes[0]["kind"], "matrix")
        self.assertEqual([[cell[0]["value"] for cell in row] for row in nodes[0]["rows"]], [["1","2"],["3","4"]])

    def test_table_rowspan_does_not_shift_next_row(self):
        node = self.converter.content('<table><tr><th rowspan="2">a</th><th>b</th></tr><tr><td>c</td></tr></table>')[0]
        self.assertEqual(node["columns"], 2)
        self.assertEqual((node["cells"][2]["x"],node["cells"][2]["y"]),(1,1))

    def test_code_indentation_and_less_than_are_preserved(self):
        node = self.converter.content('<pre><code class="language-c">if (a &lt; b) {\n    x++;\n}</code></pre>')[0]
        self.assertEqual(node["value"], "if (a < b) {\n    x++;\n}")
        self.assertEqual(node["lang"], "c")

    def test_unknown_element_fails_instead_of_silent_loss(self):
        with self.assertRaisesRegex(ValueError,"Unsupported"):
            self.converter.content('<canvas>new diagram</canvas>')

    def test_display_fix_is_scoped_and_guarded(self):
        q={"id":"2026-46", "answer":{"html":"<p>≤ft⌊x⌋</p>"}}
        self.assertEqual(corrected_html(q,"answer"),"<p>⌊x⌋</p>")
        self.assertEqual(q["answer"]["html"],"<p>≤ft⌊x⌋</p>")
        q["answer"]["html"]="<p>source changed</p>"
        with self.assertRaises(ValueError):corrected_html(q,"answer")

    def test_score_conflict_is_disclosed(self):
        flags=[{"year":2020,"number":43,"flags":["单题分值不同"],"local_score":11,"remote_score":10}]
        self.assertIn("本地稿 11 分",notices(2020,flags)[0])


if __name__ == "__main__":
    unittest.main()
