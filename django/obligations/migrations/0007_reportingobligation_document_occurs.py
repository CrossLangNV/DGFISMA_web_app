# Generated by Django 3.0.9 on 2021-01-22 15:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("searchapp", "0049_merge_20210118_1027"),
        ("obligations", "0006_reportingobligationoffsets_roannotationworklog"),
    ]

    operations = [
        migrations.AddField(
            model_name="reportingobligation",
            name="document_occurs",
            field=models.ManyToManyField(
                related_name="ro_occurrance", through="obligations.ReportingObligationOffsets", to="searchapp.Document"
            ),
        ),
    ]