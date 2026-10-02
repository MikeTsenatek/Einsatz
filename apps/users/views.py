from urllib.parse import urlencode

from django.contrib.auth import authenticate, login
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def _user_payload(user):
    return {
        "is_staff": user.is_staff,
        "id": user.pk,
        "username": user.get_username(),
        "name": user.get_full_name() or user.get_username(),
        "permissions": sorted(user.get_all_permissions()),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def session_view(request):
    if not request.user.is_authenticated:
        return Response({"authenticated": False, "sso_enabled": settings.KEYCLOAK_SSO_ENABLED})
    return Response({"authenticated": True, "sso_enabled": settings.KEYCLOAK_SSO_ENABLED, "user": _user_payload(request.user)})


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    if settings.KEYCLOAK_SSO_ENABLED:
        return Response(
            {"detail": "Die Anmeldung erfolgt über Keycloak."},
            status=status.HTTP_403_FORBIDDEN,
        )
    user = authenticate(request, username=request.data.get("username", "").strip(), password=request.data.get("password", ""))
    if user is None:
        return Response({"detail": "Benutzername oder Passwort ist nicht korrekt."}, status=status.HTTP_400_BAD_REQUEST)
    login(request, user)
    return Response({"authenticated": True, "user": _user_payload(user)})


def provider_logout(request):
    """Build the RP-initiated logout URL before OIDCLogoutView clears the session."""
    params = {
        'client_id': settings.OIDC_RP_CLIENT_ID,
        'post_logout_redirect_uri': request.build_absolute_uri(settings.LOGOUT_REDIRECT_URL),
    }
    id_token = request.session.get('oidc_id_token')
    if id_token:
        params['id_token_hint'] = id_token
    # Older sessions without an ID token require confirmation at Keycloak.
    return f'{settings.OIDC_OP_LOGOUT_ENDPOINT}?{urlencode(params)}'
