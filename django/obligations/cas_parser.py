import os

import cassis
from cassis import load_typesystem, load_cas_from_xmi
KEY_CHILDREN = "children"
KEY_VALUE = "value"
KEY_SENTENCE_FRAG_CLASS = "class"

SOFA_ID_HTML2TEXT = "html2textView"
VALUE_BETWEEN_TAG_TYPE_CLASS = "com.crosslang.uimahtmltotext.uima.type.ValueBetweenTagType"


class CasContent(dict):
    """
    Dictionary of cas contents.
    https://stackoverflow.com/questions/4045161/should-i-use-a-class-or-dictionary
    """

    @classmethod
    def from_list(cls, list_ro, meta=None):
        """
        Args:
            list_ro: list with reporting obligations
            meta: optional value to save in meta data argument of dict.
        """

        d = {KEY_CHILDREN: [ROContent.from_list(ro) for ro in list_ro], "meta": meta}

        return cls(d)

    @classmethod
    def from_cassis_cas(cls, cas: cassis.Cas, name_view=SOFA_ID_HTML2TEXT):
        """
        Args:
            cas:
            name_view: Should be "html2textView" according to Arne Defauw and NOT 'ReportingObligationsView'
        Returns:
        """

        view_text_html = cas.get_view(name_view)

        l_ro = []

        for annot_p in view_text_html.select(VALUE_BETWEEN_TAG_TYPE_CLASS):
            if annot_p.tagName == "p":

                ro_i = {KEY_VALUE: annot_p.get_covered_text(), KEY_CHILDREN: []}  # string representation

                for annot_span in view_text_html.select_covered(VALUE_BETWEEN_TAG_TYPE_CLASS, annot_p):
                    if annot_span.tagName == "span":
                        str_attr = annot_span.value("attributes")

                        # First split inner arguments with values.
                        # Then only take the values
                        # We expect the class to be the first value
                        l_str_attr = str_attr.split("'")
                        attributes, values = l_str_attr[::2], l_str_attr[1::2]

                        class_atr = values[attributes.index("class=")]

                        ro_i[KEY_CHILDREN].append(
                            {KEY_SENTENCE_FRAG_CLASS: class_atr, KEY_VALUE: annot_span.get_covered_text()}
                        )

                l_ro.append(ro_i)

        return cls.from_list(l_ro)

    @classmethod
    def from_cas_file(cls, path_cas, path_typesystem):
        """Build up CasContent from file directly
        Args:
            path_cas:
            path_typesystem:
        Returns:
            a list
        """
        with open(path_typesystem, "rb") as f:
            typesystem = load_typesystem(f)

        with open(path_cas, "rb") as f:
            cas = load_cas_from_xmi(f, typesystem=typesystem)

        return cls.from_cassis_cas(cas)


class ROContent(dict):
    """
    List of reporting obligations
    """

    @classmethod
    def from_list(cls, list_sentence_fragments):
        l = []
        for sent_frag in list_sentence_fragments[KEY_CHILDREN]:
            l.append(SentenceFragment.from_value_class(v=sent_frag[KEY_VALUE], c=sent_frag[KEY_SENTENCE_FRAG_CLASS]))

        return cls({KEY_VALUE: list_sentence_fragments[KEY_VALUE], KEY_CHILDREN: l})


class SentenceFragment(dict):
    """
    Dictionary for sentence fragments
    """

    @classmethod
    def from_value_class(cls, v: str, c: str):
        return cls({KEY_SENTENCE_FRAG_CLASS: str(c), KEY_VALUE: str(v)})


def _get_example_cas_content() -> CasContent:
    """
    fixed example.
    Returns:
    """
    #
    rel_path_cas = "reporting_obligations/output_reporting_obligations/cas_laurens.xml"
    rel_path_typesystem = "reporting_obligations/output_reporting_obligations/typesystem_tmp.xml"

    # from ROOT
    path_cas = os.path.join(os.path.dirname(__file__), "..", rel_path_cas)
    path_typesystem = os.path.join(os.path.dirname(__file__), "..", rel_path_typesystem)

    cas_content = CasContent.from_cas_file(path_cas, path_typesystem)

    return cas_content


if __name__ == "__main__":
    cas_content = _get_example_cas_content()
    print(cas_content)
