from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import DestroyAPIView, ListAPIView

from apps.missions.models import Mission
from config.permissions import StrictDjangoModelPermissions

from .models import Helper, HelperMission, Team
from .serializers import HelperMissionSerializer, TeamSerializer, HelperSuggestionSerializer


class MissionTeamViewSet(ModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = (StrictDjangoModelPermissions,)

    def get_mission(self):
        return get_object_or_404(Mission, pk=self.kwargs["mission_pk"])

    def get_queryset(self):
        return Team.objects.filter(mission_id=self.kwargs["mission_pk"])

    def perform_create(self, serializer):
        serializer.save(mission=self.get_mission())

    def end_duty(self, request, *args, **kwargs):
        if not request.user.has_perm("teams.change_helpermission"):
            raise PermissionDenied("Zum Beenden der Dienstzeiten fehlt die Berechtigung.")
        with transaction.atomic():
            team = get_object_or_404(self.get_queryset().select_for_update(), pk=kwargs["pk"])
            if team.end_date is None:
                ended_at = timezone.now()
                assignments = team.helper_missions.filter(end_date__isnull=True)
                if assignments.filter(start_date__gt=ended_at).exists():
                    raise ValidationError({"detail": "Ein Dienstbeginn liegt in der Zukunft. Bitte zuerst korrigieren."})
                assignments.update(end_date=ended_at)
                team.end_date = ended_at
                team.save(update_fields=("end_date",))
            return Response(self.get_serializer(team).data)


class MissionHelperMissionViewSet(ModelViewSet):
    serializer_class = HelperMissionSerializer
    permission_classes = (StrictDjangoModelPermissions,)

    def get_mission(self):
        return get_object_or_404(Mission, pk=self.kwargs["mission_pk"])

    def get_queryset(self):
        return HelperMission.objects.filter(
            mission_id=self.kwargs["mission_pk"]
        ).select_related("helper", "team")

    def resolve_helper(self, serializer):
        selected_helper = serializer.validated_data.get("helper")
        details = serializer.validated_data.pop("helper_details", None)
        if selected_helper is not None:
            return selected_helper
        if details is None:
            return serializer.instance.helper

        name = details["name"].strip()
        birthday = details.get("birthday")
        matches = Helper.objects.select_for_update().filter(name__iexact=name)
        existing = (
            matches.filter(birthday=birthday).first()
            if birthday is not None
            else matches.filter(birthday__isnull=True).first()
        )
        if existing:
            return existing
        if not self.request.user.has_perm("teams.add_helper"):
            raise PermissionDenied("Für das Anlegen eines neuen Helfers fehlt die Berechtigung.")
        return Helper.objects.create(
            name=name, **{key: value for key, value in details.items() if key != "name"}
        )

    def validate_helper(self, helper, mission, instance=None):
        active = HelperMission.objects.filter(
            helper=helper, mission=mission, end_date__isnull=True,
        )
        if instance is not None:
            active = active.exclude(pk=instance.pk)
        if active.exists():
            raise ValidationError({"helper": "Der Helfer befindet sich bereits im Dienst."})

    def save(self, serializer):
        mission = self.get_mission()
        birthday_changed = "helper_birthday" in serializer.validated_data
        birthday = serializer.validated_data.pop("helper_birthday", None)
        if birthday_changed and not self.request.user.has_perm("teams.change_helper"):
            raise PermissionDenied("Zum Ändern des Geburtsdatums fehlt die Berechtigung teams.change_helper.")
        with transaction.atomic():
            team = serializer.validated_data.get("team", getattr(serializer.instance, "team", None))
            if team is not None:
                team = Team.objects.select_for_update().get(pk=team.pk)
                serializer.validated_data["team"] = team
            helper = self.resolve_helper(serializer)
            helper = Helper.objects.select_for_update().get(pk=helper.pk)
            end_date = serializer.validated_data.get(
                "end_date", getattr(serializer.instance, "end_date", None)
            )
            start_date = serializer.validated_data.get("start_date", getattr(serializer.instance, "start_date", None))
            if team is not None:
                same_team = serializer.instance is not None and serializer.instance.team_id == team.pk
                if team.end_date and (not same_team or end_date is None or end_date > team.end_date):
                    raise ValidationError({"team_id": "Das Team ist archiviert. Es können keine neuen Dienste zugeordnet oder wieder geöffnet werden."})
                overlaps = HelperMission.objects.filter(helper=helper, team__isnull=False).exclude(team=team)
                if serializer.instance is not None:
                    overlaps = overlaps.exclude(pk=serializer.instance.pk)
                overlaps = overlaps.filter(Q(end_date__isnull=True) | Q(end_date__gt=start_date))
                if end_date is not None:
                    overlaps = overlaps.filter(start_date__lt=end_date)
                if overlaps.exists():
                    raise ValidationError({"team_id": "Der Helfer ist in diesem Zeitraum bereits einem anderen Team zugeordnet."})
            if end_date is None:
                self.validate_helper(helper, mission, serializer.instance)
            if birthday_changed:
                helper.birthday = birthday
                helper.save(update_fields=("birthday",))
            serializer.save(mission=mission, helper=helper)

    def perform_create(self, serializer):
        self.save(serializer)

    def perform_update(self, serializer):
        self.save(serializer)


class HelperSearchView(ListAPIView):
    serializer_class = HelperSuggestionSerializer
    permission_classes = (StrictDjangoModelPermissions,)
    pagination_class = None

    def get_queryset(self):
        name = self.request.query_params.get("name", "").strip()
        if len(name) < 2:
            return Helper.objects.none()
        return Helper.objects.filter(name__icontains=name).order_by("name", "birthday", "pk")[:20]


class HelperDeleteView(DestroyAPIView):
    queryset = Helper.objects.all()
    serializer_class = HelperSuggestionSerializer
    permission_classes = (StrictDjangoModelPermissions,)

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("teams.delete_helpermission"):
            raise PermissionDenied("Zum vollständigen Löschen fehlen die Rechte zum Löschen der Dienstzeiten.")
        with transaction.atomic():
            helper = get_object_or_404(Helper.objects.select_for_update(), pk=instance.pk)
            helper.delete()
