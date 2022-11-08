import time
import base64
import json
import logging
import os
import urllib
import pysolr
import cassis
import requests
import math
import gzip

from cassis import (
    Cas,
    load_cas_from_xmi,
    TypeSystem,
    merge_typesystems,
    load_dkpro_core_typesystem,
)
from cassis.typesystem import load_typesystem, FeatureStructure
from celery import shared_task, chain
from glossary.models import Concept, ConceptOccurs, ConceptDefined, AcceptanceState, Lemma
from searchapp.models import Website, Document
from obligations.models import ReportingObligation, ReportingObligationOffsets
from minio import Minio, ResponseError
from minio.error import BucketAlreadyOwnedByYou, BucketAlreadyExists, NoSuchKey
from pycaprio.mappings import InceptionFormat, DocumentState
from pycaprio import Pycaprio

from glossary.models import AnnotationWorklog

logger = logging.getLogger(__name__)

# TODO Theres already a solr defined
SOLR_URL = os.environ["SOLR_URL"]
# Don't remove the '/' at the end here
TERM_EXTRACT_URL = os.environ["GLOSSARY_TERM_EXTRACT_URL"]
DEFINITIONS_EXTRACT_URL = os.environ["GLOSSARY_DEFINITIONS_EXTRACT_URL"]
PARAGRAPH_DETECT_URL = os.environ["GLOSSARY_PARAGRAPH_DETECT_URL"]
RO_EXTRACT_URL = os.environ["RO_EXTRACT_URL"]
CAS_TO_RDF_API = os.environ["CAS_TO_RDF_API"]
RDF_INIT_URL = os.environ["RDF_INIT_URL"]
CELERY_EXTRACT_TERMS_CHUNKS = os.environ.get("CELERY_EXTRACT_TERMS_CHUNKS", 8)
EXTRACT_TERMS_NLP_VERSION = os.environ.get("EXTRACT_TERMS_NLP_VERSION", "8a4f1d58")
EXTRACT_RO_NLP_VERSION = os.environ.get("EXTRACT_RO_NLP_VERSION", "d16bba97890")

SENTENCE_CLASS = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence"
TOKEN_CLASS = "cassis.Token"
TFIDF_CLASS = "de.tudarmstadt.ukp.dkpro.core.api.frequency.tfidf.type.Tfidf"
LEMMA_CLASS = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Lemma"
PARAGRAPH_CLASS = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Paragraph"
VALUE_BETWEEN_TAG_TYPE_CLASS = "com.crosslang.uimahtmltotext.uima.type.ValueBetweenTagType"
DEPENDENCY_CLASS = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.Dependency"
DEFINED_TYPE = "cassis.Token"  # Remove?
MAX_TERM_LENGTH = 500

# user annotations:
SENTENCE_CLASS_USER = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence_user"
TOKEN_CLASS_USER = "cassis.Token_user"
TFIDF_CLASS_USER = "de.tudarmstadt.ukp.dkpro.core.api.frequency.tfidf.type.Tfidf_user"
TOKEN_CLASS_USER_REJECTED = "cassis.Token_user_rejected"
TFIDF_CLASS_USER_REJECTED = "de.tudarmstadt.ukp.dkpro.core.api.frequency.tfidf.type.Tfidf_user_rejected"

DEFAULT_TYPESYSTEM = "scheduler/resources/typesystem.xml"

sofa_id_html2text = "html2textView"
sofa_id_text2html = "text2htmlView"
UIMA_URL = {
    "BASE": os.environ["GLOSSARY_UIMA_URL"],  # http://uima:8008
    "HTML2TEXT": "/html2text",
    "TEXT2HTML": "/text2html",
    "TYPESYSTEM": "/html2text/typesystem",
}

CONST_EXPORT = "/export/"
QUERY_ID_ASC = "id asc"
QUERY_WEBSITE = "website:"

RDF_FUSEKI_QUERY_URL = os.environ["RDF_FUSEKI_QUERY_URL"]
RDF_FUSEKI_UPDATE_URL = os.environ["RDF_FUSEKI_UPDATE_URL"]


def save_cas(cas, file_path):
    cas_xmi = cas.to_xmi(pretty_print=True)
    with open(file_path, "wb") as f:
        f.write(cas_xmi.encode())


def save_typesystem(typesystem, file_path):
    ts_xml = typesystem.to_xml()
    with open(file_path, "wb") as f:
        f.write(ts_xml.encode())


def save_compressed_cas(cas, file_name):
    cas_xmi = cas.to_xmi()
    file = gzip.open("/tmp/" + file_name, "wb")
    file.write(cas_xmi.encode())
    file.close()
    return file


def load_compressed_cas(file, typesystem):
    with gzip.open(file, "rb") as f:
        return load_cas_from_xmi(f, typesystem=typesystem, trusted=True)


def get_html2text_cas(content_html, docid, attributes):
    content_html_text = {"text": content_html, "attributes": attributes}
    logger.info("Sending request to %s", UIMA_URL["BASE"] + UIMA_URL["HTML2TEXT"])
    start = time.time()
    r = requests.post(UIMA_URL["BASE"] + UIMA_URL["HTML2TEXT"], json=content_html_text)

    end = time.time()
    logger.info(
        "UIMA Html2Text took %s seconds to succeed (code %s ) (id: %s ).",
        end - start,
        r.status_code,
        docid,
    )
    return r


