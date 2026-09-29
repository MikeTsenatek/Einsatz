from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import SuspiciousOperation
from django.test import override_settings
from django.test import TestCase
from unittest.mock import patch

from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from .auth import KeycloakOIDCAuthenticationBackend
from .permissions import DEFAULT_GROUP_NAME, ensure_standard_group


class UserModelTests(TestCase):
    def test_create_user(self):
        user = get_user_model().objects.create_user(
            username='dispatcher',
            password='secure-password',
        )

        self.assertEqual(user.username, 'dispatcher')
        self.assertTrue(user.check_password('secure-password'))
        self.assertFalse(user.is_staff)
        self.assertTrue(user.groups.filter(name='Standardbenutzer').exists())
        self.assertTrue(user.has_perm('patients.view_patient'))
        self.assertTrue(user.has_perm('teams.add_helpermission'))
        self.assertTrue(user.has_perm('map.change_mapoverlay'))
        self.assertFalse(user.has_perm('patients.delete_patient'))
        self.assertFalse(user.has_perm('teams.delete_helper'))

    def test_create_superuser(self):
        user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='secure-password',
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.groups.filter(name='Standardbenutzer').exists())

    def test_standard_group_is_not_an_admin_or_superuser_group(self):
        group = Group.objects.get(name=DEFAULT_GROUP_NAME)
        self.assertFalse(group.permissions.filter(content_type__app_label='users').exists())
        self.assertFalse(group.permissions.filter(codename='delete_user').exists())
        self.assertFalse(group.permissions.filter(codename__startswith='delete_').exists())

    def test_migration_hook_backfills_existing_users(self):
        user = get_user_model().objects.create_user(username='existing-dispatcher')
        user.groups.clear()

        ensure_standard_group(sender=None, using='default')

        self.assertTrue(user.groups.filter(name=DEFAULT_GROUP_NAME).exists())


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

    @override_settings(KEYCLOAK_REQUIRED_GROUP='einsatzverwaltung')
    def test_merges_group_claims_from_userinfo_and_id_token(self):
        backend = KeycloakOIDCAuthenticationBackend()
        with patch.object(
            OIDCAuthenticationBackend,
            'get_userinfo',
            return_value={
                'email': 'user@example.org',
                'groups': ['digitalfunk'],
            },
        ):
            claims = backend.get_userinfo(
                'access-token',
                'id-token',
                {'groups': ['einsatzverwaltung']},
            )

        self.assertEqual(
            claims['groups'],
            ['digitalfunk', 'einsatzverwaltung'],
        )
        self.assertTrue(backend.verify_claims(claims))

    def test_logs_scopes_and_group_claim_sources_when_group_is_absent(self):
        backend = KeycloakOIDCAuthenticationBackend()
        with patch.object(
            OIDCAuthenticationBackend,
            'get_userinfo',
            return_value={'email': 'user@example.org'},
        ), self.assertLogs('apps.users.auth', level='WARNING') as logs:
            backend.get_userinfo('access-token', 'id-token', {})

        self.assertIn("scopes='openid email'", logs.output[0])
        self.assertIn('ID-Token-Gruppen=[]', logs.output[0])
        self.assertIn('UserInfo-Gruppen=[]', logs.output[0])

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
        self.assertTrue(user.groups.filter(name='Standardbenutzer').exists())

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
