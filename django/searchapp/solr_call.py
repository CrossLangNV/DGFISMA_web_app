import os

import pysolr
import requests
import textdistance
import logging as logger

ROW_LIMIT = 250000

QUERY_ID_ASC = "id asc"
QUERY_HL_FL = "hl.fl"
QUERY_HL_SNIPPETS = "hl.snippets"
QUERY_HL_MAX_CHARS = "hl.maxAnalyzedChars"
QUERY_HL_PRE = "hl.simple.pre"
QUERY_HL_POST = "hl.simple.post"
QUERY_HL_PREFIX = '<span class="highlight">'
QUERY_HL_SUFFIX = "</span>"


def solr_search(core="", term=""):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    search = get_results_highlighted(
        client.search(
            term,
            **{
                "rows": ROW_LIMIT,
                "hl": "on",
                QUERY_HL_FL: "*",
                QUERY_HL_SNIPPETS: 100,
                QUERY_HL_MAX_CHARS: 1000000,
                QUERY_HL_PRE: QUERY_HL_PREFIX,
                QUERY_HL_POST: QUERY_HL_SUFFIX,
            }
        )
    )
    return search


def solr_search_ids(core="", term=""):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    search = client.search(term, **{"rows": ROW_LIMIT, "fl": "id"})
    return search


def solr_search_website_paginated(core="", q="", page_number=1, rows_per_page=10):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    # solr page starts at 0
    page_number = int(page_number) - 1
    start = page_number * int(rows_per_page)
    options = {"rows": rows_per_page, "start": start}
    return client.search(q, **options)


def solr_search_paginated(
    core="", term="", page_number=1, rows_per_page=10, ids_to_filter_on=None, sort_by=None, sort_direction="asc"
):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    # solr page starts at 0
    page_number = int(page_number) - 1
    start = page_number * int(rows_per_page)
    if core == "documents":
        term = "content:" + '"' + term + '"'
    options = {
        "rows": rows_per_page,
        "start": start,
        "hl": "on",
        QUERY_HL_FL: "*",
        "hl.requireFieldMatch": "true",
        QUERY_HL_SNIPPETS: 3,
        QUERY_HL_MAX_CHARS: -1,
        QUERY_HL_PRE: QUERY_HL_PREFIX,
        QUERY_HL_POST: QUERY_HL_SUFFIX,
    }
    if ids_to_filter_on:
        fq_ids = "id:(" + " OR ".join(ids_to_filter_on) + ")"
        options["fq"] = fq_ids
    if sort_by:
        options["sort"] = sort_by + " " + sort_direction
    result = client.search(term, **options)
    search = get_results_highlighted(result)
    num_found = result.raw_response["response"]["numFound"]
    return num_found, search


def solr_search_query_paginated(
    core="", term="", page_number=1, rows_per_page=10, ids_to_filter_on=None, sort_by=None, sort_direction="asc"
):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    # solr page starts at 0
    page_number = int(page_number) - 1
    start = page_number * int(rows_per_page)
    options = {
        "rows": rows_per_page,
        "start": start,
        "hl": "on",
        QUERY_HL_FL: "*",
        "hl.requireFieldMatch": "true",
        QUERY_HL_SNIPPETS: 3,
        QUERY_HL_MAX_CHARS: -1,
        QUERY_HL_PRE: QUERY_HL_PREFIX,
        QUERY_HL_POST: QUERY_HL_SUFFIX,
    }
    if ids_to_filter_on:
        fq_ids = "id:(" + " OR ".join(ids_to_filter_on) + ")"
        options["fq"] = fq_ids
    if sort_by:
        options["sort"] = sort_by + " " + sort_direction
    result = client.search(term, **options)
    search = get_results_highlighted(result)
    num_found = result.raw_response["response"]["numFound"]
    return num_found, search


def solr_search_query_paginated_preanalyzed(
    core="", term="", page_number=1, rows_per_page=10, sort_by=None, sort_direction="asc"
):
    url = os.environ["SOLR_URL"] + "/" + core + "/select/"
    # solr page starts at 0
    page_number = int(page_number) - 1
    start = page_number * int(rows_per_page)
    options = {
        "q": term,
        "hl": "on",
        "fl": "id,title,website,date, content",
        QUERY_HL_FL: "concept_defined, concept_occurs",
        QUERY_HL_MAX_CHARS: "-1",
        QUERY_HL_PRE: QUERY_HL_PREFIX,
        QUERY_HL_POST: QUERY_HL_SUFFIX,
        "start": start,
        "rows": rows_per_page,
    }

    if sort_by:
        options["sort"] = sort_by + " " + sort_direction
    response = requests.request("POST", url, data=options)
    result = response.json()
    search = get_results_highlighted_preanalyzed(result)
    num_found = result["response"]["numFound"]

    return num_found, search


