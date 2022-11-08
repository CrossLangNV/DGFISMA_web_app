from dblogging.models import DbQuery
from rest_framework import serializers


class DbQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = DbQuery
        fields = "__all__"
