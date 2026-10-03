from datetime import date

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.missions.models import Mission

from .admin import PatientAdmin, TreatmentInline
from .models import Patient, Treatment, calculate_age


class PatientAdminTests(SimpleTestCase):
    def test_treatment_is_only_available_as_patient_inline(self):
        self.assertTrue(admin.site.is_registered(Patient))
        self.assertFalse(admin.site.is_registered(Treatment))
        self.assertIn(TreatmentInline, PatientAdmin.inlines)

    def test_treatment_inline_inherits_mission_from_patient(self):
        self.assertIn("mission", TreatmentInline.exclude)


class PermissionTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="dispatcher")
        self.user.groups.clear()
        self.client.force_authenticate(self.user)
        self.mission = Mission.objects.create(name="Testmission")
        self.patient = Patient.objects.create(
            mission=self.mission,
            name="Anna Beispiel",
            birthday=date(1990, 5, 12),
        )

    def grant(self, codename):
        permission = Permission.objects.get(
            content_type__app_label="patients",
            codename=codename,
        )
        self.user.user_permissions.add(permission)
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)


class PatientAgeTests(SimpleTestCase):
    def test_age_is_calculated_around_birthday(self):
        self.assertEqual(calculate_age(date(2000, 8, 22), date(2026, 8, 22)), 26)
        self.assertEqual(calculate_age(date(2000, 8, 23), date(2026, 8, 22)), 25)


