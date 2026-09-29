from django.urls import path
from .views import login_view, logout_view, session_view
urlpatterns = [path("auth/session/", session_view), path("auth/login/", login_view), path("auth/logout/", logout_view)]
