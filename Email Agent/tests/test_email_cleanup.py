import unittest

from src.gmail.fetch import _strip_html


class EmailCleanupTests(unittest.TestCase):
    def test_strip_html_inserts_missing_space_between_date_and_sentence(self):
        text = "30 AugustBased on your saved search"
        self.assertEqual(_strip_html(text), "30 August Based on your saved search")

    def test_strip_html_preserves_tag_separated_text(self):
        html = "<div>30 August</div><p>Based on your saved search</p>"
        self.assertEqual(_strip_html(html), "30 August Based on your saved search")
