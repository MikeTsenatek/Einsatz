from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import DjangoModelPermissions


class StrictDjangoModelPermissions(DjangoModelPermissions):
    """Use all four standard Django model permissions for CRUD."""

    message = "Bitte melden Sie sich an oder lassen Sie Ihre Rechte prüfen."

    perms_map = {
        **DjangoModelPermissions.perms_map,
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        queryset = self._queryset(view)
        required = self.get_required_permissions(request.method, queryset.model)
        missing = [permission for permission in required if not request.user.has_perm(permission)]
        if missing:
            raise PermissionDenied(
                "Für diese Aktion fehlen folgende Rechte: "
                f"{', '.join(missing)}. Bitte Gruppenmitgliedschaft oder Rechte "
                "durch die Administration prüfen lassen."
            )
        return True
