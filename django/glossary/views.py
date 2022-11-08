from datetime import datetime
import os
import logging

from django.db.models import Q
from rest_framework import permissions, filters, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, RetrieveUpdateAPIView, ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.settings import api_settings
from rest_framework_csv.renderers import CSVRenderer


from dblogging.models import DbQuery
from glossary.models import (
    AcceptanceState,
    AcceptanceStateValue,
    Comment,
    Concept,
    Tag,
    AnnotationWorklog,
    ConceptOccurs,
    ConceptDefined,
    Lemma,
)
from glossary.serializers import (
    AcceptanceStateSerializer,
    ConceptSerializer,
    TagSerializer,
    LemmaSerializer,
    AnnotationWorklogSerializer,
    ConceptOccursSerializer,
    ConceptDefinedSerializer,
    CommentSerializer,
)
from scheduler.extract import send_document_to_webanno
from searchapp.models import Document, Bookmark
from searchapp.permissions import IsOwner

logger = logging.getLogger(__name__)

# Annotation API consants

ANNOTATION_STORE_METADATA = '{"message": "Annotator Store API","links": {}}'
KWARGS_ANNOTATION_TYPE_KEY = "annotation_type"
KWARGS_ANNOTATION_TYPE_VALUE_OCCURENCE = "occurence"
KWARGS_ANNOTATION_TYPE_VALUE_DEFINITION = "definition"
KWARGS_CONCEPT_ID_KEY = "concept_id"
KWARGS_DOCUMENT_ID_KEY = "document_id"
EXTRACT_TERMS_NLP_VERSION = os.environ.get("EXTRACT_TERMS_NLP_VERSION", "8a4f1d58")


class SmallResultsSetPagination(LimitOffsetPagination):
    default_limit = 5
    limit_query_param = "rows"
    offset_query_param = "page"


class ConceptListAPIView(ListCreateAPIView):
    pagination_class = SmallResultsSetPagination
    queryset = Concept.objects.all()
    serializer_class = ConceptSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["name", "acceptance_state_max_probability"]
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)

    def get_queryset(self):
        groups = self.request.user.groups.all()
        opinion = any(group.name == "opinion" for group in groups)

        # TODO Remove the Unknown term and empty definition exclude filter
        q = Concept.objects.all().exclude(name__exact="Unknown").exclude(definition__exact="")
        keyword = self.request.GET.get("keyword", "")
        if keyword:
            q = q.filter(name__icontains=keyword)

        if opinion:
            rejected_state_ids = AcceptanceState.objects.filter(
                Q(user__groups__name="decision") & Q(value="Rejected")
            ).values_list("id", flat=True)
            q = q.exclude(Q(acceptance_states__in=list(rejected_state_ids)))

        showonlyown = self.request.GET.get("showOnlyOwn", "")
        if showonlyown == "true":
            q = q.filter(
                Q(acceptance_states__user__username=self.request.user.username)
                & (Q(acceptance_states__value="Accepted") | Q(acceptance_states__value="Rejected"))
            )

        tag = self.request.GET.get("tag", "")
        if tag:
            q = q.filter(tags__value=tag)

        q = q.filter(version=EXTRACT_TERMS_NLP_VERSION)

        website = self.request.GET.get("website", "")
        if len(website):
            q = q.filter(website__name__iexact=website)

        filtertype = self.request.GET.get("filterType", "")
        otherUser = self.request.GET.get("otherUser", "")
        if otherUser and filtertype == "":
            if otherUser == "auto-classifier":
                q = q.filter(acceptance_states__user=None)
            else:
                q = q.filter(acceptance_states__user__username=otherUser)

        if filtertype and otherUser == "":
            if filtertype == "unvalidated":
                q = q.filter(acceptance_states__value="Unvalidated")
            else:
                q = q.filter(acceptance_states__value=filtertype.capitalize()).distinct()

        if otherUser and filtertype:

            if filtertype == "unvalidated":
                if otherUser == "auto-classifier":
                    q = q.filter(
                        acceptance_states__value="Unvalidated",
                        acceptance_states__user=None,
                    )
                else:
                    q = q.filter(
                        acceptance_states__value="Unvalidated",
                        acceptance_states__user__username=otherUser,
                    )
            else:
                if otherUser == "auto-classifier":
                    q = q.filter(
                        acceptance_states__value=filtertype.capitalize(),
                        acceptance_states__user=None,
                    ).distinct()
                else:
                    q = q.filter(
                        acceptance_states__value=filtertype.capitalize(),
                        acceptance_states__user__username=otherUser,
                    ).distinct()

        showbookmarked = self.request.GET.get("showBookmarked", "")
        if showbookmarked == "true":
            bookmarks = Bookmark.objects.filter(user__username=self.request.user.username)
            bookmarked_documents = Document.objects.filter(bookmarks__in=bookmarks)
            q = q.filter(document_defined__in=bookmarked_documents) | q.filter(
                document_occurs__in=bookmarked_documents
            )

        # Add query to the logging database
        show_db_queries = self.request.GET.get("showDbQueries", "")
        if show_db_queries == "true":
            DbQuery.objects.create(query=str(q.query), rdf_query="", user=self.request.user, app="glossary")

        return q.order_by("name")

    def list(self, request, *args, **kwargs):
        export_csv = self.request.GET.get("exportCsv", "")
        q = self.get_queryset()
        if export_csv:
            q_serialized = ConceptSerializer(q, many=True, context={"request": request})
            response = Response(data=q_serialized.data)
            response.accepted_renderer = CSVRenderer()
            response.accepted_media_type = "text/csv"
            response.renderer_context = {"request": request}
            return Response(response.rendered_content)
        else:
            page = self.paginate_queryset(q)
            q_serialized = ConceptSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(q_serialized.data)


