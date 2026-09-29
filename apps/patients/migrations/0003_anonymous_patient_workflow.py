import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0002_move_mission_to_missions"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="is_placeholder",
            field=models.BooleanField(
                db_index=True,
                default=False,
                verbose_name="Unbekannter Patient",
            ),
        ),
        migrations.AlterField(
            model_name="patient",
            name="name",
            field=models.CharField(blank=True, max_length=100, verbose_name="Name"),
        ),
        migrations.AlterField(
            model_name="treatment",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="treatments",
                to="patients.patient",
                verbose_name="Patient",
            ),
        ),
    ]
