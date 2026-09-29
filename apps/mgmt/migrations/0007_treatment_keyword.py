from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mgmt", "0006_move_mission_to_missions"),
    ]

    operations = [
        migrations.CreateModel(
            name="TreatmentKeyword",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("category", models.CharField(db_index=True, max_length=100, verbose_name="Kategorie")),
                ("name", models.CharField(max_length=200, unique=True, verbose_name="Stichwort")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Aktiv")),
            ],
            options={
                "verbose_name": "Behandlungsstichwort",
                "verbose_name_plural": "Behandlungsstichwörter",
                "ordering": ("category", "name"),
            },
        ),
    ]
