from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .numbering import MissionNumberedModel


class Mission(models.Model):
    class State(models.TextChoices):
        ACTIVE = "ACTIVE", _("Aktiv")
        INACTIVE = "INACTIVE", _("Inaktiv")
        ARCHIVED = "ARCHIVED", _("Archiviert")

    name = models.CharField(_("Name"), max_length=100)
    state = models.CharField(
        _("Status"),
        max_length=10,
        choices=State.choices,
        default=State.ACTIVE,
    )
    patient_number_counter = models.PositiveIntegerField(default=0, editable=False)
    operation_log_number_counter = models.PositiveIntegerField(default=0, editable=False)
    history = AuditlogHistoryField(delete_related=False)

    class Meta:
        db_table = "mgmt_mission"
        verbose_name = _("Einsatz")
        verbose_name_plural = _("Einsätze")

    def __str__(self):
        return self.name


class OperationLogEntryQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError(_("Einsatztagebuch-Einträge dürfen nur gestrichen werden."))

    def update(self, **kwargs):
        raise ValidationError(_("Einsatztagebuch-Einträge müssen einzeln und auditierbar geändert werden."))

    def bulk_create(self, objs, **kwargs):
        raise ValidationError(_("Einsatztagebuch-Einträge müssen einzeln und auditierbar angelegt werden."))

    def bulk_update(self, objs, fields, **kwargs):
        raise ValidationError(_("Einsatztagebuch-Einträge müssen einzeln und auditierbar geändert werden."))


class OperationLogEntry(MissionNumberedModel):
    counter_field = "operation_log_number_counter"
    mission = models.ForeignKey(
        Mission,
        verbose_name=_("Einsatz"),
        on_delete=models.PROTECT,
        related_name="operation_log_entries",
    )
    sender = models.CharField(_("Von"), max_length=100, blank=True)
    recipient = models.CharField(_("An"), max_length=100, blank=True)
    timestamp = models.DateTimeField(_("Zeitpunkt"), db_index=True)
    text = models.TextField(_("Meldung"))
    measure = models.TextField(_("Maßnahme"), blank=True)
    priority = models.ForeignKey(
        "mgmt.PriorityEnum",
        verbose_name=_("Priorität"),
        on_delete=models.PROTECT,
        related_name="operation_log_entries",
    )
    is_struck_out = models.BooleanField(_("Gestrichen"), default=False, db_index=True)
    history = AuditlogHistoryField(delete_related=False)
    objects = OperationLogEntryQuerySet.as_manager()

    class Meta:
        verbose_name = _("Einsatztagebucheintrag")
        verbose_name_plural = _("Einsatztagebucheinträge")
        constraints = [models.UniqueConstraint(fields=("mission", "number"), name="unique_operation_log_mission_number")]
        ordering = ("-timestamp", "-pk")
        default_permissions = ("add", "change", "view")

    def __str__(self):
        return f"{self.timestamp:%d.%m.%Y %H:%M} - {self.sender}"

    def delete(self, using=None, keep_parents=False):
        raise ValidationError(_("Einsatztagebuch-Einträge dürfen nur gestrichen werden."))


auditlog.register(Mission, serialize_data=True)
auditlog.register(OperationLogEntry, serialize_data=True)
