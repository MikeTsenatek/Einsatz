from django.db import migrations, models


def remove_placeholder_patients(apps, schema_editor):
    Patient = apps.get_model("patients", "Patient")
    Treatment = apps.get_model("patients", "Treatment")
    database = schema_editor.connection.alias

    placeholders = Patient.objects.using(database).filter(is_placeholder=True)
    Treatment.objects.using(database).filter(patient__in=placeholders).update(patient=None)
    placeholders.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0003_anonymous_patient_workflow"),
    ]

    operations = [
        migrations.RunPython(remove_placeholder_patients, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="patient",
            name="is_placeholder",
        ),
        migrations.AlterField(
            model_name="patient",
            name="name",
            field=models.CharField(max_length=100),
        ),
    ]