def solr_search_query_paginated_preanalyzed(
    core="", term="", page_number=1, rows_per_page=10, sort_by=None, sort_direction="asc"
):
    url = os.environ["SOLR_URL"] + "/" + core + "/select/"
    # solr page starts at 0
    page_number = int(page_number) - 1
    start = page_number * int(rows_per_page)
    options = {
        "q": term,
        "hl": "on",
        "fl": "id,title,website,date, content",
        QUERY_HL_FL: "concept_defined, concept_occurs, ro_highlight",
        QUERY_HL_MAX_CHARS: "-1",
        QUERY_HL_PRE: QUERY_HL_PREFIX,
        QUERY_HL_POST: QUERY_HL_SUFFIX,
        "start": start,
        "rows": rows_per_page,
    }

    if sort_by:
        options["sort"] = sort_by + " " + sort_direction
    response = requests.request("POST", url, data=options)
    result = response.json()
    search = get_results_highlighted_preanalyzed(result)
    num_found = result["response"]["numFound"]

    return num_found, search


def solr_search_query_with_doc_id_preanalyzed(
    doc_id, core="", term="", page_number=1, rows_per_page=10, sort_by=None, sort_direction="asc"
):
    url = os.environ["SOLR_URL"] + "/" + core + "/select/"
    # solr page starts at 0
    page_number = int(page_number) - 1
    start = page_number * int(rows_per_page)
    options = {
        "q": term,
        "hl": "on",
        "hl.fragsize": "0",
        "fl": "id,title,website,date,content",
        QUERY_HL_FL: "concept_defined, concept_occurs, ro_highlight",
        QUERY_HL_MAX_CHARS: "-1",
        QUERY_HL_PRE: QUERY_HL_PREFIX,
        QUERY_HL_POST: QUERY_HL_SUFFIX,
        "start": start,
        "rows": rows_per_page,
    }
    if doc_id:
        options["fq"] = "id:" + doc_id

    if sort_by:
        options["sort"] = sort_by + " " + sort_direction

    response = requests.request("POST", url, data=options)
    result = response.json()
    num_found = result["response"]["numFound"]

    return num_found, result


def solr_get_preanalyzed_for_doc(
    core="", id="", field="", term="", page_number=1, rows_per_page=10, sort_by=None, sort_direction="asc"
):

    query = "{!term f=" + field + "}" + term

    url = os.environ["SOLR_URL"] + "/" + core + "/select/"
    # solr page starts at 0
    page_number = int(page_number) - 1
    start = page_number * int(rows_per_page)
    options = {
        "q": query,
        "id": id,
        "hl": "on",
        "fl": "id,title,website,date",
        QUERY_HL_FL: field,
        QUERY_HL_MAX_CHARS: "-1",
        QUERY_HL_PRE: QUERY_HL_PREFIX,
        QUERY_HL_POST: QUERY_HL_SUFFIX,
        "start": start,
        "rows": rows_per_page,
    }

    if sort_by:
        options["sort"] = sort_by + " " + sort_direction
    response = requests.request("POST", url, data=options)
    fields = ["concept_occurs", "concept_defined", "ro_highlight"]

    highlights = []
    if response.status_code == 200:
        result = response.json()
        for doc in result["response"]["docs"]:
            for document_field in fields:
                if document_field in result["highlighting"][doc["id"]]:
                    doc[document_field] = result["highlighting"][doc["id"]][document_field]
                    # Specific only the highlights
                    highlights.append(result["highlighting"][doc["id"]][document_field])

    if len(highlights) > 0:
        return highlights[0][0]
    else:
        return None


def solr_search_id(core="", id=""):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    search = get_results(client.search("id:" + id, **{"rows": ROW_LIMIT}))
    return search


def solr_search_content_by_id(core="", id=""):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    search = get_results(client.search("id:" + id, **{"rows": ROW_LIMIT, "fl": "content"}))
    return search


def solr_search_id_sorted(core="", id=""):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    search = get_results(client.search("id:" + id, **{"rows": ROW_LIMIT, "sort": QUERY_ID_ASC}))
    return search