def initialise_rdf_scheme():
    headers = {
        "endpoint": RDF_FUSEKI_QUERY_URL,
        "updateendpoint": RDF_FUSEKI_UPDATE_URL,
    }
    r = requests.post(RDF_INIT_URL, headers=headers)
    logger.info("Initialised RDF scheme. Response code: %s", r.status_code)


def save_to_rdf(cas, doc_id, source_name, source_url):
    encoded_cas = base64.b64encode(bytes(cas.to_xmi(), "utf-8")).decode()

    json_content = {"content": encoded_cas}

    headers = {
        "endpoint": RDF_FUSEKI_QUERY_URL,
        "updateendpoint": RDF_FUSEKI_UPDATE_URL,
        "docid": doc_id,
        "source-name": source_name,
        "source-url": source_url,
    }

    start = time.time()
    r = requests.post(CAS_TO_RDF_API, json=json_content, headers=headers)
    end = time.time()
    logger.info(
        "Sent request to %s. Status code: %s Took %s seconds",
        CAS_TO_RDF_API,
        r.status_code,
        end - start,
    )
    return r


def create_cas(sofa):
    with open(DEFAULT_TYPESYSTEM, "rb") as f:
        ts = load_typesystem(f)

    cas = Cas(typesystem=ts)
    cas.sofa_string = sofa
    return cas


def fetch_typesystem():
    try:
        # Check if file exits
        f = open(DEFAULT_TYPESYSTEM)
        f.close()
    except IOError:
        # Fetch from UIMA
        typesystem_req = requests.get(UIMA_URL["BASE"] + UIMA_URL["TYPESYSTEM"])
        typesystem_file = open(DEFAULT_TYPESYSTEM, "w")
        typesystem_file.write(typesystem_req.content.decode("utf-8"))

    # FIXME: load only once ?
    with open(DEFAULT_TYPESYSTEM, "rb") as f:
        return load_typesystem(f)


def get_cas_from_pdf(content, docid):
    # Logic for documents without HTML, that have a "content" field which is a PDF to HTML done by Tika
    # Create a new cas here
    start = time.time()
    tika_cas = create_cas(content)

    encoded_cas = base64.b64encode(bytes(tika_cas.to_xmi(), "utf-8")).decode()

    # Then send this cas to NLP Paragraph detection
    input_for_paragraph_detection = {
        "cas_content": encoded_cas,
        "content_type": "pdf",
    }

    logger.info("Sending request to Paragraph Detection (PDF) (%s)", PARAGRAPH_DETECT_URL)
    r = requests.post(PARAGRAPH_DETECT_URL, json=input_for_paragraph_detection)
    end = time.time()
    logger.info(
        "Paragraph Detect took %s seconds to succeed (code: %s) (id: %s).",
        end - start,
        r.status_code,
        docid,
    )
    return r


def get_cas_from_paragraph_detection(content_encoded, docid):
    input_for_paragraph_detection = {
        "cas_content": content_encoded,
        "content_type": "html",
    }

    logger.info("Sending request to Paragraph Detection (HTML) (%s)", PARAGRAPH_DETECT_URL)
    start = time.time()
    paragraph_request = requests.post(PARAGRAPH_DETECT_URL, json=input_for_paragraph_detection)
    end = time.time()
    logger.info(
        "Paragraph Detect took %s seconds to succeed (code: %s) (id: %s).",
        end - start,
        paragraph_request.status_code,
        docid,
    )
    return paragraph_request


def get_reporting_obligations(input_cas_encoded, doc_id):
    input_for_reporting_obligations = {
        "cas_content": input_cas_encoded,
        "content_type": "html",
        "doc_id": doc_id,
    }

    start = time.time()
    ro_request = requests.post(RO_EXTRACT_URL, json=input_for_reporting_obligations, timeout=2000)
    end = time.time()
    logger.info(
        "Sent request to RO Extraction. Status code: %s Took % seconds",
        ro_request.status_code,
        end - start,
    )

    return ro_request


def get_encoded_content_from_cas(r):
    content_decoded = r.content.decode("utf-8")
    encoded_bytes = base64.b64encode(content_decoded.encode("utf-8"))
    return str(encoded_bytes, "utf-8")


def get_cas_from_definitions_extract(input_cas_encoded, docid):
    input_for_term_defined = {
        "cas_content": input_cas_encoded,
        "content_type": "html",
    }

    logger.info("Sending request to DefinitionExtract NLP (%s)", DEFINITIONS_EXTRACT_URL)
    start = time.time()
    definitions_request = requests.post(DEFINITIONS_EXTRACT_URL, json=input_for_term_defined)
    end = time.time()
    logger.info(
        "DefinitionExtract took %s seconds to succeed (code: %s) (id: %s).",
        end - start,
        definitions_request.status_code,
        docid,
    )

    return definitions_request


def get_cas_from_text_extract(input_cas_encoded, docid):
    text_cas = {
        "cas_content": input_cas_encoded,
        "content_type": "html",
        "extract_supergrams": "false",
    }
    logger.info("Sending request to TextExtract NLP (%s)", TERM_EXTRACT_URL)
    start = time.time()
    request_nlp = requests.post(TERM_EXTRACT_URL, json=text_cas)
    end = time.time()
    logger.info(
        "TermExtract took %s seconds to succeed (code: %s) (id: %s).",
        end - start,
        request_nlp.status_code,
        docid,
    )
    return request_nlp


