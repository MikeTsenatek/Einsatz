from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


def _user_payload(user):
    return {"is_staff": user.is_staff, "id": user.pk, "username": user.get_username(), "name": user.get_full_name() or user.get_username()}


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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)
