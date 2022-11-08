from django.test import TestCase
from glossary.models import Concept


class ConceptTestCase(TestCase):
    def setUp(self):
        Concept.objects.create(
            name="ABIR",
            definition="ABIR is a professional trade association representing Bermuda’s Class 4 insurers and reinsurers.",
            lemma="ABIR",
        )

    def test_concept_has_definition_field(self):
        abir_concept = Concept.objects.get(name="ABIR")
        self.assertIsInstance(abir_concept.definition, str)
