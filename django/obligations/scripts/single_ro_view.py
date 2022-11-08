from pathlib import Path

from lxml import etree, html


def get_single_ro_html_view(p_html: Path, s_reporting_obligation: str, b_debug=True, encoding="UTF-8"):
    """
    - TODO how to return the html
    - Fixed encoding
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


def get_single_ro_html_view_from_string(
    s_html: str, s_reporting_obligation: str, b_debug=True, encoding="UTF-8"
) -> str:
    """
    Converts the html string such that only the matching reporting obligation
    """

    parser = etree.HTMLParser(encoding=encoding)

    print("instance s_html", type(s_html))

    # If bytestring, convert to string.
    if isinstance(s_html, bytes):
        print("decoding")

        s_html = s_html.decode(encoding=encoding)

    print("instance s_html", type(s_html))

    print("s_html", s_html)

    tree = etree.HTML(s_html, parser)
    # tree = html.fromstring(
    #     s_html,
    #     # parser, # TODO return!
    # )

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

    s_html_single = etree.tostring(
        tree, encoding="UTF-8", xml_declaration=True  # TODO wanted? Adds <?xml version='1.0' encoding='UTF-8'?>
    )

    return s_html_single
