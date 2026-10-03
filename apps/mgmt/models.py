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


class DischargeDestination(NamedReferenceModel):
    is_active = models.BooleanField("Aktiv", default=True, db_index=True)

    class Meta:
        verbose_name = "Entlassziel"
        verbose_name_plural = "Entlassziele"
        ordering = ("pk",)


class HiOrg(models.Model):
    hiorg = models.CharField("HiOrg", max_length=200)
    kreisverband = models.CharField("Kreisverband", max_length=200, blank=True)
    gemeinschaft = models.CharField("Gemeinschaft", max_length=200, blank=True)
    gliederung = models.CharField("Gliederung", max_length=200, blank=True)

    class Meta:
        verbose_name = "HiOrg-Gliederung"
        verbose_name_plural = "HiOrg-Gliederungen"
        ordering = ("hiorg", "kreisverband", "gemeinschaft", "gliederung", "pk")

    def __str__(self):
        return " - ".join((self.hiorg, self.kreisverband, self.gemeinschaft, self.gliederung))
