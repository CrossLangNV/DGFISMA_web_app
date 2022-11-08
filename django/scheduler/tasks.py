from __future__ import absolute_import, unicode_literals

import json
import logging
import os
import shutil
import csv
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import pysolr
from celery import shared_task, chain
from django.core.exceptions import ValidationError
from django.db.models.functions import Length
from jsonlines import jsonlines
from django.db.models import Q
from langdetect import detect_langs
from langdetect.lang_detect_exception import LangDetectException
from minio import Minio, ResponseError
from minio.error import NoSuchKey
from minio.error import BucketAlreadyOwnedByYou, BucketAlreadyExists
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from tika import parser
from twisted.internet import reactor

from scheduler.extract import (
    extract_terms,
    extract_reporting_obligations,
    export_all_user_data,
)
from scheduler.extract_identifiers import retrieve_identifier
from searchapp.datahandling import score_documents
from searchapp.models import Website, Document, AcceptanceState, Tag, AcceptanceStateValue
from searchapp.solr_call import solr_search_website_sorted, solr_search_website_with_content

from scheduler.integration_tests import test_concept_highlights_it

from glossary.models import Concept, ConceptOccurs, ConceptDefined, AnnotationWorklog
from glossary.models import AcceptanceState as ConceptAcceptanceState
from glossary.models import Comment as ConceptComment
from glossary.models import Tag as ConceptTag
from obligations.models import ReportingObligation

logger = logging.getLogger(__name__)
workpath = os.path.dirname(os.path.abspath(__file__))

CONST_EXPORT = "/export/"
QUERY_ID_ASC = "id asc"
QUERY_WEBSITE = "website:"


@shared_task
def full_service_task(website_id, **kwargs):
    website = Website.objects.get(pk=website_id)
    logger.info("Full service for WEBSITE: %s", website.name)
    # the following subtasks are linked together in order:
    # sync_scrapy_to_solr -> parse_content -> sync (solr to django) -> score
    # a task only starts after the previous finished, immutable signatures (si)
    # are used since a task doesn't need the result of the previous task: see
    # https://docs.celeryproject.org/en/stable/userguide/canvas.html
    chain(
        sync_scrapy_to_solr_task.si(website_id),
        parse_content_to_plaintext_task.si(website_id, date=kwargs.get("date", None)),
        sync_documents_task.si(website_id, date=kwargs.get("date", None)),
        score_documents_task.si(website_id, date=kwargs.get("date", None)),
        check_documents_unvalidated_task.si(website_id),
        update_documents_custom_id_task.si(website_id),
        extract_terms.si(website_id),
        extract_reporting_obligations.si(website_id),
    )()


@shared_task
def delete_deprecated_acceptance_states():
    acceptance_states = (
        AcceptanceState.objects.all()
        .order_by("document")
        .distinct("document_id")
        .annotate(text_len=Length("document__title"))
        .filter(text_len__gt=1)
        .values()
    )
    documents = Document.objects.all().annotate(text_len=Length("title")).filter(text_len__gt=1).values()

    documents = [str(doc["id"]) for doc in documents]
    acceptances = [str(acc["document_id"]) for acc in acceptance_states]

    diff = list(set(acceptances) - set(documents))
    count = AcceptanceState.objects.all().filter(document_id__in=diff).delete()

    logger.info("Deleted %s deprecated acceptance states", count)


def reset_pre_analyzed_fields_document(document_id):
    logger.info("Resetting all PreAnalyzed fields for DOCUMENT: %s", document_id)
    core = "documents"
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    document = {"id": document_id, "concept_occurs": {"set": ""}, "concept_defined": {"set": ""}}
    client.add(document, commit=True)


