from django.contrib.auth.models import User
from rest_framework import permissions, filters, status
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from dblogging.models import DbQuery
from dblogging.serializers import DbQuerySerializer


class SmallResultsSetPagination(LimitOffsetPagination):
    default_limit = 5
    limit_query_param = "rows"
    offset_query_param = "page"


class DbQueryListAPIView(ListCreateAPIView):
    pagination_class = SmallResultsSetPagination
    serializer_class = DbQuerySerializer
    queryset = DbQuery.objects.all()
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at"]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        q = DbQuery.objects.all()
        email = self.request.GET.get("user", "")
        app = self.request.GET.get("app", "")

        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = User.objects.get(username=email)

            q = q.filter(user__iexact=user.username)

        if app:
            q = q.filter(app__iexact=app)

        return q.order_by("-id")


class DbQueryDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = DbQuerySerializer
    queryset = DbQuery.objects.all()
    permission_classes = [permissions.IsAuthenticated]
