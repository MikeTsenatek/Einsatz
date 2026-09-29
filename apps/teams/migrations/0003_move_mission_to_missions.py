import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("missions", "0001_initial"),
        ("teams", "0002_remove_helper_age"),
    ]

    operations = [
        migrations.AlterField(
            model_name="helper",
            name="missions",
            field=models.ManyToManyField(
                blank=True,
                related_name="helpers",
                through="teams.HelperMission",
                to="missions.mission",
            ),
        ),
        migrations.AlterField(
            model_name="helpermission",
            name="mission",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="missions.mission",
            ),
        ),
    ]
