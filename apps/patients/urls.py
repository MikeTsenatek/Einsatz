from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MissionTreatmentViewSet, PatientViewSet, TreatmentViewSet


router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patient")

patient_treatment_list = TreatmentViewSet.as_view({"get": "list", "post": "create"})
patient_treatment_detail = TreatmentViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)
mission_treatment_list = MissionTreatmentViewSet.as_view({"get": "list", "post": "create"})
mission_treatment_detail = MissionTreatmentViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = [
    *router.urls,
    path("patients/<int:patient_pk>/treatments/", patient_treatment_list, name="patient-treatment-list"),
    path("patients/<int:patient_pk>/treatments/<int:pk>/", patient_treatment_detail, name="patient-treatment-detail"),
    path("missions/<int:mission_pk>/treatments/", mission_treatment_list, name="mission-treatment-list"),
    path("missions/<int:mission_pk>/treatments/<int:pk>/", mission_treatment_detail, name="mission-treatment-detail"),
]
