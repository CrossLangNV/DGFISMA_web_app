import os

from django.urls import path, re_path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from glossary import views

schema_view = get_schema_view(
    openapi.Info(
        title="Glossary of Concepts API",
        default_version="v1",
        description="Documentation for REST API",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="nobody@crosslang.com"),
        license=openapi.License(name="BSD License"),
    ),
    url=os.environ["DJANGO_BASE_URL"],
    patterns=[path("glossary/", include(("glossary.urls", "glossary"), namespace="glossary"))],
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # API
    # Swagger drf-yasg
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    # Concept
    path("api/concepts", views.ConceptListAPIView.as_view(), name="concept_api_list"),
    path("api/lemmas", views.LemmaListAPIView.as_view(), name="lemma_api_list"),
    path("api/concepts/versions", views.ConceptDistinctVersions.as_view(), name="concept_distinct_versions"),
    path("api/concept/<int:pk>", views.ConceptDetailAPIView.as_view(), name="concept_api_detail"),
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
    # Worklog
    path("api/worklogs", views.WorkLogAPIView.as_view(), name="worklog_list_api"),
    path("api/worklog/<int:pk>", views.WorklogDetailAPIView.as_view(), name="worklog_detail_api"),
    # WebAnno
    path("api/webanno_link/<document_id>", views.WebAnnoLink.as_view(), name="webanno_link_api"),
    ### Terms and Definitions Annotations API
    # API root
    path(
        "api/annotations/<str:annotation_type>/<str:concept_id>/<str:document_id>",
        views.ConceptAnnotationRootAPIView.as_view(),
        name="api_root",
    ),
    # Search
    path(
        "api/annotations/<str:annotation_type>/<str:concept_id>/<str:document_id>/search",
        views.ConceptAnnotationSearchListAPIView.as_view(),
        name="api_search",
    ),
    # Create
    path(
        "api/annotations/<str:annotation_type>/<str:concept_id>/<str:document_id>/annotations",
        views.ConceptAnnotationCreateListAPIView.as_view(),
        name="api_create",
    ),
    # Delete
    path(
        "api/annotations/<str:annotation_type>/<str:concept_id>/<str:document_id>/annotations/<str:annotation_id>",
        views.ConceptAnnotationDeleteAPIView.as_view(),
        name="api_delete",
    ),

    path(
        "api/conceptoccurs",
        views.ConceptOccursForConceptAPIView.as_view(),
        name="concept_occurs_list_api",
    ),
]
