from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("teams", "0009_helper_hiorg")]

    operations = [
        migrations.RemoveConstraint(
            model_name="team", name="unique_team_name_per_mission",
        ),
        migrations.AddConstraint(
            model_name="team",
            constraint=models.UniqueConstraint(
                fields=("mission", "name"),
                condition=models.Q(end_date__isnull=True),
                name="unique_active_team_name_per_mission",
            ),
        ),
    ]