class LemmaListAPIView(ListCreateAPIView):
    pagination_class = SmallResultsSetPagination
    queryset = Concept.objects.all()
    serializer_class = LemmaSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["name"]

    def get_queryset(self):
        concept_ids = ConceptListAPIView.get_queryset(self).values_list("id", flat=True)
        return Lemma.objects.filter(concepts__id__in=concept_ids).order_by("name").distinct("name")


class ConceptDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Concept.objects.all()
    serializer_class = ConceptSerializer


class TagListAPIView(ListCreateAPIView):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()


class TagDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()


class WorkLogAPIView(ListCreateAPIView):
    serializer_class = AnnotationWorklogSerializer
    queryset = AnnotationWorklog.objects.all()


class WorklogDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = AnnotationWorklogSerializer
    queryset = AnnotationWorklog.objects.all()


class AcceptanceStateValueAPIView(APIView):
    queryset = AcceptanceState.objects.none()

    def get(self, request, format=None):
        return Response([state.value for state in AcceptanceStateValue])


class AcceptanceStateListAPIView(ListCreateAPIView):
    serializer_class = AcceptanceStateSerializer
    queryset = AcceptanceState.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = AcceptanceState.objects.filter(user=request.user)
        serializer = AcceptanceStateSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        request.data["user"] = request.user.id
        concept = Concept.objects.get(pk=request.data["concept"])
        AcceptanceState.objects.update_or_create(
            concept=concept,
            user=request.user,
            defaults={"value": request.data["value"]},
        )
        return Response("ok")


