import unittest
from scripts.collect_xit import attachments, inspect_pdf


class XitCollectorTests(unittest.TestCase):
    def test_extracts_year_kind_and_deduplicates_links(self):
        html = b'''<a href="/a.pdf">2025\xe5\xb9\xb4408\xe7\x9c\x9f\xe9\xa2\x98.pdf</a>
<a href="/b.pdf">2025\xe5\xb9\xb4408\xe7\xad\x94\xe6\xa1\x88.pdf</a>
<a href="/a.pdf">2025\xe5\xb9\xb4408\xe7\x9c\x9f\xe9\xa2\x98.pdf</a>'''
        items = attachments(html)
        self.assertEqual([(x['year'], x['kind']) for x in items], [(2025, 'answers'), (2025, 'paper')])
        self.assertEqual(items[0]['url'], 'https://www.xit.edu.cn/b.pdf')

    def test_rejects_conflicting_files_and_external_attachments(self):
        for html in ['<a href="https://example.com/a.pdf">2025年408真题</a>',
                     '<a href="/a.pdf">2025年408真题</a><a href="/b.pdf">2025年408真题</a>']:
            with self.assertRaises(ValueError): attachments(html.encode())

    def test_html_response_cannot_be_saved_as_pdf(self):
        with self.assertRaisesRegex(ValueError, 'not a PDF'):
            inspect_pdf(b'<html>Server unavailable</html>')
