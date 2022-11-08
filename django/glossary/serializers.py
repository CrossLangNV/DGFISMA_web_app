from rest_framework import serializers
from django.contrib.auth.models import User, Group

from glossary.models import (
    Concept,
    Comment,
    Tag,
    AcceptanceState,
    AnnotationWorklog,
    ConceptOccurs,
    ConceptDefined,
    Lemma,
)
from searchapp.models import Document


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class AnnotationWorklogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnotationWorklog
        fields = "__all__"

    def create(self, validated_data):
        annotation_worklog = AnnotationWorklog.objects.create(**validated_data)
        return annotation_worklog


class ConceptOccursSerializer(serializers.ModelSerializer):
    concept = serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    id = serializers.PrimaryKeyRelatedField(many=False, read_only=True)  # Document id
    title = serializers.SerializerMethodField()
    website = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()

    occurances_occ = serializers.SerializerMethodField()

    def get_occurances_occ(self, concept_occurs):
        total_occurances_count = len(
            ConceptOccurs.objects.filter(concept__name=concept_occurs.concept.name, document=concept_occurs.document))
        return total_occurances_count

    def get_title(self, concept_occurs):
        return concept_occurs.document.title

    def get_website(self, concept_occurs):
        return concept_occurs.document.website.name

    def get_date(self, concept_occurs):
        return concept_occurs.document.date


    class Meta:
        model = ConceptOccurs
        fields = "__all__"

    def create(self, validated_data):
        concept_occurs = ConceptOccurs.objects.create(**validated_data)
        return concept_occurs


class ConceptDefinedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConceptDefined
        fields = "__all__"

    def create(self, validated_data):
        concept_defined = ConceptDefined.objects.create(**validated_data)
        return concept_defined


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
    concept = serializers.PrimaryKeyRelatedField(queryset=Concept.objects.all())
    user = UserSerializer(read_only=True)

    class Meta:
        model = AcceptanceState
        fields = "__all__"


class ConceptOtherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concept
        fields = ["id", "name"]


class ConceptSerializer(serializers.ModelSerializer):
    comments = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    acceptance_states = AcceptanceStateSerializer(many=True, read_only=True)
    acceptance_states_count = serializers.SerializerMethodField()
    acceptance_state = serializers.SerializerMethodField()
    acceptance_state_value = serializers.SerializerMethodField()
    other = ConceptOtherSerializer(many=True, read_only=True)

    def get_acceptance_states_count(self, concept):
        q = AcceptanceState.objects.filter(concept=concept)
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

    def get_acceptance_state(self, concept):
        user = self.context["request"].user
        qs = AcceptanceState.objects.filter(concept=concept, user=user)
        serializer = AcceptanceStateSerializer(instance=qs, many=True)
        state_id = None
        if len(serializer.data) > 0:
            state_id = serializer.data[0]["id"]
        return state_id

    def get_acceptance_state_value(self, concept):
        user = self.context["request"].user
        qs = AcceptanceState.objects.filter(concept=concept, user=user)
        res = qs.values_list("value", flat=True)
        if len(res):
            return res[0]
        else:
            return "Unvalidated"

    class Meta:
        model = Concept
        fields = "__all__"


class LemmaSerializer(serializers.ModelSerializer):
    concepts = serializers.SerializerMethodField()

    def get_concepts(self, lemma):
        qs = lemma.concepts.exclude(definition="")
        serializer = ConceptSerializer(
            instance=qs, many=True, read_only=True, context={"request": self.context["request"]}
        )
        return serializer.data

    class Meta:
        model = Lemma
        fields = "__all__"


class ConceptDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concept
        fields = ("id", "name", "definition")


class CommentSerializer(serializers.ModelSerializer):
    Concept = serializers.PrimaryKeyRelatedField(queryset=Concept.objects.all())
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    username = serializers.SerializerMethodField("get_username")

    class Meta:
        model = Comment
        fields = ["id", "value", "Concept", "user", "created_at", "username"]

    def get_username(self, comment):
        return comment.user.username
