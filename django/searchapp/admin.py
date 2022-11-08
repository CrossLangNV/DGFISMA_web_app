import logging
import os

import requests
from django.contrib import admin
from django.contrib.auth.models import User

from admin_rest.models import site as rest_site
from scheduler import tasks
from scheduler.extract import send_document_to_webanno
from .models import Website, Attachment, Document, AcceptanceState, Comment, Tag

logger = logging.getLogger(__name__)

admin.site.register(Attachment)

rest_site.register(Website)
rest_site.register(Document)
rest_site.register(Attachment)
rest_site.register(AcceptanceState)
rest_site.register(Comment)
rest_site.register(Tag)
rest_site.register(User)


def reset_pre_analyzed_fields(modeladmin, request, queryset):
    for website in queryset:
        tasks.reset_pre_analyzed_fields.delay(website.id)


def full_service(modeladmin, request, queryset):
    for website in queryset:
        tasks.full_service_task.delay(website.id)


def scrape_website(modeladmin, request, queryset):
    for website in queryset:
        tasks.scrape_website_task.delay(website.id)


def parse_content_to_plaintext(modeladmin, request, queryset):
    for website in queryset:
        tasks.parse_content_to_plaintext_task.delay(website.id)


def sync_scrapy_to_solr(modeladmin, request, queryset):
    for website in queryset:
        tasks.sync_scrapy_to_solr_task.delay(website.id)


def sync_documents(modeladmin, request, queryset):
    for website in queryset:
        tasks.sync_documents_task.delay(website.id)


def delete_documents_not_in_solr(modeladmin, request, queryset):
    for website in queryset:
        tasks.delete_documents_not_in_solr_task.delay(website.id)


def score_documents(modeladmin, request, queryset):
    for website in queryset:
        tasks.score_documents_task.delay(website.id)


def check_documents_unvalidated(modeladmin, request, queryset):
    for website in queryset:
        tasks.check_documents_unvalidated_task.delay(website.id)


def update_documents_custom_id(modeladmin, request, queryset):
    for website in queryset:
        tasks.update_documents_custom_id_task.delay(website.id)


def export_documents(modeladmin, request, queryset):
    website_ids = []
    for website in queryset:
        website_ids.append(website.id)
    tasks.export_documents.delay(website_ids)


def extract_terms(modeladmin, request, queryset):
    for website in queryset:
        tasks.extract_terms.delay(website.id)


def extract_reporting_obligations(modeladmin, request, queryset):
    for website in queryset:
        tasks.extract_reporting_obligations.delay(website.id)
    logger.info("Reporting Obligations extraction has finished!")


def handle_document_updates(modeladmin, request, queryset):
    for website in queryset:
        tasks.handle_document_updates_task.delay(website.id)


def delete_from_solr(modeladmin, request, queryset):
    for website in queryset:
        r = requests.post(
            os.environ["SOLR_URL"] + "/" + "documents" + "/update?commit=true",
            headers={"Content-Type": "application/json"},
            data='{"delete": {"query": "website:' + website.name.lower() + '"}}',
        )
        logger.info("Deleted solr content for website: %s => %s", website.name.lower(), r.json())


def export_all_user_data(modeladmin, request, queryset):
    for website in queryset:
        tasks.export_all_user_data.delay(website.id)


def test_concept_highlights_it(modeladmin, request, queryset):
    tasks.test_concept_highlights_it.delay()


class WebsiteAdmin(admin.ModelAdmin):
    list_display = ["name", "count_documents"]
    ordering = ["name"]
    actions = [
        full_service,
        scrape_website,
        handle_document_updates,
        sync_scrapy_to_solr,
        parse_content_to_plaintext,
        sync_documents,
        delete_documents_not_in_solr,
        score_documents,
        check_documents_unvalidated,
        update_documents_custom_id,
        extract_terms,
        extract_reporting_obligations,
        export_documents,
        delete_from_solr,
        reset_pre_analyzed_fields,
        export_all_user_data,
        test_concept_highlights_it,
    ]

    def count_documents(self, doc):
        return doc.documents.count()

    count_documents.short_description = "Documents"


def extract_terms_document(modeladmin, request, queryset):
    for document in queryset:
        tasks.extract_terms(document.website.id, str(document.id))


def extract_reporting_obligations_document(modeladmin, request, queryset):
    for document in queryset:
        tasks.extract_reporting_obligations(document.website.id, str(document.id))


def export_all_user_data_document(modeladmin, request, queryset):
    for document in queryset:
        tasks.export_all_user_data.delay(document.website.id, str(document.id))


def send_to_webanno(modeladmin, request, queryset):
    for document in queryset:
        send_document_to_webanno(str(document.id))


def reset_pre_analyzed_fields_document(modeladmin, request, queryset):
    for document in queryset:
        tasks.reset_pre_analyzed_fields_document(str(document.id))


class DocumentAdmin(admin.ModelAdmin):
    search_fields = ["id", "title", "celex"]
    list_filter = ("website__name", "date")
    actions = [
        extract_terms_document,
        extract_reporting_obligations_document,
        reset_pre_analyzed_fields_document,
        export_all_user_data_document,
    ]


class AcceptanceStateAdmin(admin.ModelAdmin):
    autocomplete_fields = ["document"]
    list_filter = ("user__username", "updated_at")
    list_display = ["id", "user", "value", "updated_at"]


class CommentAdmin(admin.ModelAdmin):
    autocomplete_fields = ["document"]
    list_filter = ("user__username", "updated_at")
    list_display = ["id", "user", "value", "updated_at"]


class TagAdmin(admin.ModelAdmin):
    autocomplete_fields = ["document"]


admin.site.register(Website, WebsiteAdmin)
admin.site.register(Document, DocumentAdmin)

admin.site.register(AcceptanceState, AcceptanceStateAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Tag, TagAdmin)
