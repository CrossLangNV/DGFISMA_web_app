# Generated by Django 3.0.9 on 2021-02-17 10:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("obligations", "0009_auto_20210216_0819"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="acceptancestate",
            options={"ordering": ["user"]},
        ),
    ]
