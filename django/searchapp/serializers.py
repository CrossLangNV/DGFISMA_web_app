from django.contrib.auth.models import User, Group
from rest_framework import serializers

from obligations.models import RoDocumentSerializer
from searchapp.datahandling import enrich_with_annotations
from searchapp.models import Attachment, Document, Website, AcceptanceState, Comment, Tag, Bookmark
from glossary.serializers import ConceptDocumentSerializer

import logging
import os

logger = logging.getLogger(__name__)
EXTRACT_TERMS_NLP_VERSION = os.environ.get("EXTRACT_TERMS_NLP_VERSION", "8a4f1d58")
EXTRACT_RO_NLP_VERSION = os.environ.get("EXTRACT_RO_NLP_VERSION")


class WebsiteSerializer(serializers.ModelSerializer):
    total_documents = serializers.IntegerField(read_only=True)

    class Meta:
        model = Website
        fields = "__all__"


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["name"]


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)

    class Meta:
        model = User
        exclude = ["password"]


class AcceptanceStateSerializer(serializers.ModelSerializer):
    document = serializers.PrimaryKeyRelatedField(queryset=Document.objects.all())
    user = UserSerializer(read_only=True)

    class Meta:
        model = AcceptanceState
        fields = "__all__"


class AttachmentWithoutContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        exclude = ["content", "file"]


class DocumentSerializer(serializers.ModelSerializer):
    website = serializers.PrimaryKeyRelatedField(queryset=Website.objects.all())
    website_name = serializers.SerializerMethodField()
    attachments = AttachmentWithoutContentSerializer(many=True, read_only=True)
    comments = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    acceptance_states = AcceptanceStateSerializer(many=True, read_only=True)
    acceptance_states_count = serializers.SerializerMethodField()
    acceptance_state = serializers.SerializerMethodField()
    acceptance_state_value = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    content_annotated = serializers.SerializerMethodField()
    bookmark = serializers.SerializerMethodField()
    definition = serializers.SerializerMethodField()
    ro_occurrance = serializers.SerializerMethodField()

    def get_definition(self, document):
        qs = document.definition.filter(version=EXTRACT_TERMS_NLP_VERSION)
        serializer = ConceptDocumentSerializer(instance=qs, many=True, read_only=True)
        return serializer.data

    def get_ro_occurrance(self, document):
        qs = document.ro_occurrance.filter(version=EXTRACT_RO_NLP_VERSION)
        serializer = RoDocumentSerializer(instance=qs, many=True, read_only=True)
        return serializer.data

    def get_content(self, document):
        try:
            return document.content.strip()
        except AttributeError:
            return ""

    def get_content_annotated(self, document):
        try:
            # only load when with_content requested.
            if document.content:
                return enrich_with_annotations(document).strip()
        except AttributeError:
            return ""

    def get_bookmark(self, document):
        user = self.context["request"].user
        if len(document.bookmarks.filter(user=user)) > 0:
            return True
        else:
            return False

    def get_acceptance_states_count(self, document):
        q = AcceptanceState.objects.filter(document=document)
        qs1 = q.filter(value="Accepted", user__isnull=False)
        qs2 = q.filter(value="Rejected", user__isnull=False)
        qs3 = q.filter(value="Unvalidated", user__isnull=False)
        qs4 = q.filter(user=None).distinct("value")

        count_values = [qs1, qs2, qs3]
        result = []

        for cvalue in count_values:
            if cvalue.count() > 0:
                result.append(
                    {"value": f"{cvalue[0].value} ({str(cvalue.count())})", "style": str(cvalue[0].value).lower()}
                )

        for acs in qs4:
            result.append({"value": "Auto-classifier", "style": acs.value.lower()})
        return result

    def get_acceptance_state(self, document):
        user = self.context["request"].user
        qs = AcceptanceState.objects.filter(document=document, user=user)
        serializer = AcceptanceStateSerializer(instance=qs, many=True)
        state_id = None
        if len(serializer.data) > 0:
            state_id = serializer.data[0]["id"]

        return state_id

    def get_acceptance_state_value(self, document):
        user = self.context["request"].user
        qs = AcceptanceState.objects.filter(document=document, user=user)
        res = qs.values_list("value", flat=True)
        if len(res):
            return res[0]
        else:
            return "Unvalidated"

    def get_website_name(self, document):
        return document.website.name

    class Meta:
        model = Document
        fields = "__all__"


class AttachmentSerializer(serializers.ModelSerializer):
    document = serializers.PrimaryKeyRelatedField(queryset=Document.objects.all())

    class Meta:
        model = Attachment
        fields = "__all__"


class CommentSerializer(serializers.ModelSerializer):
    document = serializers.PrimaryKeyRelatedField(queryset=Document.objects.all())
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    username = serializers.SerializerMethodField("get_username")

    class Meta:
        model = Comment
        fields = ["id", "value", "document", "user", "created_at", "username"]

    def get_username(self, comment):
        return comment.user.username


class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ["document"]
