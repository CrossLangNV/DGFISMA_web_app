# Generated by Django 3.0.5 on 2020-04-16 11:17

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("searchapp", "0016_auto_20200414_2107"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="document",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
