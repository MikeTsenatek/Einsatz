from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'apps.users'

    def ready(self):
        from .permissions import connect_permission_signals

        connect_permission_signals()
