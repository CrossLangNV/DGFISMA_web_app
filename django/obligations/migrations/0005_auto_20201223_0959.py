# Generated by Django 3.0.9 on 2020-12-23 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("obligations", "0004_auto_20201202_1541"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="acceptancestate",
            constraint=models.CheckConstraint(
                check=models.Q(("user__isnull", False), ("probability_model__isnull", False), _connector="OR"),
                name="obligations_not_both_null",
            ),
        ),
    ]
