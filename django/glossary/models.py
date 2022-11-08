from django.db import models
from django.db.models import Q
from django.utils import timezone

from searchapp.models import Document, Website


class Lemma(models.Model):
    name = models.CharField(max_length=200, db_index=True, blank=False)

    def __str__(self):
        return self.name


class Concept(models.Model):
    name = models.CharField(max_length=500, db_index=True)
    definition = models.TextField()
    lemma = models.CharField(max_length=500, db_index=True, blank=False)
    lemma_fk = models.ForeignKey(Lemma, related_name="concepts", on_delete=models.CASCADE, null=True)
    version = models.CharField(max_length=50, db_index=True, default="initial")
    website = models.ForeignKey(Website, related_name="website", on_delete=models.CASCADE, null=True)
    other = models.ManyToManyField("self", blank=True)
    document_occurs = models.ManyToManyField(
        Document,
        through="ConceptOccurs",
        through_fields=("concept", "document"),
        related_name="occurrance",
    )
    document_defined = models.ManyToManyField(
        Document,
        through="ConceptDefined",
        through_fields=("concept", "document"),
        related_name="definition",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ConceptOffsetBase(models.Model):
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    quote = models.TextField(default="")
    probability = models.FloatField(default=0.0, blank=True)

    start = models.CharField(max_length=255, default="", blank=True, null=True)
    startOffset = models.IntegerField(default=0)
    end = models.CharField(max_length=255, default="", blank=True, null=True)
    endOffset = models.IntegerField(default=0)

    class Meta:
        abstract = True


class ConceptOccurs(ConceptOffsetBase):
    class Meta(ConceptOffsetBase.Meta):
        verbose_name_plural = "Concept Occurances"


class ConceptDefined(ConceptOffsetBase):
    class Meta(ConceptOffsetBase.Meta):
        verbose_name_plural = "Concept Definitions"


class AnnotationWorklog(models.Model):
    concept_occurs = models.ForeignKey(ConceptOccurs, on_delete=models.CASCADE, null=True)
    concept_defined = models.ForeignKey(ConceptDefined, on_delete=models.CASCADE, null=True)

    document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True)

    user = models.ForeignKey("auth.User", related_name="user_worklog", on_delete=models.SET_NULL, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class AcceptanceStateValue(models.TextChoices):
    UNVALIDATED = ("Unvalidated",)
    ACCEPTED = ("Accepted",)
    REJECTED = "Rejected"


class AcceptanceState(models.Model):
    value = models.CharField(
        max_length=20,
        choices=AcceptanceStateValue.choices,
        default=AcceptanceStateValue.UNVALIDATED,
        db_index=True,
    )
    concept = models.ForeignKey("Concept", related_name="acceptance_states", on_delete=models.CASCADE)
    user = models.ForeignKey(
        "auth.User",
        related_name="user_acceptance_state",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    probability_model = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    accepted_probability = models.FloatField(default=0.0, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["concept_id", "user_id"], name="unique_per_concepts_and_user"),
            models.UniqueConstraint(
                fields=["concept_id", "probability_model"],
                name="unique_per_concept_and_model",
            ),
            models.CheckConstraint(
                check=Q(user__isnull=False) | Q(probability_model__isnull=False),
                name="glossary_not_both_null",
            ),
        ]


class Comment(models.Model):
    value = models.TextField()
    Concept = models.ForeignKey("Concept", related_name="comments", on_delete=models.CASCADE)
    user = models.ForeignKey("auth.User", related_name="user_comment", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class Tag(models.Model):
    value = models.CharField(max_length=50)
    concept = models.ForeignKey("Concept", related_name="tags", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.value
