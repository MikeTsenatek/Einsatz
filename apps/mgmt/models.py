from django.db import models


class NamedReferenceModel(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        abstract = True
        ordering = ("pk",)

    def __str__(self):
        return self.name


class AssigningEnum(NamedReferenceModel):
    pass


class LeavingEnum(NamedReferenceModel):
    has_to_be_specified = models.BooleanField(default=False)


class GenderEnum(NamedReferenceModel):
    pass


class PriorityEnum(models.Model):
    level = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ("level",)

    def __str__(self):
        return f"{self.level} {self.name}"


class TreatmentKeyword(models.Model):
    name = models.CharField("Stichwort", max_length=200, unique=True)
    is_active = models.BooleanField("Aktiv", default=True, db_index=True)

    class Meta:
        verbose_name = "Behandlungsstichwort"
        verbose_name_plural = "Behandlungsstichwörter"
        ordering = ("name",)

    def __str__(self):
        return self.name
