# Generated by Django 3.0.9 on 2020-09-24 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("searchapp", "0036_auto_20200915_0901"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="unvalidated",
            field=models.BooleanField(default=True, editable=False),
        ),
    ]