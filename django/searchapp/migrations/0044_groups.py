from django.db import migrations


def apply_migration(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.bulk_create([Group(name=u"opinion"), Group(name=u"decision")])
    opinion_group = Group.objects.get(name="opinion")
    decision_group = Group.objects.get(name="decision")
    Permission = apps.get_model("auth", "Permission")
    perms = Permission.objects.all()
    for p in perms:
        opinion_group.permissions.add(p)
        decision_group.permissions.add(p)


class Migration(migrations.Migration):
    dependencies = [
        ("searchapp", "0043_auto_20201231_1027"),
    ]

    operations = [migrations.RunPython(apply_migration)]
