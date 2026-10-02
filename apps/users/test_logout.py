from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import Client, TestCase, override_settings


@override_settings(
    ROOT_URLCONF='config.urls',
    KEYCLOAK_SSO_ENABLED=True,
    OIDC_OP_LOGOUT_URL_METHOD='apps.users.views.provider_logout',
    OIDC_OP_LOGOUT_ENDPOINT='https://keycloak.example/realms/test/protocol/openid-connect/logout',
    OIDC_RP_CLIENT_ID='dispatch',
    LOGOUT_REDIRECT_URL='/',
)
class OIDCLogoutTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        user = get_user_model().objects.create_user(username='logout-user')
        self.client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        self.client.get('/api/auth/session/')
        self.csrf = self.client.cookies['csrftoken'].value

    def test_logout_redirects_with_token_and_clears_session(self):
        session = self.client.session
        session['oidc_id_token'] = 'signed.id-token+with/special=characters'
        session.save()
        response = self.client.post('/api/auth/logout/', {'csrfmiddlewaretoken': self.csrf})

        self.assertEqual(response.status_code, 302)
        url = urlsplit(response['Location'])
        self.assertEqual(url.netloc, 'keycloak.example')
        self.assertEqual(url.path, '/realms/test/protocol/openid-connect/logout')
        self.assertEqual(parse_qs(url.query), {
            'client_id': ['dispatch'],
            'id_token_hint': ['signed.id-token+with/special=characters'],
            'post_logout_redirect_uri': ['http://testserver/'],
        })
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotIn('oidc_id_token', self.client.session)
        self.assertFalse(self.client.get('/api/auth/session/').json()['authenticated'])

    def test_older_session_without_token_still_redirects_to_provider(self):
        response = self.client.post('/api/auth/logout/', {'csrfmiddlewaretoken': self.csrf})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(parse_qs(urlsplit(response['Location']).query), {
            'client_id': ['dispatch'],
            'post_logout_redirect_uri': ['http://testserver/'],
        })
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logout_requires_csrf_token(self):
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, 403)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_get_does_not_log_out(self):
        self.assertEqual(self.client.get('/api/auth/logout/').status_code, 405)
        self.assertIn(SESSION_KEY, self.client.session)

    @override_settings(KEYCLOAK_SSO_ENABLED=False, OIDC_OP_LOGOUT_URL_METHOD='')
    def test_password_logout_still_works(self):
        response = self.client.post('/api/auth/logout/', {'csrfmiddlewaretoken': self.csrf})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')
        self.assertNotIn(SESSION_KEY, self.client.session)
