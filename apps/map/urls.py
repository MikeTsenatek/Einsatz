from django.urls import path
from .views import MissionMapView, MissionGeoJSONView

urlpatterns = [
    path('missions/<int:mission_pk>/map/', MissionMapView.as_view(), name='mission-map'),
    path('missions/<int:mission_pk>/map/geojson/', MissionGeoJSONView.as_view(), name='mission-geojson'),
]
