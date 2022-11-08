from django.test import TestCase

from cassis.typesystem import load_typesystem
from cassis.xmi import load_cas_from_xmi
from unittest import skip

# Create your tests here.
class ExtractTerms(TestCase):

    # @skip("Depends on external XMI file")
    def test_extract_terms(self):
        """
        check if term definition is extracted correctly
        """
        SENTENCE_CLASS = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence"
        TFIDF_CLASS = "de.tudarmstadt.ukp.dkpro.core.api.frequency.tfidf.type.Tfidf"
        LEMMA_CLASS = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Lemma"
        PARAGRAPH_CLASS = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Paragraph"
        SOFA_ID_HTML2TEXT = "html2textView"

        with open("scheduler/resources/typesystem.xml", "rb") as f:
            typesystem = load_typesystem(f)
        xmi_content = open("scheduler/resources/f1fdbb28-39b4-559a-a873-40dd209e893d/after_term.xmi").read()
        cas = load_cas_from_xmi(xmi_content, typesystem=typesystem)
        # Term defined, we check which terms are covered by definitions
        for num_defi, defi in enumerate(cas.get_view(SOFA_ID_HTML2TEXT).select(SENTENCE_CLASS)):
            term_name = "Unknown"
            lemma_name = ""

            print("===============================================")
            for i, term in enumerate(cas.get_view(SOFA_ID_HTML2TEXT).select_covered(TFIDF_CLASS, defi)):
                print(str(i) + ":" + term.term + " (" + str(term.begin) + ":" + str(term.end) + ")")
                if i > 0:  # and prev_term.begin != term.begin:
                    continue

                # Retrieve the lemma for the term
                for lemma in cas.get_view(SOFA_ID_HTML2TEXT).select_covered(LEMMA_CLASS, term):
                    if term.begin == lemma.begin and term.end == lemma.end:
                        lemma_name = lemma.value

                term_name = term.get_covered_text()
                prev_term = term

            # Handle paragraphs
            for par in cas.get_view(SOFA_ID_HTML2TEXT).select_covering(PARAGRAPH_CLASS, defi):
                if (
                    par.begin == defi.begin
                ):  # if beginning of paragraph == beginning of a definition ==> this detected paragraph should replace the definition
                    defi = par

            token_defined = defi.get_covered_text()
            start_defined = defi.begin
            end_defined = defi.end
            print("===============================================")
            print("==" + term_name + "(lemma: " + lemma_name + ")")
            print("===============================================")
            print(token_defined)
            print("")
            print("")

        self.assertEqual(num_defi, 39)
