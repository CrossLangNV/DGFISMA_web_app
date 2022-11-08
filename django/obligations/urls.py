from django.urls import path

import os

from django.urls import path, re_path, include

from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from rest_framework import permissions
from obligations import views

schema_view = get_schema_view(
    openapi.Info(
        title="Reporting Obligations API",
        default_version="v1",
        description="Documentation for REST API",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="nobody@crosslang.com"),
        license=openapi.License(name="BSD License"),
    ),
    url=os.environ["DJANGO_BASE_URL"],
    patterns=[path("obligations/", include(("obligations.urls", "obligations"), namespace="obligations"))],
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # API
    # Swagger drf-yasg
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    # Reporting Obligations
    path("api/ros", views.ReportingObligationListAPIView.as_view(), name="ro_api_list"),
    path("api/ros/similar", views.ReportingObligationSimilarListAPIView.as_view(), name="ro_api_similar_list"),
    path("api/ro/<int:pk>", views.ReportingObligationDetailAPIView.as_view(), name="ro_api_detail"),
    # State
    path("api/states", views.AcceptanceStateListAPIView.as_view(), name="state_list_api"),
    path("api/state/<int:pk>", views.AcceptanceStateDetailAPIView.as_view(), name="state_detail_api"),
    path("api/state/value", views.AcceptanceStateValueAPIView.as_view(), name="state_value_api"),
    # Comment
    path("api/comments", views.CommentListAPIView.as_view(), name="comment_list_api"),
    path("api/comment/<int:pk>", views.CommentDetailAPIView.as_view(), name="comment_detail_api"),
    # Tag
    path("api/tags", views.TagListAPIView.as_view(), name="tag_list_api"),
    path("api/tag/<int:pk>", views.TagDetailAPIView.as_view(), name="tag_detail_api"),
    # Get all items from this entity
    path("api/ros/predicate", views.ReportingObligationGetByPredicate.as_view(), name="ro_find_by_predicate"),
    # Replace the other one later
    path("api/rdf_ros", views.ReportingObligationListRdfQueriesAPIView.as_view(), name="ro_rdf_api_list"),
    # All entities of RDF + their options
    path("api/ros/entity_map", views.ReportingObligationEntityMapAPIView.as_view(), name="ro_rdf_entity_map"),
    ### RO Annotations API
    # API root
    path("api/annotations/ro/<str:ro_id>/<str:document_id>", views.RoAnnotationRootAPIView.as_view(), name="api_root"),
    # Search
    path(
        "api/annotations/ro/<str:ro_id>/<str:document_id>/search",
        views.RoAnnotationSearchListAPIView.as_view(),
        name="api_search",
    ),
    # Create
    path(
        "api/annotations/ro/<str:ro_id>/<str:document_id>/annotations",
        views.RoAnnotationCreateListAPIView.as_view(),
        name="api_create",
    ),
    # Delete
    path(
        "api/annotations/ro/<str:ro_id>/<str:document_id>/annotations/<str:annotation_id>",
        views.RoAnnotationDeleteAPIView.as_view(),
        name="api_delete",
    ),
    # Get HTML output from reporting obligation extraction
    path(
        "api/ros/document/<document_id>",
        views.ReportingObligationDocumentHtmlAPIView.as_view(),
        name="ro_document_html_api_detail",
    ),
    # Get Reporting Obligation filters
    path(
        "api/ros/rdf_entities_lazy",
        views.ReportingObligationsFilterEntitiesLazy.as_view(),
        name="ro_rdf_entities_lazy",
    ),
    # Get a single RO html view
    path(
        "api/ros/ro_html_view",
        views.ReportingObligationSingleROHtmlAPIView.as_view(),
        name="ro_html_api_detail",
    ),
    path("api/dataset", views.FusekiDatasetAPIView.as_view(), name="fuseki_dataset_api"),
]
