import datetime
import logging as logger
import os
import time
import warnings
from datetime import datetime

import requests
from django.contrib.postgres.search import TrigramDistance
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from minio import Minio
from minio.error import NoSuchKey
from rest_framework import permissions, filters, status
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    RetrieveUpdateAPIView,
    ListAPIView,
)
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT
from rest_framework.views import APIView
from rest_framework_csv.renderers import CSVRenderer

from dblogging.models import DbQuery
from obligations.build_rdf import ROGraph
from obligations.models import (
    ReportingObligation,
    AcceptanceState,
    AcceptanceStateValue,
    Comment,
    Tag,
    ROAnnotationWorklog,
    ReportingObligationOffsets,
)
from obligations.rdf_parser import QUERY, URIS
from obligations.scripts.single_ro_view import get_single_ro_html_view_from_string
from obligations.serializers import (
    ROAnnotationWorklogSerializer,
    ReportingObligationOffsetsSerializer,
)
from obligations.serializers import (
    ReportingObligationSerializer,
    AcceptanceStateSerializer,
    CommentSerializer,
    TagSerializer,
)
from searchapp.models import Document, Website
from searchapp.permissions import IsOwner
from .rdf_call import (
    rdf_get_predicate,
    rdf_get_all_reporting_obligations,
    rdf_query_predicate_multiple_id,
    get_different_entity_types,
    get_filter_entities_from_type_lazy_loading,
)

# Annotation API consants

ANNOTATION_STORE_METADATA = '{"message": "Annotator Store API","links": {}}'
KWARGS_RO_ID_KEY = "ro_id"
KWARGS_DOCUMENT_ID_KEY = "document_id"
EXTRACT_RO_NLP_VERSION = os.environ.get("EXTRACT_RO_NLP_VERSION", "d16bba97890")
RDF_FUSEKI_QUERY_URL = os.environ.get("RDF_FUSEKI_QUERY_URL")


class PaginationHandlerMixin(object):
    @property
    def paginator(self):
        if not hasattr(self, "_paginator"):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        else:
            pass
        return self._paginator

    def paginate_queryset(self, queryset):
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)


class SmallResultsSetPagination(LimitOffsetPagination):
    default_limit = 5
    limit_query_param = "rows"
    offset_query_param = "page"


class MediumResultsSetPagination(LimitOffsetPagination):
    default_limit = 10
    limit_query_param = "rows"
    offset_query_param = "page"


# This one is used to fill the dropdowns in the UI
class ReportingObligationEntityMapAPIView(APIView):
    pagination_class = SmallResultsSetPagination
    queryset = ReportingObligation.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    # @method_decorator(cache_page(60 * 60 * 2))
    # @method_decorator(vary_on_cookie)
    def get(self, request, format=None):
        all_entities = get_different_entity_types()

        if all_entities:

            entities_sorted = []

            who = "hasReporter"
            must = "hasPropMod"
            report = "hasVerb"
            what = "hasReport"
            to_who = "hasRegulatoryBody"
            when = "hasPropTmp"

            def _pop_uri(substring):
                i_name = next(
                    (i for i, x in enumerate(all_entities) if substring.lower() in x.lower()),
                    None,
                )
                return all_entities.pop(i_name)

            # Remove "hasEntity" and DON'T add to entities_sorted
            _pop_uri("hasEntity")

            for name in who, must, report, what, to_who, when:
                entities_sorted.append(_pop_uri(name))

            entities_sorted += list(sorted(all_entities))

            return Response(entities_sorted)
        else:
            return Response("RDF has not been initialized yet. See technical documentation for more information", status=status.HTTP_406_NOT_ACCEPTABLE)


