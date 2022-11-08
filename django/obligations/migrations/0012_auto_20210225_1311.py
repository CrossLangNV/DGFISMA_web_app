from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("obligations", "0011_merge_20210222_1544"),
    ]

    operations = [TrigramExtension()]
