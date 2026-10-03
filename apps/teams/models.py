from django.db import models


class Helper(models.Model):
    name = models.CharField(max_length=100)
    birthday = models.DateField(null=True, blank=True)
    hiorg = models.ForeignKey("mgmt.HiOrg", on_delete=models.PROTECT, null=True, blank=True)
    street = models.CharField(max_length=100, null=True, blank=True)
    zip_code = models.CharField(max_length=10, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    missions = models.ManyToManyField(
        "missions.Mission", related_name="helpers", blank=True, through="HelperMission"
    )

    def __str__(self):
        return self.name


class Team(models.Model):
    mission = models.ForeignKey(
        "missions.Mission", on_delete=models.CASCADE, related_name="teams"
    )
    name = models.CharField(max_length=100)
    notes = models.TextField(blank=True, default="")
    end_date = models.DateTimeField(null=True, blank=True)
    planned_end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("name", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("mission", "name"),
                condition=models.Q(end_date__isnull=True),
                name="unique_active_team_name_per_mission"
            ),
        )

    def __str__(self):
        return self.name


class HelperMission(models.Model):
    helper = models.ForeignKey(Helper, on_delete=models.CASCADE)
    mission = models.ForeignKey("missions.Mission", on_delete=models.CASCADE)
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="helper_missions",
    )
    start_date = models.DateTimeField()
    planned_end_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-start_date", "-pk")

    def __str__(self):
        return f"{self.helper} - {self.mission}"
