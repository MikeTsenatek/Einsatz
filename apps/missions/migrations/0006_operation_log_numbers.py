from django.db import migrations, models


def assign_numbers(apps, schema_editor):
    Record = apps.get_model("missions", "OperationLogEntry")
    Mission = apps.get_model("missions", "Mission")
    database = schema_editor.connection.alias
    for mission in Mission.objects.using(database).all().iterator():
        number = 0
        for record in Record.objects.using(database).filter(mission_id=mission.pk).order_by("pk").iterator():
            number += 1
            Record.objects.using(database).filter(pk=record.pk).update(number=number)
        Mission.objects.using(database).filter(pk=mission.pk).update(operation_log_number_counter=number)


class Migration(migrations.Migration):
    dependencies = [
        ("missions", "0005_optional_operation_log_fields"),
    ]
    operations = [
        migrations.AddField(model_name="mission", name="patient_number_counter", field=models.PositiveIntegerField(default=0, editable=False)),
        migrations.AddField(model_name="mission", name="operation_log_number_counter", field=models.PositiveIntegerField(default=0, editable=False)),
        migrations.AddField(model_name="operationlogentry", name="number", field=models.PositiveIntegerField("Laufende Nummer", editable=False, null=True)),
        migrations.RunPython(assign_numbers, migrations.RunPython.noop),
        migrations.AlterField(model_name="operationlogentry", name="number", field=models.PositiveIntegerField("Laufende Nummer", editable=False)),
        migrations.AddConstraint(model_name="operationlogentry", constraint=models.UniqueConstraint(fields=("mission", "number"), name="unique_operation_log_mission_number")),
    ]