class ReportingObligationListAPIView(ListCreateAPIView):
    pagination_class = SmallResultsSetPagination
    queryset = ReportingObligation.objects.all()
    serializer_class = ReportingObligationSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["name"]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        groups = self.request.user.groups.all()
        opinion = any(group.name == "opinion" for group in groups)

        q = ReportingObligation.objects.all()
        keyword = self.request.GET.get("keyword", "")
        if keyword:
            q = q.filter(name__icontains=keyword)

        if opinion:
            rejected_state_ids = AcceptanceState.objects.filter(
                Q(user__groups__name="decision") & Q(value="Rejected")
            ).values_list("id", flat=True)
            q = q.exclude(Q(acceptance_states__in=list(rejected_state_ids)))
        return q.order_by("name")


class ReportingObligationSimilarListAPIView(ListAPIView):
    pagination_class = MediumResultsSetPagination
    queryset = ReportingObligation.objects.all()
    serializer_class = ReportingObligationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ro_id = request.data["ro_id"]

        ro = ReportingObligation.objects.get(pk=ro_id)
        q = (
            ReportingObligation.objects.annotate(distance=TrigramDistance("name", ro.name))
                .filter(distance__lte=0.6)
                .exclude(id=ro_id)
                .order_by("distance")
        )

        page = self.paginate_queryset(q)
        q_serialized = ReportingObligationSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(q_serialized.data)

    def get(self, request):
        return Response(ReportingObligation.objects.none())


"""
    This controller is used to load the autocomplete suggestions.
    POST args:
        uri_type: the URI of the entity
        keyword: keyword, case unsensitive
        list_pred_value:
"""


class ReportingObligationsFilterEntitiesLazy(APIView):
    queryset = ReportingObligation.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(60 * 60 * 2))
    @method_decorator(vary_on_cookie)
    def post(self, request, format=None, *args, **kwargs):
        uri_type_has = request.data["uri_type"]
        keyword = request.data["keyword"]

        dict_rdf_filters = request.data["rdfFilters"]

        if uri_type_has in dict_rdf_filters:
            dict_rdf_filters.pop(
                uri_type_has
            )  # Dropdown item filter should only look at the other filters and ignore this filter.
        list_pred_value = dict_rdf_filters.items()

        q = ReportingObligation.objects.filter(version=EXTRACT_RO_NLP_VERSION)
        documents_with_ros = q.values("document_occurs__id")
        from_bookmarked_filter = self.request.GET.get("fromBookmarked", "")

        def get_website_url():
            website_filter = self.request.GET.get("website", None)
            if website_filter:
                website_url = Website.objects.get(name__iexact=website_filter).url
                return website_url
            else:
                return None

        website_url = get_website_url()

        l_doc_uri = get_l_doc_uri(documents_with_ros=documents_with_ros,
                          from_bookmarked_filter=from_bookmarked_filter,
                          username= self.request.user.username
                          )

        results = get_filter_entities_from_type_lazy_loading(
            uri_type_has,
            str_match=keyword,
            list_pred_value=list_pred_value,
            l_doc_uri=l_doc_uri,
            doc_src = website_url,
            exact_match=False,
            limit=100,
        )

        d_results = [{"name": a} for a in results]

        return Response(d_results)