def get_values_from_html_attribute(attributes: str, value: str):
    """get value a from format f"{substring}'{a}'"

    :param substring:
    :return:
    """

    assert value in attributes, f"Did not find substring sub_string in full_string"

    i_right = attributes.find(value)
    s_right = attributes[i_right:]

    l_split = s_right.split("'", 2)

    assert l_split[1], """Did not find value between "'"."""

    s_value = l_split[1]

    assert s_value.isdigit(), f"""Could not cast to integer: {s_value}."""

    return int(s_value)


def post_pre_analyzed_to_solr(data):
    params = json.dumps(data).encode("utf-8")
    # FIXME: find a way to commit when all the work is done, commits after 15s now

    logger.debug("params: %s", params)
    req = urllib.request.Request(
        os.environ["SOLR_URL"] + "/documents/update?commitWithin=15000",
        data=params,
        headers={"content-type": "application/json"},
    )
    response = urllib.request.urlopen(req)
    logger.info(response.read().decode("utf8"))


def has_overlapping_user_annotation(cas: Cas, sofaID: str, annotation: FeatureStructure, user_type: str) -> bool:
    """
    Function checks if the FeatureStructure has an overlap with an annotation of type user_type in the given cas and sofa.
    This could potentially get slow if the CAS contains too many user annotations of a certain type. Please monitor performance.
    """

    for user_type_annotation in cas.get_view(sofaID).select(user_type):

        if not ((annotation.end < user_type_annotation.begin) or (annotation.begin > user_type_annotation.end)):
            return True

    return False


@shared_task
def extract_reporting_obligations(website_id, document_id=None):
    website = Website.objects.get(pk=website_id)
    website_name = website.name.lower()
    core = "documents"
    page_number = 0
    rows_per_page = 250
    cursor_mark = "*"

    if document_id:
        q = "id:" + document_id
        logger.info("Extract reporting obligations, DOCUMENT: %s", document_id)
    else:
        logger.info("Extract reporting obligations task, WEBSITE: %s", website)
        q = QUERY_WEBSITE + website_name + " AND acceptance_state:accepted"

    # Load all documents from Solr
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    options = {
        "rows": rows_per_page,
        "start": page_number,
        "cursorMark": cursor_mark,
        "sort": QUERY_ID_ASC,
        "fl": "content_html,content,id",
    }
    documents = client.search(q, **options)

    # Divide the document in chunks
    extract_reporting_obligations_for_document.chunks(zip(documents), int(CELERY_EXTRACT_TERMS_CHUNKS)).delay()


