from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from apps.mgmt.models import PriorityEnum
from apps.patients.models import Patient, Treatment
from apps.patients.serializers import PatientSerializer, TreatmentPatientSerializer, TreatmentSerializer
from .models import Mission, OperationLogEntry
from .serializers import OperationLogEntrySerializer


class MissionNumberingTests(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name="Einsatz A")
        self.other = Mission.objects.create(name="Einsatz B")
        self.priority = PriorityEnum.objects.create(level=1, name="Hoch")

    def entry(self, mission=None):
        return OperationLogEntry.objects.create(
            mission=mission or self.mission, timestamp=timezone.now(),
            text="Meldung", priority=self.priority,
        )

    def treatment(self, mission=None, patient=None):
        return Treatment.objects.create(mission=mission or self.mission, patient=patient, start_date=timezone.now())

    def test_separate_sequences_per_mission_and_record_type(self):
        first = Patient.objects.create(mission=self.mission, name="A")
        second = Patient.objects.create(mission=self.mission, name="B")
        other = Patient.objects.create(mission=self.other, name="C")
        self.assertEqual([first.number, second.number, other.number], [1, 2, 1])
        self.assertEqual([self.entry().number, self.entry().number, self.entry(self.other).number], [1, 2, 1])
        self.assertEqual([self.treatment(patient=first).number, self.treatment(patient=first).number, self.treatment(self.other).number], [1, 2, 1])

    def test_deleted_patient_number_is_not_reused(self):
        patient = Patient.objects.create(mission=self.mission, name="A")
        patient.delete()
        self.assertEqual(Patient.objects.create(mission=self.mission, name="B").number, 2)

    def test_changes_and_striking_preserve_numbers(self):
        patient = Patient.objects.create(mission=self.mission, name="A")
        patient.name = "Korrigiert"
        patient.save(update_fields=["name"])
        entry = self.entry()
        entry.is_struck_out = True
        entry.save(update_fields=["is_struck_out"])
        patient.refresh_from_db()
        entry.refresh_from_db()
        self.assertEqual((patient.number, entry.number, self.entry().number), (1, 1, 2))

    def test_number_and_mission_cannot_be_changed(self):
        for record in [Patient.objects.create(mission=self.mission, name="A"), self.entry(), self.treatment()]:
            record.number = 99
            with self.assertRaises(ValidationError):
                record.save()
            record.refresh_from_db()
            record.mission = self.other
            with self.assertRaises(ValidationError):
                record.save()

    def test_counter_rolls_back_with_record(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.entry()
                raise RuntimeError("rollback")
        self.assertEqual(self.entry().number, 1)

    def test_api_numbers_are_exposed_and_read_only(self):
        patient = Patient.objects.create(mission=self.mission, name="A")
        entry = self.entry()
        for serializer_type, record in [(PatientSerializer, patient), (TreatmentPatientSerializer, patient), (OperationLogEntrySerializer, entry), (TreatmentSerializer, self.treatment())]:
            self.assertEqual(serializer_type(record).data["number"], 1)
            serializer = serializer_type(record, data={"number": 99}, partial=True)
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertNotIn("number", serializer.validated_data)
        serializer = PatientSerializer(patient, data={"mission": self.other.pk}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("mission", serializer.errors)

    def test_treatment_numbers_survive_assignment_completion_and_deletion(self):
        patient = Patient.objects.create(mission=self.mission, name="Patient")
        treatment = self.treatment()
        treatment.patient = patient
        treatment.save(update_fields=["patient"])
        treatment.keyword = "Versorgung"
        treatment.end_date = timezone.now()
        treatment.discharge_destination = "Nach Hause"
        treatment.save(update_fields=["keyword", "end_date", "discharge_destination"])
        treatment.refresh_from_db()
        self.assertEqual(treatment.number, 1)
        treatment.delete()
        self.assertEqual(self.treatment(patient=patient).number, 2)
        patient.treatments.all().delete()
        patient.delete()
        self.assertEqual(self.treatment().number, 3)

    def test_treatment_counter_rolls_back_with_record(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.treatment()
                raise RuntimeError("rollback")
        self.assertEqual(self.treatment().number, 1)