# Query for RO+RDF ROS search
class ReportingObligationListRdfQueriesAPIView(APIView, PaginationHandlerMixin):
    pagination_class = SmallResultsSetPagination
    queryset = ReportingObligation.objects.all()
    serializer_class = ReportingObligationSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["name"]
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(60 * 60 * 2))
    @method_decorator(vary_on_cookie)
    def post(self, request, format=None, *args, b_debug=False, **kwargs):
        request.data["user"] = request.user.id

        from_bookmarked_filter = self.request.GET.get("fromBookmarked", "")
        filtertype = self.request.GET.get("filterType", "")
        otherUser = self.request.GET.get("otherUser", "")
        groups = self.request.user.groups.all()
        opinion = any(group.name == "opinion" for group in groups)

        if b_debug:
            t1 = time.time()

        q = ReportingObligation.objects.filter(version=EXTRACT_RO_NLP_VERSION)

        if b_debug:
            print("q1", len(q))

        documents_with_ros = q.values("document_occurs__id")
        rdf_filters = request.data["rdfFilters"]

        if b_debug:
            t2 = time.time()
            print("t2-t1: ", t2-t1)
            logger.info("rdf_filters: %s", rdf_filters)

        l_doc_uri = get_l_doc_uri(documents_with_ros=documents_with_ros,
                          from_bookmarked_filter=from_bookmarked_filter,
                          username= self.request.user.username
                          )

        if b_debug:
            t3 = time.time()
            print("t3-t2: ", t3 - t2)

        def get_website_url():
            website_filter = self.request.GET.get("website", None)
            if website_filter:
                website_url = Website.objects.get(name__iexact=website_filter).url
                return website_url
            else:
                return None

        website_url = get_website_url()

        if b_debug:
            t4 = time.time()
            print("t4-t3: ", t4 - t3)

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

        if b_debug:
            t5 = time.time()
            print("t5-t4: ", t5 - t4)

        sparql_q = "No SPARQL query"
        if rdf_filters or website_url or otherUser or filtertype or from_bookmarked_filter:
            rdf_results = rdf_query_predicate_multiple_id(
                rdf_filters.items(),
                l_doc_uri=l_doc_uri,
                doc_src=website_url,
                limit=None,
                offset=0,
                exact_match=False,
            )

            if b_debug:
                t6 = time.time()
                print("t6-t5: ", t6 - t5)

            sparql_q = rdf_results[QUERY]
            ro_uris = rdf_results[URIS]

            if ro_uris:
                q = q.filter(rdf_id__in=ro_uris)
                if b_debug:
                    print("ro_uris, ", bool(q))
                if opinion:
                    rejected_state_ids = AcceptanceState.objects.filter(
                        Q(user__groups__name="decision") & Q(value="Rejected")
                    ).values_list("id", flat=True)
                    q = q.exclude(Q(acceptance_states__in=list(rejected_state_ids)))

                if b_debug:
                    logger.info(q)
                    logger.info(len(q))
                    t7 = time.time()
                    print("t7-t6: ", t7 - t6)

            else:
                q = ReportingObligation.objects.none()

        else:
            q = ReportingObligation.objects.all()

        if b_debug:
            t8 = time.time()
        export_csv = self.request.GET.get("exportCsv", "")
        if export_csv:
            q_serialized = self.serializer_class(q, many=True, context={"request": request})
            response = Response(data=q_serialized.data)
            response.accepted_renderer = CSVRenderer()
            response.accepted_media_type = "text/csv"
            response.renderer_context = {"request": request}
            return Response(response.rendered_content)
        else:
            page = self.paginate_queryset(q)

            if b_debug:
                t9 = time.time()
                print("t9-t8", t9-t8)

            serializer = self.get_paginated_response(
                self.serializer_class(page, many=True, context={"request": request}).data
            )
            if b_debug:
                t10 = time.time()
                print("t10-t9", t10 - t9)

            # Add query to the logging database
            show_db_queries = self.request.GET.get("showDbQueries", "")

            if show_db_queries == "true":
                # Need to cast to str otherwise some dramatic things happen (q.query is django.db.models.sql.query.Query)
                DbQuery.objects.create(
                    query=str(q.query),
                    rdf_query=str(sparql_q),
                    user=self.request.user,
                    app="obligations",
                )

            return Response(serializer.data)


class ReportingObligationDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ReportingObligation.objects.all()
    serializer_class = ReportingObligationSerializer
    permission_classes = [permissions.IsAuthenticated]


# Predicate
class ReportingObligationGetByPredicate(APIView):
    queryset = ReportingObligation.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        predicate = request.data["predicate"]
        result = rdf_get_predicate(predicate)
        return Response(result)


# Get all RO's from RDF
class ReportingObligationsRDFListAPIView(APIView):
    queryset = ReportingObligation.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        result = rdf_get_all_reporting_obligations()
        return Response(result)


class TagListAPIView(ListCreateAPIView):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    permission_classes = [permissions.IsAuthenticated]


class TagDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    permission_classes = [permissions.IsAuthenticated]


