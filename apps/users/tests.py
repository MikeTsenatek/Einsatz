from django.contrib.auth import get_user_model
from django.core.exceptions import SuspiciousOperation
from django.test import override_settings
from django.test import TestCase
from unittest.mock import patch

from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from .auth import KeycloakOIDCAuthenticationBackend


class UserModelTests(TestCase):
    def test_create_user(self):
        user = get_user_model().objects.create_user(
            username='dispatcher',
            password='secure-password',
        )

        self.assertEqual(user.username, 'dispatcher')
        self.assertTrue(user.check_password('secure-password'))
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='secure-password',
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


@override_settings(
    KEYCLOAK_REQUIRED_GROUP='/einsatzleitung',
    KEYCLOAK_GROUPS_CLAIM='groups',
    OIDC_OP_TOKEN_ENDPOINT='https://keycloak.example/token',
    OIDC_OP_USER_ENDPOINT='https://keycloak.example/userinfo',
    OIDC_OP_JWKS_ENDPOINT='https://keycloak.example/certs',
    OIDC_RP_CLIENT_ID='test-client',
    OIDC_RP_CLIENT_SECRET='test-secret',
    OIDC_RP_SIGN_ALGO='RS256',
    OIDC_RP_SCOPES='openid email',
)
class KeycloakGroupAccessTests(TestCase):
    def test_allows_user_in_required_keycloak_group(self):
        backend = KeycloakOIDCAuthenticationBackend()

        self.assertTrue(backend.verify_claims({
            'email': 'user@example.org',
            'groups': ['/einsatzleitung', '/weitere-gruppe'],
        }))

    def test_denies_user_outside_required_keycloak_group(self):
        backend = KeycloakOIDCAuthenticationBackend()

        with self.assertLogs('apps.users.auth', level='WARNING') as logs:
            self.assertFalse(backend.verify_claims({
                'email': 'user@example.org',
                'groups': ['/andere-gruppe'],
            }))

        self.assertIn("erwartet='/einsatzleitung'", logs.output[0])
        self.assertIn("erhalten=['/andere-gruppe']", logs.output[0])

    def test_denies_user_when_group_claim_is_missing(self):
        backend = KeycloakOIDCAuthenticationBackend()

        self.assertFalse(backend.verify_claims({'email': 'user@example.org'}))

    def test_uses_group_claim_from_verified_id_token_when_userinfo_omits_it(self):
        backend = KeycloakOIDCAuthenticationBackend()
        with patch.object(
            OIDCAuthenticationBackend,
            'get_userinfo',
            return_value={'email': 'user@example.org'},
        ):
            claims = backend.get_userinfo(
                'access-token',
                'id-token',
                {'groups': ['/einsatzleitung']},
            )

        self.assertEqual(claims['groups'], ['/einsatzleitung'])

    def test_logs_scopes_and_group_claim_sources_when_group_is_absent(self):
        backend = KeycloakOIDCAuthenticationBackend()
        with patch.object(
            OIDCAuthenticationBackend,
            'get_userinfo',
            return_value={'email': 'user@example.org'},
        ), self.assertLogs('apps.users.auth', level='WARNING') as logs:
            backend.get_userinfo('access-token', 'id-token', {})

        self.assertIn("scopes='openid email'", logs.output[0])
        self.assertIn('ID-Token-Gruppen=None', logs.output[0])
        self.assertIn('UserInfo-Gruppen=None', logs.output[0])

    @override_settings(OIDC_CREATE_USER=True)
    def test_registers_active_user_when_group_matches(self):
        backend = KeycloakOIDCAuthenticationBackend()
        with patch.object(
            backend,
            'get_userinfo',
            return_value={
                'email': 'new-user@example.org',
                'groups': ['/einsatzleitung'],
                'given_name': 'Erika',
                'family_name': 'Muster',
            },
        ):
            user = backend.get_or_create_user('access-token', 'id-token', {})

        self.assertTrue(user.is_active)
        self.assertEqual(user.email, 'new-user@example.org')
        self.assertEqual(user.first_name, 'Erika')
        self.assertEqual(user.last_name, 'Muster')

    @override_settings(OIDC_CREATE_USER=True)
    def test_does_not_register_user_when_group_does_not_match(self):
        backend = KeycloakOIDCAuthenticationBackend()
        with patch.object(
            backend,
            'get_userinfo',
            return_value={
                'email': 'blocked-user@example.org',
                'groups': ['/andere-gruppe'],
            },
        ):
            with self.assertRaises(SuspiciousOperation):
                backend.get_or_create_user('access-token', 'id-token', {})

        self.assertFalse(
            get_user_model().objects.filter(email='blocked-user@example.org').exists()
        )

    def test_rejects_password_authentication(self):
        backend = KeycloakOIDCAuthenticationBackend()

        self.assertIsNone(backend.authenticate(
            None,
            username='dispatcher',
            password='secure-password',
        ))

    @override_settings(KEYCLOAK_SSO_ENABLED=True)
    def test_password_login_is_disabled_when_keycloak_sso_is_enabled(self):
        response = self.client.post(
            '/api/auth/login/',
            data={'username': 'dispatcher', 'password': 'secure-password'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
