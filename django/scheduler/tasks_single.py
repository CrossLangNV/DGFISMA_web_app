import json
import logging
import os
from io import BytesIO

import pysolr
import requests
from celery import shared_task, chain
from django.core.serializers import serialize
from minio import Minio, ResponseError
from minio.error import BucketAlreadyOwnedByYou, BucketAlreadyExists
from tika import parser

from scheduler.extract import extract_terms_for_document, fetch_typesystem, extract_reporting_obligations
from searchapp.datahandling import classify
from searchapp.models import Website, Document, AcceptanceState, AcceptanceStateValue

logger = logging.getLogger(__name__)
workpath = os.path.dirname(os.path.abspath(__file__))

CONST_UPDATE_WITH_COMMIT = "/update?commit=true"


@shared_task
def full_service_single(document_id):
    chain(
        minio_upload.s(document_id),
        solr_upload.si(document_id),
        parse_content_to_plaintext.si(document_id),
        score_document.s(),
        extract_terms_for_document.s(),
        extract_reporting_obligations.si(1, document_id)
    )()


@shared_task
def minio_upload(document_id):
    document_json = document_to_json(document_id)
    website = Website.objects.get(pk=document_json["website"])
    document_json["website"] = website.name.lower()
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

    object_bytes = json.dumps(document_json).encode("utf-8")
    object_stream = BytesIO(object_bytes)
    size = len(object_bytes)
    minio_file_name = document_json["id"] + ".jsonl"
    minio_client.put_object(bucket_name, minio_file_name, object_stream, size)
    return minio_file_name


def document_to_json(document_id):
    document = Document.objects.get(pk=document_id)
    document_json = json.loads(serialize("json", [document]))[0]["fields"]
    document_json["id"] = str(document.id)

    document_json["file_name"] = document_json.pop("file")

    list_to_pop = ["unvalidated", "extract_terms_nlp_version", "extract_ro_nlp_version"]
    for key in list_to_pop:
        document_json.pop(key)
    return document_json


def create_bucket(client, name):
    try:
        client.make_bucket(name)
    except BucketAlreadyOwnedByYou as err:
        pass
    except BucketAlreadyExists as err:
        pass


@shared_task
def solr_upload(document_id):
    document_json = document_to_json(document_id)
    website = Website.objects.get(pk=document_json["website"])
    document_json["website"] = website.name.lower()
    bucket_name = document_json["website"]
    minio_client = Minio(
        os.environ["MINIO_STORAGE_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )
    bucket_archive_name = bucket_name + "-archive"
    bucket_failed_name = bucket_name + "-failed"
    create_bucket(minio_client, bucket_archive_name)
    create_bucket(minio_client, bucket_failed_name)
    core = "documents"

    file_name = document_id + ".jsonl"
    file_data = minio_client.get_object(bucket_name, file_name)
    url = os.environ["SOLR_URL"] + "/" + core + "/update/json/docs"
    output = BytesIO()
    for d in file_data.stream(32 * 1024):
        output.write(d)
    r = requests.post(url, output.getvalue())
    json_r = r.json()
    logger.info("SOLR RESPONSE: %s", json_r)
    if json_r["responseHeader"]["status"] == 0:
        logger.info("ALL good, MOVE to '%s'", bucket_archive_name)
        minio_client.copy_object(bucket_archive_name, file_name, bucket_name + "/" + file_name)
    else:
        logger.info("NOT so good, MOVE to '%s'", bucket_failed_name)
        minio_client.copy_object(bucket_failed_name, file_name, bucket_name + "/" + file_name)

    minio_client.remove_object(bucket_name, file_name)
    # Update solr index
    requests.get(os.environ["SOLR_URL"] + "/" + core + CONST_UPDATE_WITH_COMMIT)
    return document_id


@shared_task
def parse_content_to_plaintext(document_id):
    document_json = document_to_json(document_id)
    # Make sure solr index is updated
    core = "documents"
    requests.get(os.environ["SOLR_URL"] + "/" + core + CONST_UPDATE_WITH_COMMIT)

    minio_client = Minio(
        os.environ["MINIO_STORAGE_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )
    solr_client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)

    # Parse content
    content_text = None
    if "file_name" in document_json:
        try:
            file_data = minio_client.get_object(os.environ["MINIO_STORAGE_MEDIA_BUCKET_NAME"], document_json["file_name"])
            output = BytesIO()
            for d in file_data.stream(32 * 1024):
                output.write(d)
            content_text = parser.from_buffer(output.getvalue())
            if "content" in content_text:
                content_text = content_text["content"]
        except ResponseError as err:
            print(err)

    # Store plaintext
    if content_text is None:
        # could not parse content
        logger.info("No content for: %s", document_json["id"])
    else:
        logger.debug("Got content for: %s (%s)", document_json["id"], len(content_text))
        # add to document model and save
        document = {"id": document_json["id"], "content": {"set": content_text}}
        document_json["content"] = content_text
        logger.info("Post to solr")
        solr_client.add(document)
        requests.get(os.environ["SOLR_URL"] + "/" + core + CONST_UPDATE_WITH_COMMIT)
    return document_json


@shared_task
def score_document(document_json):
    logger.info("Oan: document_json %s", document_json)
    CLASSIFIER_ERROR_SCORE = -9999
    DJANGO_ERROR_SCORE = -1
    ACCEPTED_THRESHOLD = 0.5
    core = "documents"
    solr_client = pysolr.Solr(os.environ["SOLR_URL"] + "/" + core)
    classifier_response = classify(document_json["id"], document_json["content"], "pdf")
    accepted_probability = classifier_response["accepted_probability"]
    # Check acceptance
    if accepted_probability != CLASSIFIER_ERROR_SCORE:
        # Validated
        classifier_status = (
            AcceptanceStateValue.ACCEPTED
            if accepted_probability > ACCEPTED_THRESHOLD
            else AcceptanceStateValue.REJECTED
        )
    else:
        # couldn't classify
        accepted_probability = DJANGO_ERROR_SCORE
        classifier_status = AcceptanceStateValue.UNVALIDATED

    # Storage
    django_doc = Document.objects.get(pk=document_json["id"])
    django_doc.acceptance_state_max_probability = accepted_probability
    django_doc.save()
    score_update = {
        "id": document_json["id"],
        "accepted_probability": {"set": accepted_probability},
        "acceptance_state": {"set": classifier_status},
    }
    # Store AcceptanceState
    AcceptanceState.objects.update_or_create(
        probability_model="auto classifier",
        document=django_doc,
        defaults={
            "value": classifier_status,
            "accepted_probability": accepted_probability,
            "accepted_probability_index": 0,
        },
    )

    # Store score in solr
    logger.info("Posting score to SOLR")
    solr_client.add(score_update)
    requests.get(os.environ["SOLR_URL"] + "/" + core + "/update?commit=true")

    # store document content in array, so it mimics a solr document
    document_json["content"] = [document_json["content"]]
    return document_json
