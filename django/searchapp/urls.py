"""django URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path, re_path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

import os

from searchapp import views

schema_view = get_schema_view(
    openapi.Info(
        title="Catalogue Manager API",
        default_version="v1",
        description="Documentation for REST API",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="nobody@crosslang.com"),
        license=openapi.License(name="BSD License"),
    ),
    url=os.environ["DJANGO_BASE_URL"],
    patterns=[path("searchapp/", include(("searchapp.urls", "searchapp"), namespace="searchapp"))],
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="searchapp/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # API
    # Swagger drf-yasg
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    # Website
    path("api/websites", views.WebsiteListAPIView.as_view(), name="website_list_api"),
    path("api/website/<int:pk>", views.WebsiteDetailAPIView.as_view(), name="website_detail_api"),
    # Document
    path("api/documents", views.DocumentListAPIView.as_view(), name="document_list_api"),
    path("api/document/<uuid:pk>", views.DocumentDetailAPIView.as_view(), name="document_detail_api"),
    # EurLex Formex
    path("api/formex/urls/<str:celex>", views.FormexUrlsAPIView.as_view(), name="formex_urls_api"),
    path("api/formex/act/<str:celex>", views.FormexActAPIView.as_view(), name="formex_act_api"),
    # Attachment
    path("api/attachments", views.AttachmentListAPIView.as_view(), name="attachment_list_api"),
    path("api/attachment/<uuid:pk>", views.AttachmentDetailAPIView.as_view(), name="attachment_detail_api"),
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
    # Document stats
    path("api/stats", views.DocumentStats.as_view(), name="document_stats"),
    # Super
    path("api/super", views.IsSuperUserAPIView.as_view(), name="super_api"),
    # Solr
    path("api/solrdocument/search/", views.SolrDocumentSearchPost.as_view(), name="solr_document_search_post_api"),
    # Django + SOLR
    path(
        "api/solrdocument/search/query/django/",
        views.SolrDocumentsSearchQueryDjango.as_view(),
        name="solr_document_search_query_django_api",
    ),
    path(
        "api/solrdocument/search/ro_query/django/",
        views.SolrDocumentsSearchQueryDjangoReportingObligation.as_view(),
        name="solr_document_search_query_django_by_ro_api",
    ),
    # SOLR ONLY
    path(
        "api/solrdocument/search/query/preanalyzed/",
        views.SolrDocumentsSearchQueryPreAnalyzed.as_view(),
        name="solr_document_search_query_preanalyzed_api",
    ),
    path(
        "api/solrdocument/search/query/preanalyzed/<doc_id>",
        views.SolrDocumentSearchQueryPreAnalyzed.as_view(),
        name="solr_search_query_with_doc_id_preanalyzed_api",
    ),
    # solr_get_preanalyzed_for_doc
    path("api/solrdocuments/like/<id>", views.SimilarDocumentsAPIView.as_view(), name="similar_documents_api"),
    # Export
    path("api/export/launch", views.ExportDocumentsLaunch.as_view(), name="export_launch_api"),
    path("api/export/status/<task_id>", views.ExportDocumentsStatus.as_view(), name="export_status_api"),
    path("api/export/download/<task_id>", views.ExportDocumentsDownload.as_view(), name="export_download_api"),
    # Bookmarks
    path("api/bookmarks", views.BookmarkListAPIView.as_view(), name="bookmark_list_api"),
    path("api/bookmarks/<document_id>", views.BookmarkDetailAPIView.as_view(), name="bookmark_detail_api"),
    # Dropdown: celex
    path("api/filters/celex", views.CelexListAPIView.as_view(), name="celex_list_api"),
    # Dropdown: type
    path("api/filters/type", views.TypeListAPIView.as_view(), name="type_list_api"),
    # Dropdown: status
    path("api/filters/status", views.StatusListAPIView.as_view(), name="status_list_api"),
    # Dropdown: eli
    path("api/filters/eli", views.EliListAPIView.as_view(), name="eli_list_api"),
    # Dropdown: eli
    path("api/filters/author", views.AuthorListAPIView.as_view(), name="eli_list_api"),
    # Dropdown: eli
    path("api/filters/effectdate", views.DateOfEffectListAPIView.as_view(), name="eli_list_api"),
    path("api/version", views.AppVersion.as_view(), name="app_version_api"),
    # Usernames
    path("api/userlist", views.UserListAPIView.as_view(), name="user_list_api"),
    # Public API for Solr
    path("api/solr/query", views.SolrPublicDocumentSearch.as_view(), name="solr_public_query_api"),
]
