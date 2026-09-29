from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate, post_save


DEFAULT_GROUP_NAME = "Standardbenutzer"
DEFAULT_GROUP_APP_LABELS = ("map", "mgmt", "missions", "patients", "teams")


def ensure_standard_group(sender, using, **kwargs):
    """Create the operational group, grant app permissions, and backfill users."""
    group, _ = Group.objects.using(using).get_or_create(name=DEFAULT_GROUP_NAME)
    permissions = Permission.objects.using(using).filter(
        content_type__app_label__in=DEFAULT_GROUP_APP_LABELS,
    ).exclude(codename__startswith="delete_")
    group.permissions.add(*permissions)

    user_model = get_user_model()
    users_without_group = user_model.objects.using(using).exclude(groups__pk=group.pk)
    for user in users_without_group.iterator():
        user.groups.add(group)


def add_standard_group_on_user_save(sender, instance, raw=False, using=None, **kwargs):
    if raw:
        return
    group = Group.objects.using(using or instance._state.db).filter(
        name=DEFAULT_GROUP_NAME,
    ).first()
    if group is not None:
        instance.groups.add(group)


def connect_permission_signals():
    post_migrate.connect(
        ensure_standard_group,
        dispatch_uid="apps.users.ensure_standard_group",
    )
    post_save.connect(
        add_standard_group_on_user_save,
        sender=settings.AUTH_USER_MODEL,
        dispatch_uid="apps.users.add_standard_group_on_user_save",
    )