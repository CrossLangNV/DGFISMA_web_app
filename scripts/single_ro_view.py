from pathlib import Path

from lxml import etree
from lxml import html


def get_single_ro_html_view(p_html: Path, s_reporting_obligation: str, b_debug=True, encoding="UTF-8"):
    """
    - TODO how to return the html
    - Fixed encoding
    - encoding should be added in another form, not: <?xml version='1.0' encoding='UTF-8'?> on top
    """

    parser = etree.HTMLParser(encoding=encoding)
    tree = html.parse(
        p_html,
        parser,
    )

    for span in tree.iterfind(".//p"):
        s_span = "".join(span.itertext())

        if s_reporting_obligation == s_span:
            if b_debug:
                print(s_reporting_obligation)

        else:
            if 0:
                # Remove all span tags.
                etree.strip_tags(span, "span")
            else:
                # Remove everything
                span.getparent().remove(span)

    return tree
