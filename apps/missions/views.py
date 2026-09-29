from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.mgmt.models import PriorityEnum
from config.pagination import StandardResultsSetPagination
from config.permissions import StrictDjangoModelPermissions

from .models import Mission, OperationLogEntry
from .serializers import MissionSerializer, OperationLogEntrySerializer, PrioritySerializer


class MissionViewSet(viewsets.ModelViewSet):
    queryset = Mission.objects.all().order_by("name")
    serializer_class = MissionSerializer
    permission_classes = (StrictDjangoModelPermissions,)

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as error:
            raise ValidationError(
                {"detail": "Einsätze mit Einsatztagebuch-Einträgen können nicht gelöscht werden."}
            ) from error


class OperationLogEntryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OperationLogEntrySerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = (StrictDjangoModelPermissions,)
    http_method_names = ("get", "post", "patch", "head", "options")
    editable_fields = {"sender", "recipient", "timestamp", "text", "measure", "priority"}

    def get_queryset(self):
        queryset = OperationLogEntry.objects.select_related("priority").filter(
            mission_id=self.kwargs["mission_pk"]
        )
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(sender__icontains=search) | Q(recipient__icontains=search)
                | Q(text__icontains=search) | Q(measure__icontains=search)
            )
        visibility = self.request.query_params.get("visibility")
        if visibility == "active":
            queryset = queryset.filter(is_struck_out=False)
        elif visibility == "struck":
            queryset = queryset.filter(is_struck_out=True)
        return queryset.order_by("-timestamp", "-pk")

    def perform_create(self, serializer):
        serializer.save(mission=get_object_or_404(Mission, pk=self.kwargs["mission_pk"]))

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        fields = set(request.data)

        if fields == {"is_struck_out"} and request.data.get("is_struck_out") is True:
            if not instance.is_struck_out:
                instance.is_struck_out = True
                instance.save(update_fields=("is_struck_out",))
            return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

        if instance.is_struck_out:
            raise ValidationError(
                {"detail": "Gestrichene Einsatztagebuch-Einträge können nicht bearbeitet werden."}
            )
        if not fields or not fields.issubset(self.editable_fields):
            raise ValidationError(
                {"detail": "Der Eintrag enthält nicht bearbeitbare Felder."}
            )

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def history(self, request, *args, **kwargs):
        instance = self.get_object()
        content_type = ContentType.objects.get_for_model(
            OperationLogEntry,
            for_concrete_model=False,
        )
        logs = (
            LogEntry.objects.select_related("actor")
            .filter(content_type=content_type, object_pk=str(instance.pk))
            .order_by("-timestamp", "-pk")
        )
        return Response([
            {
                "id": log.pk,
                "timestamp": log.timestamp,
                "action": log.get_action_display(),
                "actor": (
                    {
                        "id": log.actor_id,
                        "name": log.actor.get_full_name() or log.actor.get_username(),
                    }
                    if log.actor
                    else None
                ),
                "changes": log.changes_dict,
            }
            for log in logs
        ])


class PriorityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PriorityEnum.objects.all()
    serializer_class = PrioritySerializer
    permission_classes = (StrictDjangoModelPermissions,)
