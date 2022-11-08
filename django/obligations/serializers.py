from rest_framework import serializers

from obligations.models import (
    ReportingObligation,
    Tag,
    AcceptanceState,
    Comment,
    ROAnnotationWorklog,
    ReportingObligationOffsets,
)
from django.contrib.auth.models import User, Group
import logging as logger

from obligations.models import AcceptanceStateValue


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class ROAnnotationWorklogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ROAnnotationWorklog
        fields = "__all__"

    def create(self, validated_data):
        annotation_worklog = ROAnnotationWorklog.objects.create(**validated_data)
        return annotation_worklog


class ReportingObligationOffsetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportingObligationOffsets
        fields = "__all__"

    def create(self, validated_data):
        ro_offsets = ReportingObligationOffsets.objects.create(**validated_data)
        return ro_offsets


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
    reporting_obligation = serializers.PrimaryKeyRelatedField(queryset=ReportingObligation.objects.all())
    user = UserSerializer(read_only=True)

    class Meta:
        model = AcceptanceState
        fields = "__all__"


class CommentSerializer(serializers.ModelSerializer):
    reporting_obligation = serializers.PrimaryKeyRelatedField(queryset=ReportingObligation.objects.all())
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    username = serializers.SerializerMethodField("get_username")

    class Meta:
        model = Comment
        fields = ["id", "value", "reporting_obligation", "user", "created_at", "username"]

    def get_username(self, comment):
        return comment.user.username


class ReportingObligationSerializer(serializers.ModelSerializer):
    comments = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    acceptance_states = AcceptanceStateSerializer(many=True, read_only=True)
    acceptance_states_count = serializers.SerializerMethodField()
    acceptance_state = serializers.SerializerMethodField()
    acceptance_state_value = serializers.SerializerMethodField()

    def get_acceptance_state(self, reporting_obligation):
        user = self.context["request"].user
        qs = AcceptanceState.objects.filter(reporting_obligation=reporting_obligation, user=user)
        serializer = AcceptanceStateSerializer(instance=qs, many=True)
        state_id = None
        if len(serializer.data) > 0:
            state_id = serializer.data[0]["id"]
        else:
            new_unvalidated_state = AcceptanceState(
                reporting_obligation=reporting_obligation, user=user, value=AcceptanceStateValue.UNVALIDATED
            )
            state_id = new_unvalidated_state.id
        return state_id

    def get_acceptance_state_value(self, reporting_obligation):
        user = self.context["request"].user
        qs = AcceptanceState.objects.filter(reporting_obligation=reporting_obligation, user=user)
        res = qs.values_list("value", flat=True)
        if len(res):
            return res[0]
        else:
            return "Unvalidated"

    def get_acceptance_states_count(self, reporting_obligation):
        q = AcceptanceState.objects.filter(reporting_obligation=reporting_obligation)
        qs1 = q.filter(value="Accepted")
        qs2 = q.filter(value="Rejected")
        qs3 = q.filter(value="Unvalidated")

        count_values = [qs1, qs2, qs3]
        result = []

        for cvalue in count_values:
            if cvalue.count() > 0:
                result.append(
                    {"value": f"{cvalue[0].value} ({str(cvalue.count())})", "style": str(cvalue[0].value).lower()}
                )

        return result

    class Meta:
        model = ReportingObligation
        fields = "__all__"
