from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from apps.missions.numbering import MissionNumberedModel


def calculate_age(birthday, today=None):
    today = today or timezone.localdate()
    return today.year - birthday.year - (
        (today.month, today.day) < (birthday.month, birthday.day)
    )


class Patient(MissionNumberedModel):
    counter_field = "patient_number_counter"
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        related_name="patients",
    )
    name = models.CharField(max_length=100)
    birthday = models.DateField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    gender = models.ForeignKey(
        "mgmt.GenderEnum",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    street = models.CharField(max_length=100, null=True, blank=True)
    zip_code = models.CharField(max_length=10, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    history = AuditlogHistoryField(delete_related=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("mission", "number"), name="unique_patient_mission_number")]

    def save(self, *args, **kwargs):
        if self.birthday:
            self.age = calculate_age(self.birthday)
            update_fields = kwargs.get("update_fields")
            if update_fields and "birthday" in update_fields:
                kwargs["update_fields"] = tuple(set(update_fields) | {"age"})
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or f"Unbekannt #{self.pk or 'neu'}"


class Treatment(MissionNumberedModel):
    counter_field = "treatment_number_counter"
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        related_name="treatments",
    )
    patient = models.ForeignKey(
        Patient,
        verbose_name="Patient",
        on_delete=models.PROTECT,
        related_name="treatments",
        null=True,
        blank=True,
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    transported_by_public_ems = models.BooleanField(
        "Abtransport durch öffentlich-rechtlichen Rettungsdienst", default=False,
    )
    discharge_destination = models.CharField("Entlassziel", max_length=200, blank=True, default="")
    keyword = models.CharField(max_length=200, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    treater_text = models.CharField(max_length=100, null=True, blank=True)
    treater_id = models.ForeignKey(
        "teams.Helper",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="treatments_as_treater",
    )
    doctor_text = models.CharField(max_length=100, null=True, blank=True)
    doctor_id = models.ForeignKey(
        "teams.Helper",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="treatments_as_doctor",
    )
    assigning_enum = models.ForeignKey(
        "mgmt.AssigningEnum",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    leaving_enum = models.ForeignKey(
        "mgmt.LeavingEnum",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    leaving_specified = models.CharField(max_length=100, null=True, blank=True)
    external_order_number = models.CharField(max_length=100, null=True, blank=True)
    history = AuditlogHistoryField(delete_related=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("mission", "number"), name="unique_treatment_mission_number",
            ),
        ]

    def clean(self):
        super().clean()
        if self.end_date is not None and not self.discharge_destination.strip():
            raise ValidationError({
                "discharge_destination": "Zum Abschließen einer Behandlung ist ein Entlassziel erforderlich."
            })


    def __str__(self):
        patient = self.patient or "Nicht zugeordnet"
        start_date = self.start_date
        if isinstance(start_date, str):
            start_date = parse_datetime(start_date)
        formatted_start_date = (
            start_date.strftime("%d.%m.%Y %H:%M")
            if hasattr(start_date, "strftime")
            else str(self.start_date)
        )
        return f"{patient} ({formatted_start_date})"


auditlog.register(Patient, serialize_data=True)
auditlog.register(Treatment, serialize_data=True)
