# Generated by Django 3.0.9 on 2020-12-21 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("glossary", "0010_auto_20201210_1307"),
    ]

    operations = [
        migrations.AddField(
            model_name="concept",
            name="version",
            field=models.CharField(db_index=True, default="initial", max_length=50),
        ),
    ]