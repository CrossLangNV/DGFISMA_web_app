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
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.views.generic import RedirectView

from admin_rest.models import site
from project import settings
from django.conf.urls import url

urlpatterns = [
    path("", RedirectView.as_view(url="admin/", permanent=True)),
    path("admin/api/", site.urls),
    path("admin/", admin.site.urls),
    path("searchapp/", include(("searchapp.urls", "searchapp"), namespace="searchapp")),
    path("social-auth/", include("social_django.urls", namespace="social-view")),
    path("auth/", include("rest_framework_social_oauth2.urls")),
    path("glossary/", include(("glossary.urls", "glossary"), namespace="glossary")),
    path("obligations/", include(("obligations.urls", "obligations"), namespace="obligations")),
    path("dblogging/", include(("dblogging.urls", "dblogging"), namespace="dblogging")),
    path("ht/", include("health_check.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
