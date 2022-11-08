from django.db import models
from django.utils import timezone
from django.db.models import Q
from rest_framework import serializers

from searchapp.models import Document


class ReportingObligation(models.Model):
    rdf_id = models.CharField(max_length=200, null=True, db_index=True)
    name = models.TextField()
    definition = models.TextField()
    version = models.CharField(max_length=50, db_index=True, default="initial")

    document_occurs = models.ManyToManyField(
        Document,
        through="ReportingObligationOffsets",
        through_fields=("ro", "document"),
        related_name="ro_occurrance",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ReportingObligationOffsets(models.Model):
    ro = models.ForeignKey(ReportingObligation, on_delete=models.CASCADE)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    quote = models.TextField(default="")
    probability = models.FloatField(default=0.0, blank=True)

    start = models.CharField(max_length=255, default="", blank=True, null=True)
    startOffset = models.IntegerField(default=0)
    end = models.CharField(max_length=255, default="", blank=True, null=True)
    endOffset = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Reporting Obligation Offsets"


class ROAnnotationWorklog(models.Model):
    ro_offsets = models.ForeignKey(ReportingObligationOffsets, on_delete=models.CASCADE, null=True)

    user = models.ForeignKey(
        "auth.User",
        related_name="obligation_user_worklog",
        on_delete=models.SET_NULL,
        null=True,
    )

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
    reporting_obligation = models.ForeignKey(
        "ReportingObligation",
        related_name="acceptance_states",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "auth.User",
        related_name="obligation_acceptance_state",
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
            models.UniqueConstraint(
                fields=["reporting_obligation_id", "user_id"],
                name="unique_per_reporting_obligation_and_user",
            ),
            models.UniqueConstraint(
                fields=["reporting_obligation_id", "probability_model"],
                name="unique_per_reporting_obligation_and_model",
            ),
            models.CheckConstraint(
                check=Q(user__isnull=False) | Q(probability_model__isnull=False),
                name="obligations_not_both_null",
            ),
        ]


class Comment(models.Model):
    value = models.TextField()
    reporting_obligation = models.ForeignKey("ReportingObligation", related_name="comments", on_delete=models.CASCADE)
    user = models.ForeignKey("auth.User", related_name="obligation_comment", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class Tag(models.Model):
    value = models.CharField(max_length=50)
    reporting_obligation = models.ForeignKey("ReportingObligation", related_name="tags", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.value


class RoDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportingObligation
        fields = ("id", "name")
