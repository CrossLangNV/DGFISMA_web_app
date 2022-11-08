# Generated by Django 3.0.9 on 2021-01-09 21:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("searchapp", "0045_auto_20210105_1001"),
        ("obligations", "0005_auto_20201223_0959"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportingObligationOffsets",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quote", models.TextField(default="")),
                ("probability", models.FloatField(blank=True, default=0.0)),
                ("start", models.CharField(blank=True, default="", max_length=255, null=True)),
                ("startOffset", models.IntegerField(default=0)),
                ("end", models.CharField(blank=True, default="", max_length=255, null=True)),
                ("endOffset", models.IntegerField(default=0)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="searchapp.Document")),
                (
                    "ro",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="obligations.ReportingObligation"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ROAnnotationWorklog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "ro_offsets",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="obligations.ReportingObligationOffsets",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="obligation_user_worklog",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