class PatientApiTests(PermissionTestCase):
    def test_search_requires_view_permission_and_filters_name_and_birthday(self):
        Patient.objects.create(
            mission=self.mission,
            name="Anna Anders",
            birthday=date(1992, 8, 20),
        )
        search_url = reverse("patient-search")

        self.assertEqual(
            self.client.get(search_url, {"name": "anna"}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.grant("view_patient")

        by_name = self.client.get(search_url, {"name": "anna"})
        self.assertEqual(by_name.status_code, status.HTTP_200_OK)
        self.assertEqual(len(by_name.data), 2)

        by_name_and_birthday = self.client.get(
            search_url,
            {"name": "anna", "birthday": "1990-05-12"},
        )
        self.assertEqual(by_name_and_birthday.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [patient["id"] for patient in by_name_and_birthday.data],
            [self.patient.pk],
        )

        self.assertEqual(
            self.client.get(search_url).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_patient_crud_uses_standard_model_permissions(self):
        list_url = reverse("patient-list")
        detail_url = reverse("patient-detail", args=(self.patient.pk,))

        denied = self.client.get(list_url)
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("patients.view_patient", denied.data["detail"])
        self.grant("view_patient")
        self.assertEqual(self.client.get(list_url).status_code, status.HTTP_200_OK)

        payload = {"mission": self.mission.pk, "name": "Neuer Patient"}
        self.assertEqual(
            self.client.post(list_url, payload).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.grant("add_patient")
        self.assertEqual(
            self.client.post(list_url, payload).status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            self.client.patch(detail_url, {"city": "Berlin"}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.grant("change_patient")
        self.assertEqual(
            self.client.patch(detail_url, {"city": "Berlin"}).status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.grant("delete_patient")
        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_204_NO_CONTENT,
        )


class TreatmentApiTests(PermissionTestCase):
    def test_nested_treatment_crud_uses_standard_model_permissions(self):
        list_url = reverse("patient-treatment-list", args=(self.patient.pk,))

        self.assertEqual(self.client.get(list_url).status_code, status.HTTP_403_FORBIDDEN)
        self.grant("view_treatment")
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

        payload = {"start_date": "2026-08-22T10:00:00Z", "keyword": "Sturz"}
        self.assertEqual(
            self.client.post(list_url, payload).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.grant("add_treatment")
        create_response = self.client.post(list_url, payload)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["patient"]["id"], self.patient.pk)
        self.assertEqual(create_response.data["mission"], self.mission.pk)

        detail_url = reverse(
            "patient-treatment-detail",
            args=(self.patient.pk, create_response.data["id"]),
        )
        self.assertEqual(
            self.client.patch(detail_url, {"keyword": "Kontrolle"}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.grant("change_treatment")
        self.assertEqual(
            self.client.patch(detail_url, {"keyword": "Kontrolle"}).status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.grant("delete_treatment")
        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_204_NO_CONTENT,
        )


class UnassignedTreatmentWorkflowTests(PermissionTestCase):
    def test_treatment_can_be_created_without_patient_and_assigned_later(self):
        self.grant("add_treatment")
        list_url = reverse("mission-treatment-list", args=(self.mission.pk,))
        created = self.client.post(
            list_url,
            {"start_date": "2026-08-22T10:00:00Z", "keyword": "Unbekannte Person"},
            format="json",
        )

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(created.data["patient"])

        self.grant("change_treatment")
        detail_url = reverse(
            "mission-treatment-detail",
            args=(self.mission.pk, created.data["id"]),
        )
        assigned = self.client.patch(
            detail_url,
            {"patient": self.patient.pk, "keyword": "Korrigiertes Stichwort"},
            format="json",
        )

        self.assertEqual(assigned.status_code, status.HTTP_200_OK)
        self.assertEqual(assigned.data["patient"]["id"], self.patient.pk)
        self.assertEqual(assigned.data["keyword"], "Korrigiertes Stichwort")

    def test_unique_existing_patient_is_linked_by_name(self):
        self.grant("add_treatment")
        response = self.client.post(
            reverse("mission-treatment-list", args=(self.mission.pk,)),
            {
                "start_date": "2026-08-22T10:00:00Z",
                "patient_details": {"name": "anna beispiel"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["patient"]["id"], self.patient.pk)
        self.assertEqual(Patient.objects.filter(mission=self.mission).count(), 1)

    def test_same_name_with_different_birthday_creates_new_patient(self):
        self.grant("add_treatment")
        self.grant("add_patient")
        response = self.client.post(
            reverse("mission-treatment-list", args=(self.mission.pk,)),
            {
                "start_date": "2026-08-22T10:00:00Z",
                "patient_details": {
                    "name": "Anna Beispiel",
                    "birthday": "2001-06-15",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response.data["patient"]["id"], self.patient.pk)
        self.assertTrue(
            Patient.objects.filter(
                mission=self.mission,
                name="Anna Beispiel",
                birthday="2001-06-15",
            ).exists()
        )

    def test_ambiguous_name_requires_birthday_or_explicit_selection(self):
        Patient.objects.create(mission=self.mission, name="Anna Beispiel")
        self.grant("add_treatment")
        self.grant("add_patient")

        response = self.client.post(
            reverse("mission-treatment-list", args=(self.mission.pk,)),
            {
                "start_date": "2026-08-22T10:00:00Z",
                "patient_details": {"name": "Anna Beispiel"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Treatment.objects.filter(mission=self.mission).count(), 0)

    def test_editing_linked_patient_updates_patient_data(self):
        treatment = Treatment.objects.create(
            mission=self.mission,
            patient=self.patient,
            start_date="2026-08-22T10:00:00Z",
        )
        self.grant("change_treatment")
        self.grant("change_patient")

        response = self.client.patch(
            reverse(
                "mission-treatment-detail",
                args=(self.mission.pk, treatment.pk),
            ),
            {
                "patient": self.patient.pk,
                "patient_details": {
                    "name": "Anna Korrigiert",
                    "birthday": "1990-05-13",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.name, "Anna Korrigiert")
        self.assertEqual(self.patient.birthday, date(1990, 5, 13))
        self.assertEqual(response.data["patient"]["id"], self.patient.pk)

    def test_explicit_new_patient_does_not_update_or_reuse_linked_patient(self):
        treatment = Treatment.objects.create(
            mission=self.mission, patient=self.patient, start_date="2026-08-22T10:00:00Z"
        )
        self.grant("change_treatment")
        self.grant("add_patient")

        response = self.client.patch(
            reverse("mission-treatment-detail", args=(self.mission.pk, treatment.pk)),
            {
                "patient": None,
                "patient_details": {
                    "name": "Anna Beispiel",
                    "birthday": "1990-05-12",
                },
                "create_new_patient": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data["patient"]["id"], self.patient.pk)
        self.assertEqual(Patient.objects.filter(mission=self.mission).count(), 2)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.name, "Anna Beispiel")

    def test_treatment_requires_patient_before_completion(self):
        self.grant("add_treatment")
        self.grant("change_treatment")
        created = self.client.post(
            reverse("mission-treatment-list", args=(self.mission.pk,)),
            {"start_date": "2026-08-22T10:00:00Z"},
            format="json",
        )
        detail_url = reverse(
            "mission-treatment-detail",
            args=(self.mission.pk, created.data["id"]),
        )

        rejected = self.client.patch(
            detail_url,
            {"end_date": "2026-08-22T11:00:00Z"},
            format="json",
        )
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)

        completed = self.client.patch(
            detail_url,
            {
                "patient": self.patient.pk,
                "keyword": "Versorgung",
                "discharge_destination": "Nach Hause", "transported_by_public_ems": False,
                "end_date": "2026-08-22T11:00:00Z",
            },
            format="json",
        )
        self.assertEqual(completed.status_code, status.HTTP_200_OK)
        self.assertEqual(completed.data["patient"]["id"], self.patient.pk)
        self.assertIsNotNone(completed.data["end_date"])

    def test_treatment_requires_keyword_before_completion(self):
        treatment = Treatment.objects.create(
            mission=self.mission, patient=self.patient, start_date="2026-08-22T10:00:00Z"
        )
        self.grant("change_treatment")

        response = self.client.patch(
            reverse("mission-treatment-detail", args=(self.mission.pk, treatment.pk)),
            {"end_date": "2026-08-22T11:00:00Z"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("keyword", response.data)

    def test_deleting_patient_requires_treatment_delete_permission_and_cascades(self):
        Treatment.objects.create(
            mission=self.mission, patient=self.patient, start_date="2026-08-22T10:00:00Z"
        )
        self.grant("delete_patient")
        detail_url = reverse("patient-detail", args=(self.patient.pk,))

        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_403_FORBIDDEN)
        self.grant("delete_treatment")
        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(pk=self.patient.pk).exists())
        self.assertEqual(Treatment.objects.filter(mission=self.mission).count(), 0)

    def test_treatment_end_cannot_precede_start(self):
        self.grant("add_treatment")
        response = self.client.post(
            reverse("mission-treatment-list", args=(self.mission.pk,)),
            {
                "patient": self.patient.pk,
                "start_date": "2026-08-22T11:00:00Z",
                "end_date": "2026-08-22T10:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DischargeDestinationTreatmentTests(PermissionTestCase):
    def setUp(self):
        super().setUp()
        self.grant("change_treatment")
        self.grant("add_treatment")
        self.treatment = Treatment.objects.create(
            mission=self.mission, patient=self.patient,
            start_date="2026-08-22T10:00:00Z", keyword="Versorgung",
        )
        self.url = reverse("mission-treatment-detail", args=(self.mission.pk, self.treatment.pk))

    def test_completion_requires_nonempty_destination(self):
        for destination in (None, "", "   "):
            with self.subTest(destination=destination):
                payload = {"end_date": "2026-08-22T11:00:00Z"}
                if destination is not None:
                    payload["discharge_destination"] = destination
                response = self.client.patch(self.url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("discharge_destination", response.data)
                self.treatment.refresh_from_db()
                self.assertIsNone(self.treatment.end_date)

    def test_completion_accepts_suggestions_and_custom_text(self):
        for destination in ("Zurück zur Veranstaltung", "Nach Hause", "Krankenhaus", "Abholung durch Angehörige am Nordtor"):
            with self.subTest(destination=destination):
                response = self.client.patch(self.url, {
                    "end_date": "2026-08-22T11:00:00Z",
                    "discharge_destination": destination, "transported_by_public_ems": False,
                }, format="json")
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["discharge_destination"], destination)
                self.treatment.refresh_from_db()
                self.assertEqual(self.treatment.discharge_destination, destination)

    def test_saved_destination_is_used_for_completion_and_cannot_be_cleared_afterwards(self):
        saved = self.client.patch(self.url, {"discharge_destination": "Nach Hause", "transported_by_public_ems": False}, format="json")
        self.assertEqual(saved.status_code, status.HTTP_200_OK)
        completed = self.client.patch(self.url, {"end_date": "2026-08-22T11:00:00Z"}, format="json")
        self.assertEqual(completed.status_code, status.HTTP_200_OK)
        rejected = self.client.patch(self.url, {"discharge_destination": ""}, format="json")
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)
        self.treatment.refresh_from_db()
        self.assertEqual(self.treatment.discharge_destination, "Nach Hause")
        updated = self.client.patch(self.url, {"notes": "Nachtrag"}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK)

    def test_completed_creation_requires_destination_for_both_routes(self):
        for route, key in [("mission-treatment-list", self.mission.pk), ("patient-treatment-list", self.patient.pk)]:
            with self.subTest(route=route):
                payload = {
                    "patient": self.patient.pk, "keyword": "Versorgung",
                    "start_date": "2026-08-22T10:00:00Z", "end_date": "2026-08-22T11:00:00Z",
                }
                response = self.client.post(reverse(route, args=(key,)), payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("discharge_destination", response.data)
                payload["discharge_destination"] = "Krankenhaus"
                payload["transported_by_public_ems"] = False
                response = self.client.post(reverse(route, args=(key,)), payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.data["discharge_destination"], "Krankenhaus")

    def test_admin_validation_requires_destination(self):
        from django.core.exceptions import ValidationError
        from django.utils.dateparse import parse_datetime
        self.treatment.end_date = parse_datetime("2026-08-22T11:00:00Z")
        with self.assertRaises(ValidationError) as error:
            self.treatment.clean()
        self.assertIn("discharge_destination", error.exception.message_dict)
        self.treatment.discharge_destination = "Nach Hause"
        self.treatment.transported_by_public_ems = False
        self.treatment.clean()


class PublicEmsTransportTests(PermissionTestCase):
    def setUp(self):
        super().setUp()
        self.grant("change_treatment")
        self.treatment = Treatment.objects.create(mission=self.mission, patient=self.patient, start_date="2026-08-22T10:00:00Z", keyword="Versorgung")
        self.url = reverse("mission-treatment-detail", args=(self.mission.pk, self.treatment.pk))
        self.payload = {"end_date": "2026-08-22T11:00:00Z", "discharge_destination": "Krankenhaus"}

    def test_transport_defaults_to_no_and_completion_needs_no_explicit_answer(self):
        self.assertIs(self.treatment.transported_by_public_ems, False)
        response = self.client.patch(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIs(response.data["transported_by_public_ems"], False)
        self.treatment.refresh_from_db()
        self.assertIsNotNone(self.treatment.end_date)
        self.assertIs(self.treatment.transported_by_public_ems, False)

    def test_yes_and_no_are_saved_and_can_be_corrected(self):
        for answer in (True, False):
            response = self.client.patch(self.url, {**self.payload, "transported_by_public_ems": answer}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIs(response.data["transported_by_public_ems"], answer)
            self.treatment.refresh_from_db()
            self.assertIs(self.treatment.transported_by_public_ems, answer)
        response = self.client.patch(self.url, {"notes": "Nachtrag"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.patch(self.url, {"transported_by_public_ems": None}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
