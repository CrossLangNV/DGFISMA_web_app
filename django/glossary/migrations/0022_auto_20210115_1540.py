# Generated by Django 3.0.9 on 2021-01-15 15:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("glossary", "0021_auto_20210115_1531"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tag",
            name="value",
            field=models.CharField(max_length=50),
        ),
    ]