class AcceptanceStateValueAPIView(APIView):
    queryset = AcceptanceState.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        return Response([state.value for state in AcceptanceStateValue])


class AcceptanceStateListAPIView(ListCreateAPIView):
    serializer_class = AcceptanceStateSerializer
    queryset = AcceptanceState.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = AcceptanceState.objects.filter(user=request.user)
        serializer = AcceptanceStateSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        request.data["user"] = request.user.id
        ro = ReportingObligation.objects.get(pk=request.data["reporting_obligation"])
        AcceptanceState.objects.update_or_create(
            reporting_obligation=ro,
            user=request.user,
            defaults={"value": request.data["value"]},
        )
        return Response("ok")


class AcceptanceStateDetailAPIView(RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    serializer_class = AcceptanceStateSerializer
    queryset = AcceptanceState.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, *args, **kwargs):
        request.data["user"] = request.user.id
        return self.update(request, *args, **kwargs)


class CommentListAPIView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, *args, **kwargs):
        request.data["user"] = request.user.id
        return self.update(request, *args, **kwargs)


class RoAnnotationRootAPIView(APIView):
    queryset = ROAnnotationWorklog.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, subject_id, document_id, format=None):
        return Response(ANNOTATION_STORE_METADATA)


class RoAnnotationSearchListAPIView(ListCreateAPIView):
    queryset = ROAnnotationWorklog.objects.none()
    serializer_class = ROAnnotationWorklogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        annotation_worklogs = ROAnnotationWorklog.objects.filter(
            ro_offsets__ro__id=self.kwargs[KWARGS_RO_ID_KEY]
        ).filter(ro_offsets__document__id=self.kwargs[KWARGS_DOCUMENT_ID_KEY])
        serializer = ROAnnotationWorklogSerializer(annotation_worklogs, many=True)
        rows = []
        for data_item in serializer.data:
            ro_offsets = ReportingObligationOffsets.objects.get(pk=data_item["ro_offsets"])
            if ro_offsets:
                row = {
                    "id": str(data_item["id"]),
                    "quote": ro_offsets.quote,
                    "ranges": [],
                }

                ranges_dict = {
                    "start": str(ro_offsets.start),
                    "startOffset": ro_offsets.startOffset,
                    "end": str(ro_offsets.end),
                    "endOffset": ro_offsets.endOffset,
                }

                row["ranges"].append(ranges_dict)
                row["text"] = ""
                rows.append(row)

        response = {"total": str(len(rows)), "rows": rows}
        return Response(response)


