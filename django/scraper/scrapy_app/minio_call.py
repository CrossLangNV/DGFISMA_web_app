from minio.error import ResponseError
import os
from minio import Minio
import uuid
from io import BytesIO
from scrapy.exporters import BaseItemExporter
from scrapy import signals
from scrapy.utils.python import to_bytes
from scrapy.utils.serialize import ScrapyJSONEncoder
from minio.error import BucketAlreadyOwnedByYou, BucketAlreadyExists

import logging

FLUSH_DOCS = 1000


class S3ItemExporter(BaseItemExporter):
    items = []

    def __init__(self, bucket, **kwargs):
        self._configure(kwargs)
        self.bucket = bucket
        kwargs.setdefault("ensure_ascii", not self.encoding)
        self.encoder = ScrapyJSONEncoder(**kwargs)
        self.logger = logging.getLogger(__name__)

    def start_exporting(self):
        self.client = connect()
        self.logger.info("Bucket '%s' will be created if not exist", self.bucket)
        create_bucket(self.client, self.bucket)

    def finish_exporting(self):
        if len(self.items) == 0:
            return
        data = ""
        for item in self.items:
            itemdict = dict(self._get_serialized_fields(item))
            data += self.encoder.encode(itemdict) + "\n"
        object_bytes = data.encode("utf-8")
        object_stream = BytesIO(object_bytes)
        size = len(object_bytes)

        task_id = self.items[0]["task"]
        if task_id is None:
            name = str(uuid.uuid4()) + ".jsonl"
        else:
            name = str(uuid.uuid4()) + "--" + task_id + ".jsonl"

        put_object(self.client, self.bucket, name, object_stream, size)
        self.logger.info("Wrote %d items to jsonlines feed: %s", len(self.items), self.bucket + "/" + name)
        self.items = []

    def export_item(self, item):
        self.items.append(item)
        if len(self.items) >= FLUSH_DOCS:
            self.logger.info("S3 item exporter got %d item, writing to minio", FLUSH_DOCS)
            self.finish_exporting()


# S3 Related
def connect():
    return Minio(
        os.environ["MINIO_STORAGE_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )


def create_bucket(client, name):
    try:
        client.make_bucket(name)
    except BucketAlreadyOwnedByYou as err:
        pass
    except BucketAlreadyExists as err:
        pass


def put_object(client, bucket_name, object_name, object_data, size):
    return client.put_object(bucket_name, object_name, object_data, size)
