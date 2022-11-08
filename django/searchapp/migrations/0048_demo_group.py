from django.db import migrations


def apply_migration(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.create(name="demo")
    demo_group = Group.objects.get(name="demo")
    Permission = apps.get_model("auth", "Permission")
    perms = Permission.objects.all()
    for p in perms:
        demo_group.permissions.add(p)


class Migration(migrations.Migration):
    dependencies = [
        ("searchapp", "0047_auto_20210115_1531"),
    ]

    operations = [migrations.RunPython(apply_migration)]
