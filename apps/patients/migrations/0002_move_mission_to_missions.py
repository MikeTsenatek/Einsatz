import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("missions", "0001_initial"),
        ("patients", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="patient",
            name="mission",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="patients",
                to="missions.mission",
            ),
        ),
        migrations.AlterField(
            model_name="treatment",
            name="mission",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="treatments",
                to="missions.mission",
            ),
        ),
    ]
