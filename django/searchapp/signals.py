from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save


def add_user_to_opinion_group(sender, instance, created, **kwargs):
    """Post-create user signal that adds the user to opinion group."""
    try:
        if created:
            instance.groups.add(Group.objects.get(name="opinion"))
    except Group.DoesNotExist:
        pass


post_save.connect(add_user_to_opinion_group, sender=User)