def solr_search_website_with_content(core="", website="", **kwargs):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    date = kwargs.get("date", None)
    query = "website:" + website

    if date:
        query = query + " AND date:[" + date + " TO NOW]"
    search = client.search(query, **{"rows": 250, "start": 0, "cursorMark": "*", "sort": QUERY_ID_ASC})
    return search


def solr_search_website_sorted(core="", website="", **kwargs):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    SOLR_SYNC_FIELDS = "id,custom_id,title,title_prefix,author,misc_author,status,type,date,dates,dates_type,dates_info,date_last_update,url,eli,celex,file_url,website,summary,various,consolidated_versions"
    date = kwargs.get("date", None)
    query = "website:" + website

    if date:
        query = query + " AND date:[" + date + " TO NOW]"
    search = get_results(client.search(query, **{"rows": ROW_LIMIT, "fl": SOLR_SYNC_FIELDS, "sort": QUERY_ID_ASC}))
    return search


def solr_search_document_id_sorted(core="", document_id=""):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    search = get_results(
        client.search('attr_document_id:"' + document_id + '"', **{"rows": ROW_LIMIT, "sort": QUERY_ID_ASC})
    )
    return search


def get_results(response):
    results = []
    for doc in response:
        results.append(doc)
    return results


def get_results_highlighted(response):
    results = []
    # iterate over docs
    for doc in response:
        # iterate over every key in single doc dictionary
        for key in doc:
            if key in response.highlighting[doc["id"]]:
                doc[key] = response.highlighting[doc["id"]][key]
        results.append(doc)
    return results


def get_results_highlighted_preanalyzed(response):
    results = []
    fields = ["concept_occurs", "concept_defined", "ro_highlight"]

    highlights = []
    # iterate over docs
    for doc in response["response"]["docs"]:
        for document_field in fields:
            # iterate over every key in single doc dictionary
            # Here we replace the docs['concept_defined'] full-text by the one provided by the highlighting (shorter)
            if document_field in response["highlighting"][doc["id"]]:
                doc[document_field] = response["highlighting"][doc["id"]][document_field]
                results.append(doc)
                # Specific only the highlights
                highlights.append(response["highlighting"][doc["id"]][document_field])

    return results


def solr_update(core, document):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    document_existing_result = client.search("id:" + str(document["id"]))
    if len(document_existing_result.docs) == 1:
        document_existing = document_existing_result.docs[0]
        for key, value in document.items():
            if key == "file_url":
                document_existing[key] = value.name
            elif key != "id":
                document_existing[key] = value
        client.add([document_existing], commit=True)
    else:
        client.add([document], commit=True)


def solr_add_file(core, file, file_id, file_url, document_id):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    extra_params = {
        "commit": "true",
        "literal.id": file_id,
        "resource.name": file.name,
        "literal.url": file_url,
        "literal.document_id": document_id,
    }
    client.extract(file, extractOnly=False, **extra_params)


def solr_delete(core, id):
    try:
        client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
        client.delete(id=id)
        client.commit()
    except pysolr.SolrError:
        pass


"""
Use Solr MoreLikeThis https://lucene.apache.org/solr/guide/8_5/morelikethis.html
to find similar documents given a document id. Solr MLT returns candidates, apply coefficient to candidates
upon which a threshold can be applied: see https://www.dexstr.io/finding-duplicates-large-set-files/.
"""


def solr_mlt(core, id, mlt_field="title,content", number_candidates=5, threshold=0.0):
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    search_result = client.search(
        "id:" + id,
        **{"mlt": "true", "mlt.fl": mlt_field, "mlt.count": number_candidates, "fl": "id,website," + mlt_field}
    )
    # document to compare against

    similar_documents_with_coeff = []

    if search_result:
        base_doc = search_result.docs[0]

        base_tokens = base_doc["content"][0].split()

        # list of similar documents with Jaccard coefficient

        for doc in search_result.raw_response["moreLikeThis"][id]["docs"]:
            candidate_tokens = doc["content"][0].split()
            similarity = textdistance.jaccard(base_tokens, candidate_tokens)
            if similarity > float(threshold):
                similar_documents_with_coeff.append((doc["id"], doc["title"][0], doc["website"][0], similarity))

        # sort descending on coefficient
        similar_documents_with_coeff.sort(key=lambda x: x[-1], reverse=True)

    return similar_documents_with_coeff
