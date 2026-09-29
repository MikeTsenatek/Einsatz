from .base import *  # noqa: F401,F403

DEBUG = True
_allowed_hosts = os.getenv('DJANGO_ALLOWED_HOSTS') or 'localhost,127.0.0.1,0.0.0.0,app'
ALLOWED_HOSTS = [
    host.strip()
    for host in _allowed_hosts.split(',')
    if host.strip()
]

if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
