# Generated by Django 3.0.3 on 2020-03-13 07:42

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("searchapp", "0010_auto_20200313_0533"),
    ]

    operations = [
        migrations.AlterField(
            model_name="acceptancestate",
            name="document",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="acceptance_states", to="searchapp.Document"
            ),
        ),
        migrations.AlterField(
            model_name="acceptancestate",
            name="user",
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL),
        ),
    ]
