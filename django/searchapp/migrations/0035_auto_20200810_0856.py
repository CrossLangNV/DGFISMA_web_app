# Generated by Django 3.0.9 on 2020-08-10 08:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("searchapp", "0034_document_deleted"),
    ]

    operations = [
        migrations.AddField(
            model_name="acceptancestate",
            name="deleted",
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="comment",
            name="deleted",
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="tag",
            name="deleted",
            field=models.DateTimeField(editable=False, null=True),
        ),
    ]