class AcceptanceStateDetailAPIView(RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    serializer_class = AcceptanceStateSerializer
    queryset = AcceptanceState.objects.all()

    def put(self, request, *args, **kwargs):
        request.data["user"] = request.user.id
        return self.update(request, *args, **kwargs)


class CommentListAPIView(ListCreateAPIView):
    serializer_class = CommentSerializer
    queryset = Comment.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = Comment.objects.filter(user=request.user)
        serializer = CommentSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        request.data["user"] = request.user.id
        return self.create(request, *args, **kwargs)


class CommentDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    queryset = Comment.objects.all()

    def put(self, request, *args, **kwargs):
        request.data["user"] = request.user.id
        return self.update(request, *args, **kwargs)


class ConceptDistinctVersions(APIView):
    queryset = Concept.objects.none()

    def get(self, request):
        q = set(Concept.objects.values_list("version", flat=True))
        return Response(q)


class WebAnnoLink(APIView):
    queryset = Document.objects.none()

    def get(self, request, document_id):
        doc = Document.objects.get(pk=document_id)
        if doc.webanno_document_id is None:
            webanno_doc = send_document_to_webanno(document_id)
            if webanno_doc is None:
                doc.webanno_document_id = None
                doc.webanno_project_id = None
                doc.save()
                return Response("404")

            doc.webanno_document_id = webanno_doc.document_id
            doc.webanno_project_id = webanno_doc.project_id
            doc.save()

        return Response(
            os.environ["WEBANNO_URL"]
            + "/annotation.html?50#!p="
            + str(doc.webanno_project_id)
            + "&d="
            + str(doc.webanno_document_id)
            + "&f=1"
        )


# Terms and Definitions Annotations API
class ConceptAnnotationRootAPIView(APIView):
    queryset = AnnotationWorklog.objects.none()

    def get(self, request, annotation_type, concept_id, document_id, format=None):
        return Response(ANNOTATION_STORE_METADATA)


class ConceptAnnotationSearchListAPIView(ListCreateAPIView):
    serializer_class = AnnotationWorklogSerializer
    queryset = AnnotationWorklog.objects.all()

    def list(self, request, *args, **kwargs):
        annotation_worklogs = None
        if self.kwargs[KWARGS_ANNOTATION_TYPE_KEY] == KWARGS_ANNOTATION_TYPE_VALUE_OCCURENCE:
            annotation_worklogs = AnnotationWorklog.objects.filter(
                concept_occurs__concept__id=self.kwargs[KWARGS_CONCEPT_ID_KEY]
            ).filter(concept_occurs__document__id=self.kwargs[KWARGS_DOCUMENT_ID_KEY])
        elif self.kwargs[KWARGS_ANNOTATION_TYPE_KEY] == KWARGS_ANNOTATION_TYPE_VALUE_DEFINITION:
            annotation_worklogs = AnnotationWorklog.objects.filter(
                concept_defined__concept__id=self.kwargs[KWARGS_CONCEPT_ID_KEY]
            ).filter(concept_defined__document__id=self.kwargs[KWARGS_DOCUMENT_ID_KEY])
        serializer = AnnotationWorklogSerializer(annotation_worklogs, many=True)
        rows = []
        for data_item in serializer.data:
            concept_offset_base = None
            if data_item["concept_occurs"]:
                concept_offset_base = ConceptOccurs.objects.get(pk=data_item["concept_occurs"])
            elif data_item["concept_defined"]:
                concept_offset_base = ConceptDefined.objects.get(pk=data_item["concept_defined"])
            if concept_offset_base:
                row = {
                    "id": str(data_item["id"]),
                    "quote": concept_offset_base.quote,
                    "ranges": [],
                }
                ranges_dict = {
                    "start": str(concept_offset_base.start),
                    "startOffset": concept_offset_base.startOffset,
                    "end": str(concept_offset_base.end),
                    "endOffset": concept_offset_base.endOffset,
                }
                row["ranges"].append(ranges_dict)
                row["text"] = ""
                rows.append(row)

        response = {"total": str(len(rows)), "rows": rows}
        return Response(response)


class ConceptAnnotationCreateListAPIView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AnnotationWorklogSerializer
    queryset = AnnotationWorklog.objects.all()

    def post(self, request, *args, **kwargs):
        concept_offset_data = request.data
        concept_offset_data.update({"concept": str(self.kwargs["concept_id"])})
        concept_offset_data.update({"document": str(self.kwargs["document_id"])})
        concept_offset_data.update({"quote": str(request.data["quote"]).replace('"', '\\"')})
        concept_offset_data.update({"probability": 1.0})
        concept_offset_data.update({"start": request.data["ranges"][0]["start"]})
        concept_offset_data.update({"startOffset": request.data["ranges"][0]["startOffset"]})
        concept_offset_data.update({"end": request.data["ranges"][0]["end"]})
        concept_offset_data.update({"endOffset": request.data["ranges"][0]["endOffset"]})

        annotation_worklog_data = request.data
        annotation_worklog_data.update({"user": request.user.id})
        annotation_worklog_data.update({"created_at": datetime.datetime.now()})
        annotation_worklog_data.update({"updated_at": datetime.datetime.now()})
        annotation_worklog_data.update({"document": str(self.kwargs["document_id"])})

        concept_occurs = None
        concept_defined = None
        if self.kwargs[KWARGS_ANNOTATION_TYPE_KEY] == KWARGS_ANNOTATION_TYPE_VALUE_OCCURENCE:
            concept_occurs_serializer = ConceptOccursSerializer(data=concept_offset_data)
            if concept_occurs_serializer.is_valid():
                concept_occurs = concept_occurs_serializer.save()
                annotation_worklog_data.update({"concept_occurs": concept_occurs.id})
                annotation_worklog_data.update({"concept_defined": None})
            else:
                return Response(concept_occurs_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif self.kwargs[KWARGS_ANNOTATION_TYPE_KEY] == KWARGS_ANNOTATION_TYPE_VALUE_DEFINITION:
            concept_defined_serializer = ConceptDefinedSerializer(data=concept_offset_data)
            if concept_defined_serializer.is_valid():
                concept_defined = concept_defined_serializer.save()
                annotation_worklog_data.update({"concept_occurs": None})
                annotation_worklog_data.update({"concept_defined": concept_defined.id})
            else:
                return Response(
                    concept_defined_serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                )
        annotation_worklog_serializer = AnnotationWorklogSerializer(data=annotation_worklog_data)
        if annotation_worklog_serializer.is_valid():
            annotation_worklog = annotation_worklog_serializer.save()
            annotation_worklog_serializer = AnnotationWorklogSerializer(annotation_worklog)
            response_data = {
                "id": annotation_worklog_serializer.data["id"],
                "quote": request.data["quote"],
                "text": "",
                "ranges": request.data["ranges"],
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(annotation_worklog_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConceptAnnotationDeleteAPIView(APIView):
    queryset = AnnotationWorklog.objects.none()

    def delete(
        self,
        request,
        annotation_type,
        concept_id,
        document_id,
        annotation_id,
        format=None,
    ):
        annotation_worklog = AnnotationWorklog.objects.get(id=annotation_id)
        concept_occurs = annotation_worklog.concept_occurs
        if concept_occurs:
            concept_occurs.delete()
        concept_defined = annotation_worklog.concept_defined
        if concept_defined:
            concept_defined.delete()
        annotation_worklog.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConceptOccursForConceptAPIView(ListCreateAPIView):
    queryset = ConceptOccurs.objects.all()
    serializer_class = ConceptOccursSerializer
    pagination_class = SmallResultsSetPagination

    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        q = ConceptOccurs.objects.all()

        concept_param = self.request.GET.get("concept", "")
        concept = Concept.objects.get(pk=concept_param)

        q = ConceptOccurs.objects.filter(concept__name=concept.name).distinct("document")

        return q
