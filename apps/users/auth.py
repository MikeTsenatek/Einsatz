import logging

from django.conf import settings
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from mozilla_django_oidc.views import (
    OIDCAuthenticationCallbackView,
    OIDCAuthenticationRequestView,
)


logger = logging.getLogger(__name__)


def _has_group(value, group):
    if isinstance(value, str):
        return value == group
    if isinstance(value, (list, tuple, set)):
        return group in value
    return False


class KeycloakOIDCRequestView(OIDCAuthenticationRequestView):
    def get(self, request):
        # Never log state, nonce, authorization codes, or the client secret.
        logger.info(
            'Keycloak-SSO Authorization-Anfrage: endpoint=%s, scopes=%r, '
            'response_type=code, PKCE=%s.',
            settings.OIDC_OP_AUTHORIZATION_ENDPOINT,
            settings.OIDC_RP_SCOPES,
            settings.OIDC_USE_PKCE,
        )
        return super().get(request)


class KeycloakOIDCCallbackView(OIDCAuthenticationCallbackView):
    def login_failure(self):
        logger.warning('Keycloak-SSO-Callback wurde abgelehnt oder abgebrochen.')
        return super().login_failure()


class KeycloakOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """Allow SSO only when Keycloak includes the configured group claim."""

    def authenticate(self, request, **kwargs):
        # The parent class also inherits username/password authentication from
        # ModelBackend; don't let that bypass the Keycloak group requirement.
        if 'username' in kwargs or 'password' in kwargs:
            return None
        try:
            user = super().authenticate(request, **kwargs)
        except Exception as error:
            logger.error(
                'Keycloak-SSO technisch fehlgeschlagen (Fehlertyp: %s).',
                type(error).__name__,
            )
            raise

        if user is not None and not user.is_active:
            logger.warning('Keycloak-SSO abgelehnt: Anwendungskonto ist deaktiviert.')
            return None
        if user is None and request and request.GET.get('code'):
            logger.warning(
                'Keycloak-SSO fehlgeschlagen: Anmeldung oder Benutzerzuordnung '
                'wurde abgelehnt; Details zu Claims folgen in den Meldungen davor.'
            )
        return user

    def get_userinfo(self, access_token, id_token, payload):
        claims = super().get_userinfo(access_token, id_token, payload)
        group_claim_name = settings.KEYCLOAK_GROUPS_CLAIM
        userinfo_groups = claims.get(group_claim_name, [])
        id_token_groups = payload.get(group_claim_name, [])
        required_group = settings.KEYCLOAK_REQUIRED_GROUP
        if (
            not _has_group(userinfo_groups, required_group)
            and not _has_group(id_token_groups, required_group)
        ):
            logger.warning(
                'Keycloak-SSO erforderliche Gruppe fehlt in beiden Quellen: '
                'scopes=%r, claim=%r, ID-Token-Gruppen=%r, UserInfo-Gruppen=%r.',
                settings.OIDC_RP_SCOPES,
                group_claim_name,
                id_token_groups,
                userinfo_groups,
            )
        if isinstance(userinfo_groups, str):
            userinfo_groups = [userinfo_groups]
        if isinstance(id_token_groups, str):
            id_token_groups = [id_token_groups]
        if isinstance(userinfo_groups, (list, tuple, set)) and isinstance(
            id_token_groups, (list, tuple, set)
        ):
            claims[group_claim_name] = list(dict.fromkeys(
                [*userinfo_groups, *id_token_groups]
            ))
        return claims

    def create_user(self, claims):
        user = super().create_user(claims)
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.is_active = True
        user.save(update_fields=('first_name', 'last_name', 'is_active'))
        return user

    def verify_claims(self, claims):
        if not super().verify_claims(claims):
            logger.warning('Keycloak-SSO abgelehnt: erforderlicher E-Mail-Claim fehlt.')
            return False

        required_group = settings.KEYCLOAK_REQUIRED_GROUP
        group_claim = claims.get(settings.KEYCLOAK_GROUPS_CLAIM, [])
        if isinstance(group_claim, str):
            group_claim = [group_claim]
        if not isinstance(group_claim, (list, tuple, set)):
            logger.warning(
                'Keycloak-SSO abgelehnt: Gruppen-Claim "%s" hat ein ungültiges Format.',
                settings.KEYCLOAK_GROUPS_CLAIM,
            )
            return False

        if not required_group or required_group not in group_claim:
            logger.warning(
                'Keycloak-SSO abgelehnt: Gruppe stimmt nicht überein '
                '(Claim "%s", erwartet=%r, erhalten=%r).',
                settings.KEYCLOAK_GROUPS_CLAIM,
                required_group,
                group_claim,
            )
            return False
        return True