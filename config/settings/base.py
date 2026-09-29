import os
from pathlib import Path
from urllib.parse import quote

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-only-change-me')
DEBUG = False

_allowed_hosts = os.getenv('DJANGO_ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [
    host.strip()
    for host in _allowed_hosts.split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'mozilla_django_oidc',
    'channels',
    'apps.map',
    'apps.orders',
    'apps.patients',
    'apps.teams',
    'apps.users',
    'apps.mgmt',
    'apps.missions',
    'auditlog',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

_keycloak_server_url = os.getenv('KEYCLOAK_SERVER_URL', '').strip().rstrip('/')
_keycloak_realm = os.getenv('KEYCLOAK_REALM', '').strip()
_keycloak_client_id = os.getenv('KEYCLOAK_CLIENT_ID', '').strip()
_keycloak_client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET', '').strip()
KEYCLOAK_REQUIRED_GROUP = os.getenv('KEYCLOAK_REQUIRED_GROUP', '').strip()
KEYCLOAK_GROUPS_CLAIM = os.getenv('KEYCLOAK_GROUPS_CLAIM', 'groups').strip()
KEYCLOAK_GROUPS_SCOPE = os.getenv('KEYCLOAK_GROUPS_SCOPE', 'groups').strip()

_keycloak_configuration = {
    'KEYCLOAK_SERVER_URL': _keycloak_server_url,
    'KEYCLOAK_REALM': _keycloak_realm,
    'KEYCLOAK_CLIENT_ID': _keycloak_client_id,
    'KEYCLOAK_CLIENT_SECRET': _keycloak_client_secret,
    'KEYCLOAK_REQUIRED_GROUP': KEYCLOAK_REQUIRED_GROUP,
}
_keycloak_configured = [bool(value) for value in _keycloak_configuration.values()]
if any(_keycloak_configured) and not all(_keycloak_configured):
    missing = ', '.join(
        name for name, value in _keycloak_configuration.items() if not value
    )
    raise ImproperlyConfigured(
        f'Unvollständige Keycloak-Konfiguration. Fehlend: {missing}'
    )

KEYCLOAK_SSO_ENABLED = all(_keycloak_configured)
OIDC_CREATE_USER = False
if KEYCLOAK_SSO_ENABLED:
    AUTHENTICATION_BACKENDS = [
        'apps.users.auth.KeycloakOIDCAuthenticationBackend',
    ]
    _keycloak_issuer = (
        f'{_keycloak_server_url}/realms/{quote(_keycloak_realm, safe="")}'
    )
    OIDC_RP_CLIENT_ID = _keycloak_client_id
    OIDC_RP_CLIENT_SECRET = _keycloak_client_secret
    OIDC_RP_SIGN_ALGO = 'RS256'
    _oidc_scopes = ['openid', 'email', 'profile']
    if KEYCLOAK_GROUPS_SCOPE and KEYCLOAK_GROUPS_SCOPE not in _oidc_scopes:
        _oidc_scopes.append(KEYCLOAK_GROUPS_SCOPE)
    OIDC_RP_SCOPES = ' '.join(_oidc_scopes)
    OIDC_USE_PKCE = True
    OIDC_CREATE_USER = True
    OIDC_CALLBACK_CLASS = 'apps.users.auth.KeycloakOIDCCallbackView'
    OIDC_AUTHENTICATE_CLASS = 'apps.users.auth.KeycloakOIDCRequestView'
    OIDC_OP_AUTHORIZATION_ENDPOINT = f'{_keycloak_issuer}/protocol/openid-connect/auth'
    OIDC_OP_TOKEN_ENDPOINT = f'{_keycloak_issuer}/protocol/openid-connect/token'
    OIDC_OP_USER_ENDPOINT = f'{_keycloak_issuer}/protocol/openid-connect/userinfo'
    OIDC_OP_JWKS_ENDPOINT = f'{_keycloak_issuer}/protocol/openid-connect/certs'
    LOGIN_REDIRECT_URL = '/'
    LOGIN_REDIRECT_URL_FAILURE = '/?sso=denied'
    LOGOUT_REDIRECT_URL = '/'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

if os.getenv('POSTGRES_HOST'):
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'einsatzleitsoftware'),
        'USER': os.getenv('POSTGRES_USER', 'einsatzleitsoftware'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'einsatzleitsoftware'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }}
else:
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'de-de'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'apps.users.auth': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')]},
    },
}

_trusted_origins = os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in _trusted_origins.split(",")
    if origin.strip()
]