@shared_task
def reset_pre_analyzed_fields(website_id):
    website = Website.objects.get(pk=website_id)
    logger.info("Resetting all PreAnalyzed fields for WEBSITE: %s", website.name)

    website_name = website.name.lower()
    page_number = 0
    rows_per_page = 250
    cursor_mark = "*"
    core = "documents"
    # select all records where content is empty and content_html is not
    q = "( concept_occurs: [* TO *] OR concept_defined: [* TO *] ) AND website:" + website_name
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    options = {"rows": rows_per_page, "start": page_number, "cursorMark": cursor_mark, "sort": QUERY_ID_ASC}
    results = client.search(q, **options)
    items = []

    for result in results:
        # add to document model and save
        document = {"id": result["id"], "concept_occurs": {"set": ""}, "concept_defined": {"set": ""}}
        items.append(document)

        if len(items) == 1000:
            logger.info("Got 1000 items, posting to solr")
            client.add(items, commit=True)
            items = []

    # Send to solr
    client.add(items, commit=True)


@shared_task
def export_documents():
    logger.info("Export all human validated documents...")
    # Find all human validated documents:
    # - no probability model
    # - ACCEPTED or REJECTED
    # - group by document
    human_states = AcceptanceState.objects.filter(
        (Q(value=AcceptanceStateValue.ACCEPTED) | Q(value=AcceptanceStateValue.REJECTED)) & Q(probability_model=None)
    ).order_by("document")

    core = "documents"
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    workdir = workpath + CONST_EXPORT + export_documents.request.id
    os.makedirs(workdir)

    # Find documents for all document ids found in human validated acceptance states
    for human_state in human_states:
        human_validation = {"human_validation": human_state.value, "username": human_state.user.username}
        doc_id = human_state.document.id
        q = "id:" + str(doc_id)
        documents = client.search(q, **{})
        for document in documents:
            # Each .jsonl file contains min 3 lines: document, auto classifier, human validation
            jsonl_file = Path(workdir + "/doc_" + document["id"] + ".jsonl")
            if jsonl_file.is_file():
                # if the file for a document id already exists, append human validation
                with jsonl_file.open(mode="a") as f:
                    f.write(json.dumps(human_validation))
                    f.write("\n")
            else:
                # file for document id doesn't exist, write document, auto classifier and human validation
                with jsonl_file.open(mode="w") as f:
                    # DOCUMENT
                    f.write(json.dumps(document))
                    f.write("\n")

                    # Get acceptance state AUTO CLASSIFIER from django model
                    acceptance_state_qs = AcceptanceState.objects.filter(
                        document__id=document["id"], probability_model="auto classifier"
                    )
                    if acceptance_state_qs:
                        acceptance_state = acceptance_state_qs[0]
                        classifier_score = acceptance_state.accepted_probability
                        classifier_status = acceptance_state.value
                        classifier_index = acceptance_state.accepted_probability_index
                        classifier = {
                            "classifier_status": classifier_status,
                            "classifier_score": classifier_score,
                            "classifier_index": classifier_index,
                        }
                        f.write(json.dumps(classifier))
                        f.write("\n")

                    # HUMAN validation
                    f.write(json.dumps(human_validation))

    # create zip file for all .jsonl files
    zip_destination = workpath + CONST_EXPORT + export_documents.request.id
    shutil.make_archive(zip_destination, "zip", workpath + CONST_EXPORT + export_documents.request.id)

    # upload zip to minio
    minio_client = Minio(
        os.environ["MINIO_STORAGE_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )
    try:
        minio_client.make_bucket("export")
    except BucketAlreadyOwnedByYou as err:
        pass
    except BucketAlreadyExists as err:
        pass
    except ResponseError as err:
        raise
    minio_client.fput_object("export", export_documents.request.id + ".zip", zip_destination + ".zip")

    shutil.rmtree(workpath + CONST_EXPORT + export_documents.request.id)
    os.remove(zip_destination + ".zip")
    logging.info("Removed: %s", zip_destination + ".zip")


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


@shared_task
def handle_document_updates_task(website_id):
    website = Website.objects.get(pk=website_id)
    logger.info("Handle updates for WEBSITE: %s", str(website))
    # process files from minio
    minio_client = Minio(
        os.environ["MINIO_STORAGE_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )
    bucket_name = website.name.lower()
    # get all content_hashes
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + "documents")
    client_archive = pysolr.Solr(os.environ["SOLR_URL"] + "/" + "archive")
    options = {"rows": 250000, "fl": "id,content_hash"}
    results = client.search("*:*", **options)
    content_hashes = {}
    for result in results:
        if "content_hash" in result:
            content_hashes[result["id"]] = result["content_hash"]
    logger.info("Found " + str(len(content_hashes)) + " hashes")

    try:
        # retrieve jsonlines files from minio
        objects = minio_client.list_objects(bucket_name)
        archive_items = []
        for obj in objects:
            logger.info("Working on %s", obj.object_name)
            file_data = minio_client.get_object(bucket_name, obj.object_name)
            with jsonlines.Reader(BytesIO(file_data.data)) as reader:
                for obj in reader:
                    # check if updated (see if we can find the hash from the jsonl object in the list of known content_hashes)
                    if obj["id"] in content_hashes and obj["content_hash"] != content_hashes[obj["id"]]:
                        archive_items.append(obj["id"])

            logger.info("Going to archive " + str(len(archive_items)) + " items")
            # archive_items is the list of all solr document ids that need to be copied to the archive
            for chunk in chunks(archive_items, 100):
                solr_ids = ("AND id: ").join(chunk)
                options = {"rows": 100}
                results = client.search("id:" + solr_ids, **options)
                # update ids in results
                updates = []
                for result in results:
                    result["document_id"] = result["id"]
                    result["id"] = result["id"] + result["content_hash"]
                    del result["_version_"]
                    updates.append(result)
                # send results to archive
                client_archive.add(updates, commit=True)
                updates = []

    except ResponseError as err:
        raise


@shared_task
def get_stats_for_html_size(website_id):
    core = "documents"
    page_number = 0
    rows_per_page = 250
    cursor_mark = "*"

    website = Website.objects.get(pk=website_id)
    website_name = website.name.lower()
    q = QUERY_WEBSITE + website_name + " AND content_html:* AND acceptance_state:accepted"

    # Load all documents from Solr
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    options = {
        "rows": rows_per_page,
        "start": page_number,
        "cursorMark": cursor_mark,
        "sort": QUERY_ID_ASC,
        "fl": "content_html,id",
    }
    documents = client.search(q, **options)

    size_1 = 0
    size_2 = 0
    for document in documents:
        if document["content_html"] is not None:
            if len(document["content_html"][0]) > 500000:
                size_1 = size_1 + 1
                logger.info("500K document id: %s", document["id"])
            elif len(document["content_html"][0]) > 1000000:
                size_2 = size_2 + 1
                logger.info("1M document id: %s", document["id"])

    logger.info("[Document stats]: Documents over 500k lines: %s", size_1)
    logger.info("[Document stats]: Documents over 1M lines: %s", size_2)


@shared_task
def score_documents_task(website_id, **kwargs):
    # lookup documents for website and score them
    website = Website.objects.get(pk=website_id)
    logger.info("Scoring documents with WEBSITE: " + website.name)
    solr_documents = solr_search_website_with_content("documents", website.name, date=kwargs.get("date", None))
    use_pdf_files = True
    if website.name.lower() == "eurlex":
        use_pdf_files = False
    score_documents(website.name, solr_documents, use_pdf_files)


@shared_task
def sync_documents_task(website_id, **kwargs):
    # lookup documents for website and sync them
    website = Website.objects.get(pk=website_id)
    logger.info("Syncing documents with WEBSITE: " + website.name)
    # query Solr for available documents and sync with Django

    date = kwargs.get("date", None)
    solr_documents = solr_search_website_sorted(core="documents", website=website.name.lower(), date=date)
    for solr_doc in solr_documents:

        solr_doc_date_types = solr_doc.get("dates_type", [""])
        solr_doc_date_dates = solr_doc.get("dates", [""])
        solr_doc_date_info = solr_doc.get("dates_info", [""])

        solr_doc_date_of_effect = None
        for date_info in solr_doc_date_info:
            if date_info.lower().startswith("entry into force"):
                index = solr_doc_date_info.index(date_info)
                if solr_doc_date_types[index] == "date of effect":
                    solr_doc_date_of_effect = solr_doc_date_dates[index]
                    break

        solr_doc_date = solr_doc.get("date", [datetime.now()])[0]
        solr_doc_date_last_update = solr_doc.get("date_last_update", datetime.now())
        # sanity check in case date_last_update was a solr array field
        if isinstance(solr_doc_date_last_update, list):
            solr_doc_date_last_update = solr_doc_date_last_update[0]
        data = {
            "author": solr_doc.get("misc_author", [""])[0][:500],
            "celex": solr_doc.get("celex", [""])[0][:20],
            "custom_id": solr_doc.get("custom_id", [""])[0][:100],
            "consolidated_versions": ",".join(x.strip() for x in solr_doc.get("consolidated_versions", [""])),
            "date": solr_doc_date,
            "date_of_effect": solr_doc_date_of_effect,
            "date_last_update": solr_doc_date_last_update,
            "eli": solr_doc.get("eli", [""])[0],
            "file_url": solr_doc.get("file_url", [None])[0],
            "status": solr_doc.get("status", [""])[0][:100],
            "summary": "".join(x.strip() for x in solr_doc.get("summary", [""])),
            "title": solr_doc.get("title", [""])[0][:1000],
            "title_prefix": solr_doc.get("title_prefix", [""])[0],
            "type": solr_doc.get("type", [""])[0],
            "url": solr_doc["url"][0],
            "various": "".join(x.strip() for x in solr_doc.get("various", [""])),
            "website": website,
        }
        # Update or create the document, this returns a tuple with the django document and a boolean indicating
        # whether or not the document was created
        current_doc, current_doc_created = Document.objects.update_or_create(id=solr_doc["id"], defaults=data)

    if not date:
        # check for outdated documents based on last time a document was found during scraping
        how_many_days = 30
        outdated_docs = Document.objects.filter(date_last_update__lte=datetime.now() - timedelta(days=how_many_days))
        up_to_date_docs = Document.objects.filter(date_last_update__gte=datetime.now() - timedelta(days=how_many_days))
        # tag documents that have not been updated in a while
        for doc in outdated_docs:
            try:
                Tag.objects.create(value="OFFLINE", document=doc)
            except ValidationError as e:
                # tag exists, skip
                logger.debug(str(e))
        # untag if the documents are now up to date
        for doc in up_to_date_docs:
            # fetch OFFLINE tag for this document
            try:
                offline_tag = Tag.objects.filter(value="OFFLINE", document=doc)
                offline_tag.delete()
            except Tag.DoesNotExist:
                # OFFLINE tag not found, skip
                pass


@shared_task
def delete_documents_not_in_solr_task(website_id):
    website = Website.objects.get(pk=website_id)
    # query Solr for available documents
    solr_documents = solr_search_website_sorted(core="documents", website=website.name.lower())
    # delete django Documents that no longer exist in Solr
    django_documents = list(Document.objects.filter(website=website))
    django_doc_ids = [str(django_doc.id) for django_doc in django_documents]
    solr_doc_ids = [solr_doc["id"] for solr_doc in solr_documents]
    to_delete_doc_ids = set(django_doc_ids) - set(solr_doc_ids)
    to_delete_docs = Document.objects.filter(pk__in=to_delete_doc_ids)
    logger.info("Deleting deprecated documents...")
    to_delete_docs.delete()


@shared_task
def scrape_website_task(website_id, delay=True):
    # lookup website and start scraping
    website = Website.objects.get(pk=website_id)
    logger.info("Scraping with WEBSITE: " + website.name)
    spiders = [
        {"id": "bis"},
        {"id": "eiopa"},
        {"id": "esma"},
        {"id": "eurlex", "type": "directives"},
        {"id": "eurlex", "type": "decisions"},
        {"id": "eurlex", "type": "regulations"},
        {"id": "fsb"},
        {"id": "srb"},
        {"id": "eba", "type": "guidelines"},
        {"id": "eba", "type": "recommendations"},
    ]
    for spider in spiders:
        if spider["id"].lower() == website.name.lower():
            if "type" not in spider:
                spider["type"] = ""
            date_start = None
            date_end = None
            # schedule scraping task
            if spider["id"] == "eurlex":
                for year in range(1951, datetime.now().year + 1):
                    date_start = "0101" + str(year)
                    date_end = "3112" + str(year)
                    if delay:
                        launch_crawler.delay(spider["id"], spider["type"], date_start, date_end)
                    else:
                        launch_crawler(spider["id"], spider["type"], date_start, date_end)
            else:
                if delay:
                    launch_crawler.delay(spider["id"], spider["type"], date_start, date_end)
                else:
                    launch_crawler(spider["id"], spider["type"], date_start, date_end)


@shared_task
def launch_crawler(spider, spider_type, date_start, date_end):
    scrapy_settings_path = "scraper.scrapy_app.settings"
    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", scrapy_settings_path)
    settings = get_project_settings()
    settings["celery_id"] = launch_crawler.request.id
    runner = CrawlerRunner(settings=settings)
    d = runner.crawl(spider, spider_type=spider_type, spider_date_start=date_start, spider_date_end=date_end)
    d.addBoth(lambda _: reactor.stop())
    reactor.run()  # the script will block here until the crawling is finished


@shared_task
def parse_content_to_plaintext_task(website_id, **kwargs):
    website = Website.objects.get(pk=website_id)
    website_name = website.name.lower()
    logger.info("Adding content to each %s document.", website_name)
    page_number = 0
    rows_per_page = 250
    cursor_mark = "*"
    date = kwargs.get("date", None)
    # select all records where content is empty and content_html is not
    q = '-content: ["" TO *] AND ( content_html: [* TO *] OR file_name: [* TO *] ) AND website:' + website_name
    if date:
        q = q + " AND date:[" + date + " TO NOW]"  # eg. 2013-07-17T00:00:00Z

    core = "documents"
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    options = {"rows": rows_per_page, "start": page_number, "cursorMark": cursor_mark, "sort": QUERY_ID_ASC}
    results = client.search(q, **options)
    items = []
    minio_client = Minio(
        os.environ["MINIO_STORAGE_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )
    for result in results:
        # Parse content
        content_text = None
        if "content_html" in result:
            output = parser.from_buffer(result["content_html"][0])
            content_text = output["content"]
        elif "file_name" in result:
            # If there is more than 1 pdf, we rely on score_documents to extract
            # the content of the pdf with the highest score
            if len(result["file_name"]) == 1:
                try:
                    file_data = minio_client.get_object(
                        os.environ["MINIO_STORAGE_MEDIA_BUCKET_NAME"], result["file_name"][0]
                    )
                    output = BytesIO()
                    for d in file_data.stream(32 * 1024):
                        output.write(d)
                    content_text = parser.from_buffer(output.getvalue())
                    if "content" in content_text:
                        content_text = content_text["content"]
                except ResponseError as err:
                    print(err)
                except NoSuchKey as err:
                    logger.warn(
                        "Could not find file '%s' in '%s",
                        os.environ["MINIO_STORAGE_MEDIA_BUCKET_NAME"],
                        result["file_name"][0],
                    )

        # Store plaintext
        if content_text is None:
            # could not parse content
            logger.info("No output for: %s, removing content", result["id"])
        else:
            logger.debug("Got content for: %s (%s)", result["id"], len(content_text))

        # add to document model and save
        document = {"id": result["id"], "content": {"set": content_text}}
        items.append(document)

        if len(items) == 1000:
            logger.info("Got 1000 items, posting to solr")
            client.add(items, commit=True)
            items = []

    # Send to solr
    client.add(items, commit=True)


def is_document_english(plain_text):
    english = False
    detect_threshold = 0.4
    try:
        langs = detect_langs(plain_text)
        number_langs = len(langs)
        # trivial case for 1 language detected
        if number_langs == 1:
            if langs[0].lang == "en":
                english = True
        # if 2 or more languages are detected, consider detect probability
        else:
            for detected in langs:
                if detected.lang == "en" and detected.prob >= detect_threshold:
                    english = True
                    break
    except LangDetectException:
        pass
    return english


@shared_task
def sync_scrapy_to_solr_task(website_id):
    website = Website.objects.get(pk=website_id)
    website_name = website.name.lower()
    logger.info("Scrapy to Solr WEBSITE: %s", str(website))
    # process files from minio
    minio_client = Minio(
        os.environ["MINIO_STORAGE_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )
    bucket_name = website.name.lower()
    bucket_archive_name = bucket_name + "-archive"
    bucket_failed_name = bucket_name + "-failed"
    create_bucket(minio_client, bucket_name)
    create_bucket(minio_client, bucket_archive_name)
    create_bucket(minio_client, bucket_failed_name)
    core = "documents"

    # Fetch existing id's
    client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    options = {"rows": 250000, "fl": "id,content_hash"}
    results = client.search("website: " + website_name, **options)
    content_ids = []
    for result in results:
        content_ids.append(result["id"])
    logger.info("Found " + str(len(content_ids)) + " ids")

    try:
        objects = minio_client.list_objects(bucket_name)
        for obj in objects:
            # Fetch jsonlines file
            logger.info("Working on %s", obj.object_name)
            file_data = minio_client.get_object(bucket_name, obj.object_name)
            updated_items = 0
            new_items = 0
            results = []
            # a json-line file may contain up to 1000 json documents (memory issue ?)
            with jsonlines.Reader(BytesIO(file_data.data)) as reader:
                for json in reader:
                    if json["id"] in content_ids:
                        updated_items = updated_items + 1
                        results.append(rewrite_json_doc_to_update(json))
                    else:
                        new_items = updated_items + 1
                        results.append(json)
                    if len(results) == 1000:
                        # Update solr index
                        client.add(results, commit=True)
                        results = []

            logger.info("Found " + str(updated_items) + " updated items")
            logger.info("Found " + str(new_items) + " new items")

            # Update solr index one last time
            client.add(results, commit=True)

            # move jsonlines file to archive
            logger.info("ALL good, MOVE to '%s'", bucket_archive_name)
            minio_client.copy_object(bucket_archive_name, obj.object_name, bucket_name + "/" + obj.object_name)
            minio_client.remove_object(bucket_name, obj.object_name)

    except Exception as err:
        # move jsonlines file to failed folder
        logger.info("FAILED, MOVE to '%s'", bucket_failed_name)
        minio_client.copy_object(bucket_failed_name, obj.object_name, bucket_name + "/" + obj.object_name)
        minio_client.remove_object(bucket_name, obj.object_name)
        raise


def rewrite_json_doc_to_update(doc):
    for field in doc:
        if field != "id":
            doc[field] = {"set": doc[field]}
    return doc


@shared_task
def check_documents_unvalidated_task(website_id):
    website = Website.objects.get(pk=website_id)
    logger.info("Set unvalidated field for all documents for website: %s", str(website))
    docs = Document.objects.filter(website=website)
    for doc in docs:
        # get all acceptance states that are not unvalidated
        validated_states = AcceptanceState.objects.filter(document=doc).exclude(value=AcceptanceStateValue.UNVALIDATED)
        # update document unvalidated state accordingly
        if not validated_states:
            doc.unvalidated = True
        else:
            doc.unvalidated = False
        doc.save()


@shared_task
def update_documents_custom_id_task(website_id):
    website = Website.objects.get(pk=website_id)
    logger.info("Set custom_id field for all documents for website: %s", str(website))
    solr_documents = solr_search_website_with_content("documents", website.name)
    for doc in solr_documents:
        if "content" in doc:
            custom_id = retrieve_identifier(doc)
            logger.debug(custom_id)
            django_doc = Document.objects.get(pk=str(doc["id"]))
            django_doc.custom_id = custom_id
            django_doc.save()
            solr_client = pysolr.Solr(os.environ["SOLR_URL"] + "/documents")
            document = {"id": str(doc["id"]), "custom_id": {"set": custom_id}}
            solr_client.add(document, commit=True)


def create_bucket(client, name):
    try:
        client.make_bucket(name)
    except BucketAlreadyOwnedByYou as err:
        pass
    except BucketAlreadyExists as err:
        pass
