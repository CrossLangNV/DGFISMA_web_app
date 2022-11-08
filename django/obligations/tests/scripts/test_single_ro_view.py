import os
import unittest

from lxml import etree

from obligations.scripts.single_ro_view import get_single_ro_html_view

ROOT = os.path.join(os.path.dirname(__file__), "")

HTML_JSON = os.path.join(ROOT, "6d553347-bfce-50e3-abea-f1584fa68a60-d16bba97890.html")

S_RO = "10.6.1 . The discovering SIRENE bureau makes the comparison . The discovering SIRENE bureau sends a G form through the usual electronic path and asks , in field 089 , the providing SIRENE bureau to send an L form as soon as possible , as well as the fingerprints and pictures , if these are available ."

k_content_html = "content_html"


class TestGetSingleROHtmlView(unittest.TestCase):
    def test_process(self):

        b, e = os.path.splitext(HTML_JSON)
        HTML_NEW = b + "_new" + e

        tree = get_single_ro_html_view(HTML_JSON, S_RO)

        self.assertTrue(tree)

        s_html = etree.tostring(
            tree, encoding="UTF-8", xml_declaration=True  # TODO wanted? Adds <?xml version='1.0' encoding='UTF-8'?>
        )
        print(s_html)

        if 1:
            with open(HTML_NEW, "wb") as f:
                f.write(s_html)

        return
