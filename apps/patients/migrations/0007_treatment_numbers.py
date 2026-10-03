from django.db import migrations, models


def assign_numbers(apps, schema_editor):
    Treatment = apps.get_model("patients", "Treatment")
    Mission = apps.get_model("missions", "Mission")
    database = schema_editor.connection.alias
    for mission in Mission.objects.using(database).all().iterator():
        number = 0
        treatments = Treatment.objects.using(database).filter(mission_id=mission.pk).order_by("pk")
        for treatment in treatments.iterator():
            number += 1
            Treatment.objects.using(database).filter(pk=treatment.pk).update(number=number)
        Mission.objects.using(database).filter(pk=mission.pk).update(treatment_number_counter=number)


class Migration(migrations.Migration):
    dependencies = [
        ("missions", "0007_treatment_number_counter"),
        ("patients", "0006_treatment_discharge_destination"),
    ]

    operations = [
        migrations.AddField(
            model_name="treatment", name="number",
            field=models.PositiveIntegerField("Laufende Nummer", editable=False, null=True),
        ),
        migrations.RunPython(assign_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="treatment", name="number",
            field=models.PositiveIntegerField("Laufende Nummer", editable=False),
        ),
        migrations.AddConstraint(
            model_name="treatment",
            constraint=models.UniqueConstraint(fields=("mission", "number"), name="unique_treatment_mission_number"),
        ),
    ]
