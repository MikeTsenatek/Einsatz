from django.db import migrations, models


def assign_numbers(apps, schema_editor):
    Record = apps.get_model("patients", "Patient")
    Mission = apps.get_model("missions", "Mission")
    database = schema_editor.connection.alias
    for mission in Mission.objects.using(database).all().iterator():
        number = 0
        for record in Record.objects.using(database).filter(mission_id=mission.pk).order_by("pk").iterator():
            number += 1
            Record.objects.using(database).filter(pk=record.pk).update(number=number)
        Mission.objects.using(database).filter(pk=mission.pk).update(patient_number_counter=number)


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0004_remove_placeholder_patients"),
        ("missions", "0006_operation_log_numbers"),
    ]
    operations = [
        migrations.AddField(model_name="patient", name="number", field=models.PositiveIntegerField("Laufende Nummer", editable=False, null=True)),
        migrations.RunPython(assign_numbers, migrations.RunPython.noop),
        migrations.AlterField(model_name="patient", name="number", field=models.PositiveIntegerField("Laufende Nummer", editable=False)),
        migrations.AddConstraint(model_name="patient", constraint=models.UniqueConstraint(fields=("mission", "number"), name="unique_patient_mission_number")),
    ]
