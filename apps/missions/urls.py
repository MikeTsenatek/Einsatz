from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MissionViewSet, OperationLogEntryViewSet, PriorityViewSet


router = DefaultRouter()
router.register("missions", MissionViewSet, basename="mission")
router.register("priorities", PriorityViewSet, basename="priority")

operation_log_list = OperationLogEntryViewSet.as_view({"get": "list", "post": "create"})
operation_log_detail = OperationLogEntryViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update"}
)
operation_log_history = OperationLogEntryViewSet.as_view({"get": "history"})

urlpatterns = [
    path(
        "missions/<int:mission_pk>/operation-log/",
        operation_log_list,
        name="operation-log-entry-list",
    ),
    path(
        "missions/<int:mission_pk>/operation-log/<int:pk>/",
        operation_log_detail,
        name="operation-log-entry-detail",
    ),
    path(
        "missions/<int:mission_pk>/operation-log/<int:pk>/history/",
        operation_log_history,
        name="operation-log-entry-history",
    ),
    *router.urls,
]
