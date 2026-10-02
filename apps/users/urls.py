from django.urls import path
from mozilla_django_oidc.views import OIDCLogoutView

from .views import login_view, session_view

urlpatterns = [
    path('auth/session/', session_view),
    path('auth/login/', login_view),
    path('auth/logout/', OIDCLogoutView.as_view()),
]
