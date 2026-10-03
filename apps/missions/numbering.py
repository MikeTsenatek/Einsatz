from django.core.exceptions import ValidationError
from django.db import models, router, transaction
from django.db.models import F


class MissionNumberedModel(models.Model):
    number = models.PositiveIntegerField("Laufende Nummer", editable=False)
    counter_field = None

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from .models import Mission

        database = kwargs.get("using") or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=database):
            if self._state.adding:
                missions = Mission.objects.using(database).filter(pk=self.mission_id)
                # Updating the counter locks the mission until the record is saved.
                if not missions.update(**{self.counter_field: F(self.counter_field) + 1}):
                    raise ValidationError("Ein gültiger Einsatz ist erforderlich.")
                self.number = missions.values_list(self.counter_field, flat=True).get()
            else:
                original = type(self).objects.using(database).get(pk=self.pk)
                if (self.mission_id, self.number) != (original.mission_id, original.number):
                    raise ValidationError("Einsatz und laufende Nummer dürfen nicht geändert werden.")
            super().save(*args, **kwargs)
