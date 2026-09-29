from django.db import transaction
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.missions.models import Mission
from config.pagination import StandardResultsSetPagination
from config.permissions import StrictDjangoModelPermissions

from .models import Patient, Treatment
from .serializers import PatientSearchSerializer, PatientSerializer, TreatmentSerializer


class PatientViewSet(ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = (StrictDjangoModelPermissions,)

    def get_queryset(self):
        queryset = (
            Patient.objects.select_related("mission", "gender")
            .annotate(treatment_count=Count("treatments"))
            .order_by("name", "pk")
        )
        mission_id = self.request.query_params.get("mission")
        if mission_id:
            queryset = queryset.filter(mission_id=mission_id)
        return queryset

    @action(detail=False, methods=("get",))
    def search(self, request):
        query = PatientSearchSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        patients = self.filter_queryset(self.get_queryset())
        name = query.validated_data.get("name")
        if name:
            patients = patients.filter(name__icontains=name)
        birthday = query.validated_data.get("birthday")
        if birthday is not None:
            patients = patients.filter(birthday=birthday)
        return Response(self.get_serializer(patients, many=True).data)


    def perform_destroy(self, instance):
        treatments = instance.treatments.all()
        if treatments.exists() and not self.request.user.has_perm("patients.delete_treatment"):
            raise PermissionDenied(
                "Zum Löschen eines Patienten mit Behandlungen fehlt die Berechtigung zum Löschen von Behandlungen."
            )
        with transaction.atomic():
            treatments.delete()
            instance.delete()


class TreatmentViewSet(ModelViewSet):
    serializer_class = TreatmentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = (StrictDjangoModelPermissions,)

    def get_queryset(self):
        return Treatment.objects.filter(
            patient_id=self.kwargs["patient_pk"]
        ).select_related("mission", "patient", "patient__gender").order_by("-start_date", "-pk")

    def get_patient(self):
        return get_object_or_404(Patient, pk=self.kwargs["patient_pk"])

    def perform_create(self, serializer):
        patient = self.get_patient()
        serializer.validated_data.pop("create_new_patient", None)
        serializer.save(patient=patient, mission=patient.mission)

    def perform_update(self, serializer):
        patient = self.get_patient()
        serializer.validated_data.pop("create_new_patient", None)
        serializer.save(patient=patient, mission=patient.mission)


class MissionTreatmentViewSet(ModelViewSet):
    serializer_class = TreatmentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = (StrictDjangoModelPermissions,)

    def get_mission(self):
        return get_object_or_404(Mission, pk=self.kwargs["mission_pk"])

    def get_queryset(self):
        return (
            Treatment.objects.filter(mission_id=self.kwargs["mission_pk"])
            .select_related("mission", "patient", "patient__gender")
            .order_by("-start_date", "-pk")
        )

    def resolve_patient(self, serializer, mission):
        patient_was_supplied = "patient" in serializer.validated_data
        selected_patient = serializer.validated_data.get("patient")
        patient_details = serializer.validated_data.pop("patient_details", None)
        create_new_patient = serializer.validated_data.pop("create_new_patient", False)
        if create_new_patient:
            if not self.request.user.has_perm("patients.add_patient"):
                raise PermissionDenied(
                    "Für das Anlegen eines neuen Patienten fehlt die Berechtigung."
                )
            name = patient_details.pop("name").strip()
            return Patient.objects.create(mission=mission, **patient_details, name=name)
        if selected_patient is not None:
            if selected_patient.mission_id != mission.pk:
                raise ValidationError({"patient": "Der Patient gehört zu einem anderen Einsatz."})
            is_current_patient = (
                serializer.instance is not None
                and serializer.instance.patient_id == selected_patient.pk
            )
            if is_current_patient and patient_details:
                if not self.request.user.has_perm("patients.change_patient"):
                    raise PermissionDenied(
                        "Für die Änderung der Patientendaten fehlt die Berechtigung."
                    )
                selected_patient.name = patient_details.pop("name").strip()
                for field in ("birthday", "age"):
                    if field in patient_details:
                        setattr(selected_patient, field, patient_details[field])
                selected_patient.save(update_fields=("name", "birthday", "age"))
            return selected_patient
        if not patient_details:
            if patient_was_supplied:
                return None
            return getattr(serializer.instance, "patient", None)

        name = patient_details.pop("name").strip()
        birthday = patient_details.get("birthday")
        matches = Patient.objects.select_for_update().filter(
            mission=mission,
            name__iexact=name,
        )
        if birthday is not None:
            existing = matches.filter(birthday=birthday).first()
            if existing:
                return existing
        else:
            count = matches.count()
            if count == 1:
                return matches.first()
            if count > 1:
                raise ValidationError({
                    "patient_details": "Mehrere Patienten mit diesem Namen vorhanden. Bitte Geburtsdatum ergänzen oder einen Vorschlag auswählen."
                })

        if not self.request.user.has_perm("patients.add_patient"):
            raise PermissionDenied(
                "Der Patient ist noch nicht bekannt und darf mit den vorhandenen Berechtigungen nicht angelegt werden."
            )
        return Patient.objects.create(mission=mission, **patient_details, name=name)

    def perform_create(self, serializer):
        mission = self.get_mission()
        with transaction.atomic():
            patient = self.resolve_patient(serializer, mission)
            serializer.save(mission=mission, patient=patient)

    def perform_update(self, serializer):
        mission = self.get_mission()
        with transaction.atomic():
            patient = self.resolve_patient(serializer, mission)
            serializer.save(mission=mission, patient=patient)