@shared_task
def extract_reporting_obligations_for_document(document):
    # Load typesystem
    ts = fetch_typesystem()

    # Initialise the RDF scheme
    initialise_rdf_scheme()

    django_doc = Document.objects.get(id=document["id"])

    # Check if already processed
    if django_doc.extract_ro_nlp_version == EXTRACT_RO_NLP_VERSION:
        logger.info("Skipped RO extraction for %s: Already processed.", django_doc.id)
        return

    if "content_html" not in document and "content" not in document:
        logger.info(
            "Skipped RO extraction for %s: 'content' and 'content_html' fields were empty in Solr", document["id"]
        )
        return

    logger.info("Started RO extraction for document id: %s", document["id"])

    is_html = False
    is_pdf = False
    r = None
    paragraph_request = None

    # Check if document is a html or pdf document
    if "content_html" in document:
        is_html = True

    elif "content_html" not in document and "content" in document:
        is_pdf = True
        # TODO Remove this later when pdf works
        # logger.warning("PDF CURRENTLY NOT SUPPORTED, SKIPPED.")
        # continue

    if is_html:
        r = get_html2text_cas(document["content_html"][0], document["id"], True)

    # Paragraph detection for PDF + fallback cas for not having a html2text request
    if is_pdf:
        r = get_cas_from_pdf(document["content"][0], document["id"])
        paragraph_request = r

    encoded_b64 = get_encoded_content_from_cas(r)

    # Paragraph Detection for HTML
    if is_html:
        paragraph_request = get_cas_from_paragraph_detection(encoded_b64, document["id"])

    if paragraph_request.status_code == 200:
        # Send to RO API
        res = json.loads(paragraph_request.content.decode("utf-8"))

        ro_request = get_reporting_obligations(res["cas_content"], document["id"])

        if ro_request.status_code == 200:
            ro_cas = base64.b64decode(json.loads(ro_request.content)["cas_content"]).decode("utf-8")

            cas = load_cas_from_xmi(ro_cas, typesystem=ts, trusted=True)
            sofa_reporting_obligations = cas.get_view("ReportingObligationsView").sofa_string
            sofa_html2text = cas.get_view(sofa_id_html2text).sofa_string

            # Save the HTML view of the reporting obligations
            minio_client = Minio(
                os.environ["MINIO_STORAGE_ENDPOINT"],
                access_key=os.environ["MINIO_ACCESS_KEY"],
                secret_key=os.environ["MINIO_SECRET_KEY"],
                secure=False,
            )
            bucket_name = "ro-html-output"
            try:
                minio_client.make_bucket(bucket_name)
            except BucketAlreadyOwnedByYou as err:
                pass
            except BucketAlreadyExists as err:
                pass

            logger.info("Created bucket: %s", bucket_name)
            filename = document["id"] + "-" + EXTRACT_RO_NLP_VERSION + ".html"

            html_file = open(filename, "w")
            html_file.write(sofa_reporting_obligations)
            html_file.close()

            minio_client.fput_object(bucket_name, html_file.name, filename, "text/html; charset=UTF-8")
            logger.info("Uploaded to minio")

            os.remove(html_file.name)

            # Now send the CAS to UIMA Html2Text for the VBTT annotations (paragraph_request)
            r = get_html2text_cas(sofa_reporting_obligations, document["id"], True)
            cas_html2text = load_cas_from_xmi(r.content.decode("utf-8"), typesystem=ts, trusted=True)

            # This is the CAS with reporting obligations wrapped in VBTT's
            # logger.info("cas_html2text: %s", cas_html2text.to_xmi())

            django_doc = Document.objects.get(id=document["id"])

            atomic_update_ro = [
                {
                    "id": document["id"],
                    "ro_highlight": {"set": {"v": "1", "str": sofa_html2text, "tokens": []}},
                }
            ]
            ro_tokens = atomic_update_ro[0]["ro_highlight"]["set"]["tokens"]
            j = 0

            # Save RO's to Django
            for vbtt in cas_html2text.get_view(sofa_id_html2text).select(VALUE_BETWEEN_TAG_TYPE_CLASS):
                if vbtt.tagName == "p":
                    ro_token = vbtt.get_covered_text()
                    attributes = vbtt.attributes
                    original_document_begin = get_values_from_html_attribute(attributes, "original_document_begin=")
                    original_document_end = get_values_from_html_attribute(attributes, "original_document_end=")

                    if len(ro_token.encode("utf-8")) < 32000:
                        token_to_add_ro = {
                            "t": ro_token,
                            "s": original_document_begin,
                            "e": original_document_end,
                            "y": "word",
                        }
                        ro_tokens.insert(j, token_to_add_ro)
                        j = j + 1

                    # Save to Django
                    r = ReportingObligation.objects.update_or_create(
                        name=vbtt.get_covered_text(),
                        definition=vbtt.get_covered_text(),
                        defaults={"version": EXTRACT_RO_NLP_VERSION},
                    )

                    r_offset = ReportingObligationOffsets.objects.update_or_create(
                        ro=r[0],
                        document=django_doc,
                        start=original_document_begin,
                        end=original_document_end,
                    )
                    logger.info(
                        "[CAS] Saved Reporting Obligation to Django: %s",
                        vbtt.get_covered_text(),
                    )

            # Store in Solr
            escaped_json_ro = json.dumps(atomic_update_ro[0]["ro_highlight"]["set"])
            atomic_update_ro[0]["ro_highlight"]["set"] = escaped_json_ro
            logger.info("Detected %s ROs in document: %s", len(ro_tokens), document["id"])
            if len(ro_tokens) > 0:
                post_pre_analyzed_to_solr(atomic_update_ro)

            # Send CAS to Reporting Obligations API

            website = django_doc.website
            source_name = website.name
            source_url = website.url

            if len(ro_tokens) > 0:

                r = save_to_rdf(cas_html2text, document["id"], source_name, source_url)
                if r.status_code == 200:
                    rdf_json = r.json()

                    logger.info("rdf_json: %s", rdf_json)

                    for item in rdf_json["children"]:
                        rdf_value = item["value"]
                        rdf_id = item["id"]

                        # Get the id from the rdf and add it to django
                        ReportingObligation.objects.update_or_create(
                            name=rdf_value,
                            definition=rdf_value,
                            defaults={
                                "rdf_id": rdf_id,
                                "version": EXTRACT_RO_NLP_VERSION,
                            },
                        )
                    # Store nlp version in django doc
                    django_doc.extract_ro_nlp_version = EXTRACT_RO_NLP_VERSION
                    django_doc.save()
                else:
                    logger.info(
                        "[RDF]: Failed to save CAS to RDF. Response code: %s",
                        r.status_code,
                    )
        else:
            logger.error(
                "Something went wrong in RO extraction (doc id: %s).",
                document["id"],
            )
    else:
        logger.error(
            "Something went wrong in paragraph detection (doc id: %s).",
            document["id"],
        )


@shared_task
def extract_terms(website_id, document_id=None):
    website = Website.objects.get(pk=website_id)
    website_name = website.name.lower()
    core = "documents"
    page_number = 0
    rows_per_page = 250
    cursor_mark = "*"

    if document_id:
        q = "id:" + document_id
        logger.info("Extract terms task, DOCUMENT: %s", document_id)
    else:
        logger.info("Extract terms task, WEBSITE: %s", website)
        q = QUERY_WEBSITE + website_name + " AND acceptance_state:accepted"

    # Load all documents from Solr
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    options = {
        "rows": rows_per_page,
        "start": page_number,
        "cursorMark": cursor_mark,
        "sort": QUERY_ID_ASC,
        "fl": "content_html,content,id",
    }
    documents = client.search(q, **options)

    # Divide the document in chunks
    extract_terms_for_document.chunks(zip(documents), int(CELERY_EXTRACT_TERMS_CHUNKS)).delay()