class RoAnnotationCreateListAPIView(ListCreateAPIView):
    queryset = ROAnnotationWorklog.objects.none()
    serializer_class = ROAnnotationWorklogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        ro_offsets_data = request.data
        ro_offsets_data.update({"ro": str(self.kwargs[KWARGS_RO_ID_KEY])})
        ro_offsets_data.update({"document": str(self.kwargs[KWARGS_DOCUMENT_ID_KEY])})
        ro_offsets_data.update({"quote": str(request.data["quote"]).replace('"', '\\"')})
        ro_offsets_data.update({"probability": 1.0})
        ro_offsets_data.update({"start": request.data["ranges"][0]["start"]})
        ro_offsets_data.update({"startOffset": request.data["ranges"][0]["startOffset"]})
        ro_offsets_data.update({"end": request.data["ranges"][0]["end"]})
        ro_offsets_data.update({"endOffset": request.data["ranges"][0]["endOffset"]})

        annotation_worklog_data = request.data
        annotation_worklog_data.update({"user": request.user.id})
        annotation_worklog_data.update({"created_at": datetime.datetime.now()})
        annotation_worklog_data.update({"updated_at": datetime.datetime.now()})

        ro_offsets_serializer = ReportingObligationOffsetsSerializer(data=ro_offsets_data)
        if ro_offsets_serializer.is_valid():
            ro_offsets = ro_offsets_serializer.save()
            annotation_worklog_data.update({"ro_offsets": ro_offsets.id})
        else:
            return Response(ro_offsets_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        annotation_worklog_serializer = ROAnnotationWorklogSerializer(data=annotation_worklog_data)
        if annotation_worklog_serializer.is_valid():
            annotation_worklog = annotation_worklog_serializer.save()
            annotation_worklog_serializer = ROAnnotationWorklogSerializer(annotation_worklog)
            response_data = {
                "id": annotation_worklog_serializer.data["id"],
                "quote": request.data["quote"],
                "text": "",
                "ranges": request.data["ranges"],
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(annotation_worklog_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoAnnotationDeleteAPIView(APIView):
    queryset = ROAnnotationWorklog.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, ro_id, document_id, annotation_id, format=None):
        annotation_worklog = ROAnnotationWorklog.objects.get(id=annotation_id)
        ro_offsets = annotation_worklog.ro_offsets
        if ro_offsets:
            ro_offsets.delete()
        annotation_worklog.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportingObligationDocumentHtmlAPIView(APIView):
    queryset = ReportingObligation.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, document_id, format=None):
        minio_client = Minio(
            os.environ["MINIO_STORAGE_ENDPOINT"],
            access_key=os.environ["MINIO_ACCESS_KEY"],
            secret_key=os.environ["MINIO_SECRET_KEY"],
            secure=False,
        )
        bucket_name = "ro-html-output"

        try:
            html_file = minio_client.get_object(bucket_name, document_id + "-" + EXTRACT_RO_NLP_VERSION + ".html")
            result = html_file.data

            return Response(result, HTTP_200_OK)
        except NoSuchKey as err:
            return Response("", HTTP_204_NO_CONTENT)


class ReportingObligationSingleROHtmlAPIView(APIView):
    queryset = ReportingObligation.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        minio_client = Minio(
            os.environ["MINIO_STORAGE_ENDPOINT"],
            access_key=os.environ["MINIO_ACCESS_KEY"],
            secret_key=os.environ["MINIO_SECRET_KEY"],
            secure=False,
        )
        bucket_name = "ro-html-output"

        ro_str = request.data["ro"]
        doc_id = request.data["doc_id"]

        try:
            html_file = minio_client.get_object(bucket_name, doc_id + "-" + EXTRACT_RO_NLP_VERSION + ".html")
            html_str = html_file.data
            result = get_single_ro_html_view_from_string(html_str, ro_str).decode(encoding="utf-8")

            return Response(result, HTTP_200_OK)
        except NoSuchKey as err:
            return Response("", HTTP_204_NO_CONTENT)


class FusekiDatasetAPIView(APIView):
    queryset = ReportingObligation.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        req_data = {"query": request.data["query"]}

        r = requests.post(RDF_FUSEKI_QUERY_URL, data=req_data)
        return Response(r.content)


def get_l_doc_uri(documents_with_ros=None,
                  website_filter=None,
                  from_bookmarked_filter=None,
                  username=None  # self.request.user.username, Needed when using *from_bookmarked_filter*
                  ):
    """
    Check if needs to be filtered on the document ID

    Returns
        l_doc_uri: list with RDF uri's for the documents.
    """

    if website_filter:
        warnings.warn('websites can now be filtered through the RDF directly', DeprecationWarning)

    if website_filter or from_bookmarked_filter:
        relevant_documents = Document.objects.filter(id__in=documents_with_ros)

        if website_filter:
            relevant_documents = relevant_documents.filter(website__name__iexact=website_filter)

        if from_bookmarked_filter:
            relevant_documents = relevant_documents.filter(
                bookmarks__user__username=username)

        relevant_documents_ids = list(
            map(
                lambda x: str(x.get("id")),
                relevant_documents.values("id"),
            )
        )
        l_doc_uri = list(map(ROGraph._get_cat_doc_uri, relevant_documents_ids))

    else:
        # Attention!
        # Make sure l_doc_uri is None if there is no need to filter on a document level
        # else the query will get too long and heavy!
        l_doc_uri = None

    return l_doc_uri
