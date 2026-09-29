from django.urls import path

from .views import HelperDeleteView, HelperSearchView, MissionHelperMissionViewSet, MissionTeamViewSet


helper_mission_list = MissionHelperMissionViewSet.as_view({"get": "list", "post": "create"})
helper_mission_detail = MissionHelperMissionViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "put": "update", "delete": "destroy"}
)
team_list = MissionTeamViewSet.as_view({"get": "list", "post": "create"})
team_detail = MissionTeamViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "put": "update", "delete": "destroy"}
)

team_end_duty = MissionTeamViewSet.as_view({"patch": "end_duty"})

urlpatterns = [
    path("helpers/<int:pk>/", HelperDeleteView.as_view(), name="helper-delete"),
    path("helpers/search/", HelperSearchView.as_view(), name="helper-search"),
    path("missions/<int:mission_pk>/teams/<int:pk>/end-duty/", team_end_duty, name="mission-team-end-duty"),
    path("missions/<int:mission_pk>/helpers/", helper_mission_list, name="mission-helper-list"),
    path("missions/<int:mission_pk>/helpers/<int:pk>/", helper_mission_detail, name="mission-helper-detail"),
    path("missions/<int:mission_pk>/teams/", team_list, name="mission-team-list"),
    path("missions/<int:mission_pk>/teams/<int:pk>/", team_detail, name="mission-team-detail"),
]