@shared_task
def extract_terms_for_document(document, debug_cas=True):
    logger.info("Started term extraction for document id: %s", document["id"])

    if "content_html" not in document and "content" not in document:
        logger.info(
            "Skipped term extraction for %s: 'content' and 'content_html' fields were empty in Solr", document["id"]
        )
        return

    typesystem = fetch_typesystem()

    django_doc = Document.objects.get(id=document["id"])
    # Check if already processed
    if django_doc.extract_terms_nlp_version in [EXTRACT_TERMS_NLP_VERSION, "started"]:
        logger.info("Skipped term extraction for %s: Already processed.", django_doc.id)
        return

    # Set nlp version "started" in django doc
    # This will prevent processing on failed documents
    # Manually empty the nlp version on the document when OK to rerun
    django_doc.extract_terms_nlp_version = "started"
    django_doc.save()

    r = None
    paragraph_request = None

    minio_client = Minio(
        os.environ["MINIO_STORAGE_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )
    bucket_name = "cas-files"
    try:
        minio_client.make_bucket(bucket_name)
    except BucketAlreadyOwnedByYou as err:
        pass
    except BucketAlreadyExists as err:
        pass

    try:
        if debug_cas:
            raise NoSuchKey

        cas_gz = minio_client.get_object(
            "cas-files",
            str(django_doc.id) + ".xml.gz",
        )
        cas = load_compressed_cas(cas_gz, typesystem)
        paragraph_request = {}
        paragraph_request["cas_content"] = base64.b64encode(bytes(cas.to_xmi(), "utf-8")).decode()
        paragraph_request["content_type"] = "html"
    except NoSuchKey:

        if "content_html" in document:
            logger.info(
                "Extracting terms from HTML document id: %s (%s chars)",
                document["id"],
                len(document["content_html"][0]),
            )
            # Html2Text - Get XMI from UIMA - Only when HTML not for PDFs
            r = get_html2text_cas(document["content_html"][0], django_doc.id, True)
            encoded_b64 = get_encoded_content_from_cas(r)
            # Paragraph Detection for HTML
            paragraph_request = json.loads(get_cas_from_paragraph_detection(encoded_b64, django_doc.id).content)

        elif "content_html" not in document and "content" in document:
            logger.info(
                "Extracting terms from PDF document id: %s (%s chars)",
                document["id"],
                len(document["content"][0]),
            )
            # Paragraph detection for PDF + fallback cas for not having a html2text request
            r = get_cas_from_pdf(document["content"][0], django_doc.id)
            paragraph_request = json.loads(r.content)

    # Term definition
    input_content = paragraph_request["cas_content"]
    definitions_request = get_cas_from_definitions_extract(input_content, django_doc.id)

    # Step 3: NLP TextExtract
    input_content = json.loads(definitions_request.content)["cas_content"]
    request_nlp = get_cas_from_text_extract(input_content, django_doc.id)

    # Decoded cas from termextract
    terms_decoded_cas = base64.b64decode(json.loads(request_nlp.content)["cas_content"]).decode("utf-8")

    # Load CAS files from NLP
    cas2 = cassis.load_cas_from_xmi(terms_decoded_cas, typesystem=typesystem, trusted=True)

    atomic_update_defined = [
        {
            "id": document["id"],
            "concept_defined": {
                "set": {
                    "v": "1",
                    "str": cas2.get_view(sofa_id_html2text).sofa_string,
                    "tokens": [],
                }
            },
        }
    ]
    concept_defined_tokens = atomic_update_defined[0]["concept_defined"]["set"]["tokens"]
    j = 0

    start_cas = time.time()
    # Term defined, we check which terms are covered by definitions
    definitions = []
    term_definition_uniq = []
    term_definition_uniq_idx = []
    # Each sentence is a definiton

    num_of_definitions = 0
    for sentence in list(cas2.get_view("html2textView").select(SENTENCE_CLASS)):
        # For annotations obtained via NLP algorithms, check if it has overlap with a user annotation (i.e., it is corrected by user), if so, skip the annotation
        if (
            has_overlapping_user_annotation(cas2, "html2textView", sentence, SENTENCE_CLASS_USER)
            and sentence.type == SENTENCE_CLASS
        ):
            continue
        term_definitions = []
        # Instead of saving sentence, save sentence + context (i.e. paragraph annotation)
        for par in cas2.get_view(sofa_id_html2text).select_covering(PARAGRAPH_CLASS, sentence):
            if (
                par.begin == sentence.begin
            ):  # if beginning of paragraph == beginning of a definition ==> this detected paragraph should replace the definition
                sentence = par
                break
        logger.debug("Found definition: %s", sentence.get_covered_text()[0:200])
        # cas2.get_view(sofa_id_html2text).add_annotation(  #not necassary to add paragraph annotation as definition?
        #    definition_type(begin=sentence.begin, end=sentence.end))
        # Find defined terms in definitions
        # 1) process 'defined in' user annotations
        # for token in cas2.get_view("html2textView").select_covered(TOKEN_CLASS_USER, sentence):
        # take those tfidf annotations with a cassis.token annotation covering them ==> the terms defined in the definition
        # for term_defined in cas2.get_view("html2textView").select_covered(TFIDF_CLASS_USER, token):
        #     if (term_defined.begin == token.begin) and (term_defined.end == token.end):
        #         term_definitions.append((term_defined, sentence))
        #         logger.debug("Found definition term: %s", term_defined.get_covered_text())
        #         break
        # 2) process 'defined in' annotations added by NLP algorithm
        for token in cas2.get_view("html2textView").select_covered(TOKEN_CLASS, sentence):
            # For annotations obtained via NLP algorithms, check if it has overlap with a user annotation (i.e. if it is corrected by user), if so, skip the annotation
            if has_overlapping_user_annotation(
                cas2, "html2textView", token, TOKEN_CLASS_USER
            ) or has_overlapping_user_annotation(cas2, "html2textView", token, TOKEN_CLASS_USER_REJECTED):
                continue
                # take those tfidf annotations with a cassis.token annotation covering them ==> the terms defined in the definition
            for term_defined in cas2.get_view("html2textView").select_covered(TFIDF_CLASS, token):
                if (term_defined.begin == token.begin) and (term_defined.end == token.end):
                    num_of_definitions = num_of_definitions + 1

                    term_definitions.append((term_defined, sentence))
                    logger.debug("Found definition term: %s", term_defined.get_covered_text())
                    break

        # store terms + definitions in a list of definitions
        definitions.append(term_definitions)

        # Keep track of definitions alone
        if len(term_definitions) and sentence.begin not in term_definition_uniq_idx:
            term_definition_uniq.append(sentence)
            term_definition_uniq_idx.append(sentence.begin)

        logger.debug("-----------------------------------------------------")

    logger.info("Number of definitions in the CAS: %s", num_of_definitions)

    # For solr
    for definition in term_definition_uniq:
        token_defined = definition.get_covered_text()
        start_defined = definition.begin
        end_defined = definition.end

        # Step 7: Send concept terms to Solr ('concept_defined' field)
        if len(token_defined.encode("utf-8")) < 32000:
            token_to_add_defined = {
                "t": token_defined,
                "s": start_defined,
                "e": end_defined,
                "y": "word",
            }
            concept_defined_tokens.insert(j, token_to_add_defined)
            j = j + 1

    # For django
    for group in definitions:
        concept_group = []
        for term, definition in group:
            lemma_name = ""
            token_defined = definition.get_covered_text()
            start_defined = definition.begin
            end_defined = definition.end

            # Retrieve the lemma for the term
            for lemma in cas2.get_view(sofa_id_html2text).select_covered(LEMMA_CLASS, term):
                if term.begin == lemma.begin and term.end == lemma.end:
                    lemma_name = lemma.value

            if len(token_defined.encode("utf-8")) < 32000:
                if len(term.term) <= MAX_TERM_LENGTH and lemma_name != "":
                    # Save Term Definitions in Django
                    lemma = Lemma.objects.update_or_create(name=lemma_name)
                    c = Concept.objects.update_or_create(
                        name=term.term,
                        definition=token_defined,
                        lemma=lemma_name,
                        defaults={
                            "version": EXTRACT_TERMS_NLP_VERSION,
                            "website_id": django_doc.website.id,
                        },
                    )
                    c[0].lemma_fk = lemma[0]
                    c[0].save()
                    concept_group.append(c[0])

                    ConceptDefined.objects.update_or_create(
                        concept=c[0],
                        document=django_doc,
                        startOffset=start_defined,
                        endOffset=end_defined,
                    )
                else:
                    logger.info(
                        "WARNING: Term '%s' (lemma: %s) has been skipped because the term name was too long or lemma was empty. "
                        "Consider disabling supergrams or change the length in the database",
                        term.get_covered_text(),
                        lemma_name,
                    )
        # Link definitions
        if len(concept_group) > 1:
            i = 0
            for from_concept in concept_group[i:]:
                for to_concept in concept_group[i + 1 :]:
                    from_concept.other.add(to_concept)
                i = i + 1

    # Step 5: Send term extractions to Solr (term_occurs field)

    # Convert the output to a readable format for Solr
    atomic_update = [
        {
            "id": document["id"],
            "concept_occurs": {
                "set": {
                    "v": "1",
                    "str": cas2.get_view(sofa_id_html2text).sofa_string,
                    "tokens": [],
                }
            },
        }
    ]
    concept_occurs_tokens = atomic_update[0]["concept_occurs"]["set"]["tokens"]

    num_of_terms = 0
    terms_unique_test = []

    # Select all Tfidfs from the CAS
    i = 0
    for term in list(cas2.get_view(sofa_id_html2text).select(TFIDF_CLASS)):

        # For annotations obtained via NLP algorithms, check if it has overlap with a user annotation (i.e. it is corrected by user), if so, skip the annotation
        if has_overlapping_user_annotation(
            cas2, "html2textView", term, TFIDF_CLASS_USER
        ) or has_overlapping_user_annotation(cas2, "html2textView", term, TFIDF_CLASS_USER_REJECTED):
            continue
        # FIXME: check if convered text ends with a space ?
        # Save the token information
        token = term.term
        score = term.tfidfValue
        start = term.begin
        end = term.end
        num_of_terms = num_of_terms + 1
        terms_unique_test.append((token, float(score.encode("utf-8")), start, end))

        # Encode score base64
        encoded_bytes = base64.b64encode(score.encode("utf-8"))
        encoded_score = str(encoded_bytes, "utf-8")

        token_to_add = {
            "t": token,
            "s": start,
            "e": end,
            "y": "word",
            "p": encoded_score,
        }
        concept_occurs_tokens.insert(i, token_to_add)
        i = i + 1

        # Retrieve the lemma for the term. Note: TFIDF_CLASS_USER will not always have lemma (but probably will: if the TFIDF_CLASS_USER annotations are properly whitelisted, the NLP component will add them)
        lemma_name = ""
        for lemma in cas2.get_view(sofa_id_html2text).select_covered(LEMMA_CLASS, term):
            if term.begin == lemma.begin and term.end == lemma.end:
                lemma_name = lemma.value

        if len(token) <= MAX_TERM_LENGTH and lemma_name != "":
            # queryset could return more than one lemma-token pair. Because Concept consists of lemma-token-def pairs
            # (lemma1-token1-def1), #(lemma1-token1-def2),..., therefore, we only take the first one.
            queryset = Concept.objects.filter(name=token, lemma=lemma_name)

            if queryset:
                # we only take the first one, because we are only interested in 'lemma-token', not in the definition, which could be different.
                # in angular, we will only look at 'lemma-token' in the Concept object. Reason for this workaround is a design mistake in ConceptOccurs object, which only needs 'lemma-token', not Concept ( 'lemma-token-definition' )
                concept = queryset[0]

                # Save Term OccursIn in Django
                if len(token) <= MAX_TERM_LENGTH and lemma_name != "":

                    # we check if ConceptOccurs already exists at that location with concept__name==token, to avoid adding same ConceptOccurs two times at same location (for instance for possible overlapping tfidf annotations with different definitions as Concept object ( term1 def1; term1 empty_def ) ) ==> ConceptOccurs.objects.update_or_create would create two ConceptOccurs instances.
                    q = ConceptOccurs.objects.filter(
                        concept__name=token, document=django_doc, startOffset=start, endOffset=end
                    )
                    if q:
                        continue

                    co = ConceptOccurs.objects.update_or_create(
                        concept=concept,
                        document=django_doc,
                        startOffset=start,
                        endOffset=end,
                    )

            else:
                lemma = Lemma.objects.update_or_create(name=lemma_name)

                # Concepts, without definition. Add them as Concept.

                c = Concept.objects.create(
                    name=token,
                    lemma=lemma_name,
                )

                c.lemma_fk = lemma[0]
                c.save()

                co = ConceptOccurs.objects.update_or_create(
                    concept=c,
                    document=django_doc,
                    startOffset=start,
                    endOffset=end,
                )

        else:
            logger.info(
                "WARNING: Term '%s' (lemma: %s) has been skipped because the term name was too long or lemma was empty. "
                "Consider disabling supergrams or change the length in the database",
                token,
                lemma_name,
            )

    logger.info("Complete CAS handling took %s seconds to succeed .", time.time() - start_cas)

    logger.info("length of terms: %s", len(terms_unique_test))
    logger.info("length of set terms: %s", len(set(terms_unique_test)))

    # Step 6: Post term_occurs to Solr
    escaped_json = json.dumps(atomic_update[0]["concept_occurs"]["set"])
    atomic_update[0]["concept_occurs"]["set"] = escaped_json
    logger.info(
        "Detected %s concepts in document: %s",
        len(concept_occurs_tokens),
        document["id"],
    )
    if len(concept_occurs_tokens) > 0:
        post_pre_analyzed_to_solr(atomic_update)

    # Step 8: Post term_defined to Solr
    escaped_json_def = json.dumps(atomic_update_defined[0]["concept_defined"]["set"])
    atomic_update_defined[0]["concept_defined"]["set"] = escaped_json_def
    logger.info(
        "Detected %s concept definitions in document: %s",
        len(concept_defined_tokens),
        document["id"],
    )
    if len(concept_defined_tokens) > 0:
        post_pre_analyzed_to_solr(atomic_update_defined)

    if debug_cas:
        bucket_name = "debug-cas-files"
        try:
            minio_client.make_bucket(bucket_name)
        except BucketAlreadyOwnedByYou as err:
            pass
        except BucketAlreadyExists as err:
            pass

        fn2 = document["id"] + ".xml.gz"

        f2 = save_compressed_cas(cas2, fn2)
        logger.info("[DEBUG CAS] Saved gzipped cas: %s", f2.name)

        minio_client.fput_object("debug-cas-files", fn2, f2.name)
        logger.info("[DEBUG CAS] Uploaded to minio")

        os.remove(f2.filename)
        logger.info("[DEBUG CAS] Removed file from system")
    else:
        # Clean up annotations for Webanno (keep value_between_tagtype and remove all annotations added by NLP algorithms)
        # We keep the following:
        # VALUE_BETWEEN_TAG_TYPE
        # PARAGRAPH_TYPE
        annotations_to_remove = [
            DEPENDENCY_CLASS,
            LEMMA_CLASS,
            TFIDF_CLASS,
            SENTENCE_CLASS,
            TOKEN_CLASS,
        ]

        for remove in annotations_to_remove:
            for anno in cas2.get_view(sofa_id_html2text).select(remove):
                cas2.get_view(sofa_id_html2text).remove_annotation(anno)

        logger.info("Created bucket: %s", bucket_name)
        filename = document["id"] + ".xml.gz"

        file = save_compressed_cas(cas2, filename)
        logger.info("Saved gzipped cas: %s", file.name)

        minio_client.fput_object(bucket_name, filename, file.name)
        logger.info("Uploaded to minio")

        os.remove(file.filename)
        logger.info("Removed file from system")

    # Store nlp version in django doc
    django_doc.extract_terms_nlp_version = EXTRACT_TERMS_NLP_VERSION
    django_doc.save()


def generate_typesystem_fisma():
    typesystem = TypeSystem()

    # Term
    term_type = typesystem.create_type(name="com.crosslang.fisma.Term")
    typesystem.add_feature(type_=term_type, name="term", rangeTypeName="uima.cas.String")
    typesystem.add_feature(type_=term_type, name="confidence", rangeTypeName="uima.cas.Float")

    # Definition
    typesystem.create_type(name="com.crosslang.fisma.Definition")

    # DefinitionTerm
    typesystem.create_type(name="com.crosslang.fisma.DefinitionTerm", supertypeName=term_type.name)

    return typesystem


@shared_task
def send_document_to_webanno(document_id):
    client = Pycaprio("http://webanno:8080", authentication=("admin", "admin"))
    # List projects
    projects = client.api.projects()
    project = projects[0]
    logger.info("PROJECT: %s", project)
    # Load CAS from Minio
    minio_client = Minio(
        os.environ["MINIO_STORAGE_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )
    try:
        cas_gz = minio_client.get_object("cas-files", document_id + ".xml.gz")
    except NoSuchKey:
        return None

    # Load typesystems
    merged_ts = merge_typesystems(fetch_typesystem(), generate_typesystem_fisma())

    cas = load_compressed_cas(cas_gz, merged_ts)

    # # Clean up annotations for Webanno
    SOFA_ID_HTML2TEXT = "html2textView"
    # Modify cas to make html2textview the _InitialView
    cas._sofas["_InitialView"] = cas._sofas[SOFA_ID_HTML2TEXT]
    del cas._sofas[SOFA_ID_HTML2TEXT]
    cas._views["_InitialView"] = cas._views[SOFA_ID_HTML2TEXT]
    del cas._views[SOFA_ID_HTML2TEXT]
    cas._sofas["_InitialView"].sofaID = "_InitialView"
    cas._sofas["_InitialView"].sofaNum = 1
    cas._sofas["_InitialView"].xmiID = 1

    cas_xmi = cas.to_xmi()

    new_document = client.api.create_document(
        project,
        document_id,
        cas_xmi.encode(),
        document_format=InceptionFormat.XMI,
        document_state=DocumentState.ANNOTATION_IN_PROGRESS,
    )
    logger.info("NEWDOC: %s", new_document)
    return new_document


@shared_task
def export_all_user_data(website_id, document_id=None):
    website = Website.objects.get(pk=website_id)
    website_name = website.name.lower()

    if document_id:
        documents = Document.objects.filter(pk=document_id)
    else:
        documents = Document.objects.filter(website=website)
        logger.info("Exporting User Annotations to Minio CAS files for website: %s", website_name)

    # Load CAS from Minio
    minio_client = Minio(
        os.environ["MINIO_STORAGE_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )

    # Load typesystem
    typesystem = fetch_typesystem()

    occurs_type = typesystem.get_type(TFIDF_CLASS_USER)
    defined_type = typesystem.get_type(TOKEN_CLASS_USER)

    occurs_type_rejected = typesystem.get_type(TFIDF_CLASS_USER_REJECTED)
    defined_type_rejected = typesystem.get_type(TOKEN_CLASS_USER_REJECTED)

    for document in documents:
        logger.info("Extracting document: %s", str(document.id))

        try:
            cas_gz = minio_client.get_object(
                "cas-files",
                str(document.id) + ".xml.gz",
            )

            cas = load_compressed_cas(cas_gz, typesystem)
            logger.info("Loaded cas from Minio")

            annotations = AnnotationWorklog.objects.filter(document=document)
            for annotation in annotations:
                rejected = False

                if annotation.concept_occurs:
                    acceptance_state = AcceptanceState.objects.filter(concept=annotation.concept_occurs.concept)
                else:
                    acceptance_state = AcceptanceState.objects.filter(concept=annotation.concept_defined.concept)

                if len(acceptance_state):
                    if acceptance_state.value == "Rejected":
                        rejected = True

                user = ""
                role = ""
                if annotation.user:
                    user = annotation.user.username
                    role = annotation.user.groups.name

                date = annotation.created_at

                if annotation.concept_defined:

                    begin = int(annotation.concept_defined.startOffset)
                    end = int(annotation.concept_defined.endOffset)

                    if rejected:
                        cas.get_view(sofa_id_html2text).add_annotation(
                            defined_type(begin=begin, end=end, user=user, role=role, datetime=date)
                        )
                        cas.get_view(sofa_id_html2text).add_annotation(
                            occurs_type(begin=begin, end=end, user=user, role=role, datetime=date)
                        )
                    else:
                        cas.get_view(sofa_id_html2text).add_annotation(
                            defined_type_rejected(begin=begin, end=end, user=user, role=role, datetime=date)
                        )
                        cas.get_view(sofa_id_html2text).add_annotation(
                            occurs_type_rejected(begin=begin, end=end, user=user, role=role, datetime=date)
                        )

                elif annotation.concept_occurs:
                    begin = int(annotation.concept_occurs.startOffset)
                    end = int(annotation.concept_occurs.endOffset)

                    if rejected:
                        cas.get_view(sofa_id_html2text).add_annotation(
                            occurs_type(begin=begin, end=end, user=user, role=role, datetime=date)
                        )
                    else:
                        cas.get_view(sofa_id_html2text).add_annotation(
                            occurs_type_rejected(begin=begin, end=end, user=user, role=role, datetime=date)
                        )

            filename = str(document.id) + ".xml.gz"

            file = save_compressed_cas(cas, filename)
            logger.info("Saved gzipped cas: %s", file.name)

            minio_client.fput_object("cas-files", filename, file.name)
            logger.info("Uploaded to minio")

            os.remove(file.filename)

        except NoSuchKey:
            pass
