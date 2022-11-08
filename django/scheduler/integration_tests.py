import os
import time

from celery import shared_task

from glossary.models import Concept
from searchapp.solr_call import solr_search_query_paginated_preanalyzed
import logging as logger

EXTRACT_TERMS_NLP_VERSION = os.environ.get("EXTRACT_TERMS_NLP_VERSION", "8a4f1d58")


@shared_task
def test_concept_highlights_it():
    concepts = Concept.objects.all().exclude(name__exact="Unknown").exclude(definition__exact="")
    concepts.filter(version=EXTRACT_TERMS_NLP_VERSION)
    total = len(concepts)

    i = 0
    result_no_highlight = 0
    for concept in concepts:
        i = i + 1
        logger.info("Testing concept %s/%s", i, total)

        term = "{!term f=concept_occurs}" + concept.name
        result = solr_search_query_paginated_preanalyzed(
            core="documents", term=term, page_number=1, rows_per_page=5, sort_by="date", sort_direction="desc"
        )

        if result:
            try:

                concept_occurs = result[1][0]["concept_occurs"]

                highlight_str = '<span class="highlight">'
                if not highlight_str in concept_occurs[0]:
                    logger.info(
                        "No highlighting in SOLR (concept_occurs) for concept: %s (id: %s) from document id: %s",
                        concept.name,
                        concept.id,
                    )
                    result_no_highlight = result_no_highlight + 1
            except IndexError as e:
                logger.info("IndexError: No results found for concept: %s (id: %s)", concept.name, concept.id)
                result_no_highlight = result_no_highlight + 1

        else:
            logger.info("No results found for concept: %s (id: %s)", concept.name, concept.id)

    logger.info("Test succeeded. %s concepts found without highlighting.", result_no_highlight)
