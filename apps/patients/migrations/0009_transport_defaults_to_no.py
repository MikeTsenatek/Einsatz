from django.db import migrations, models


def set_missing_transport_to_no(apps, schema_editor):
    Treatment = apps.get_model("patients", "Treatment")
    Treatment.objects.using(schema_editor.connection.alias).filter(
        transported_by_public_ems__isnull=True,
    ).update(transported_by_public_ems=False)


class Migration(migrations.Migration):
    dependencies = [("patients", "0008_treatment_transported_by_public_ems")]

    operations = [
        migrations.RunPython(set_missing_transport_to_no, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="treatment", name="transported_by_public_ems",
            field=models.BooleanField(
                default=False,
                verbose_name="Abtransport durch öffentlich-rechtlichen Rettungsdienst",
            ),
        ),
    ]
