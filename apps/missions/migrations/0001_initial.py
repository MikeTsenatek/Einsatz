import django.db.models.deletion
from django.db import migrations, models


def move_mission_content_type(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.using(schema_editor.connection.alias).filter(app_label="mgmt", model="mission").update(
        app_label="missions"
    )


def restore_mission_content_type(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.using(schema_editor.connection.alias).filter(app_label="missions", model="mission").update(
        app_label="mgmt"
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("mgmt", "0005_priority_enum"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Mission",
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
                        ("name", models.CharField(max_length=100)),
                        (
                            "state",
                            models.CharField(
                                choices=[
                                    ("ACTIVE", "Aktiv"),
                                    ("INACTIVE", "Inaktiv"),
                                    ("ARCHIVED", "Archiviert"),
                                ],
                                default="ACTIVE",
                                max_length=10,
                            ),
                        ),
                    ],
                    options={"db_table": "mgmt_mission"},
                ),
            ],
        ),
        migrations.RunPython(
            move_mission_content_type,
            restore_mission_content_type,
        ),
        migrations.CreateModel(
            name="ETB",
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
                ("sender", models.CharField(max_length=100, verbose_name="Von")),
                ("recipient", models.CharField(max_length=100, verbose_name="An")),
                (
                    "timestamp",
                    models.DateTimeField(db_index=True, verbose_name="Uhrzeit"),
                ),
                ("text", models.TextField()),
                ("measure", models.TextField(verbose_name="Maßnahme")),
                (
                    "mission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="etb_entries",
                        to="missions.mission",
                    ),
                ),
                (
                    "priority",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="etb_entries",
                        to="mgmt.priorityenum",
                    ),
                ),
            ],
            options={
                "verbose_name": "Einsatztagebucheintrag",
                "verbose_name_plural": "Einsatztagebucheinträge",
                "ordering": ("-timestamp", "-pk"),
            },
        ),
    ]
