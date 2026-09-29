import django.db.models.deletion
from django.db import migrations, models


OLD_TO_NEW_PERMISSIONS = {
    "add_etb": ("add_operationlogentry", "Kann Einsatztagebucheintrag hinzufügen"),
    "change_etb": ("change_operationlogentry", "Kann Einsatztagebucheintrag ändern"),
    "view_etb": ("view_operationlogentry", "Kann Einsatztagebucheintrag ansehen"),
}


def rename_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    database = schema_editor.connection.alias
    content_type = ContentType.objects.using(database).filter(
        app_label="missions", model="etb"
    ).first()
    if content_type is None:
        return

    # Content types are normally created by post_migrate, which has not run yet
    # when this migration executes on a fresh database.
    content_type.model = "operationlogentry"
    content_type.save(using=database, update_fields=["model"])

    for old_codename, (new_codename, name) in OLD_TO_NEW_PERMISSIONS.items():
        Permission.objects.using(database).filter(
            content_type=content_type,
            codename=old_codename,
        ).update(codename=new_codename, name=name)

    Permission.objects.using(database).filter(
        content_type=content_type,
        codename__in=("delete_etb", "delete_operationlogentry"),
    ).delete()


def restore_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    database = schema_editor.connection.alias
    content_type = ContentType.objects.using(database).filter(
        app_label="missions", model="operationlogentry"
    ).first()
    if content_type is None:
        return

    for old_codename, (new_codename, _) in OLD_TO_NEW_PERMISSIONS.items():
        Permission.objects.using(database).filter(
            content_type=content_type,
            codename=new_codename,
        ).update(codename=old_codename)

    content_type.model = "etb"
    content_type.save(using=database, update_fields=["model"])


class Migration(migrations.Migration):
    dependencies = [
        ("missions", "0003_alter_etb_options"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ETB",
            new_name="OperationLogEntry",
        ),
        migrations.AlterField(
            model_name="operationlogentry",
            name="mission",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="operation_log_entries",
                to="missions.mission",
                verbose_name="Einsatz",
            ),
        ),
        migrations.AlterField(
            model_name="operationlogentry",
            name="priority",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="operation_log_entries",
                to="mgmt.priorityenum",
                verbose_name="Priorität",
            ),
        ),
        migrations.AlterField(
            model_name="operationlogentry",
            name="sender",
            field=models.CharField(max_length=100, verbose_name="Von"),
        ),
        migrations.AlterField(
            model_name="operationlogentry",
            name="recipient",
            field=models.CharField(max_length=100, verbose_name="An"),
        ),
        migrations.AlterField(
            model_name="operationlogentry",
            name="timestamp",
            field=models.DateTimeField(db_index=True, verbose_name="Zeitpunkt"),
        ),
        migrations.AlterField(
            model_name="operationlogentry",
            name="text",
            field=models.TextField(verbose_name="Meldung"),
        ),
        migrations.AlterModelOptions(
            name="operationlogentry",
            options={
                "default_permissions": ("add", "change", "view"),
                "ordering": ("-timestamp", "-pk"),
                "verbose_name": "Einsatztagebucheintrag",
                "verbose_name_plural": "Einsatztagebucheinträge",
            },
        ),
        migrations.AlterField(
            model_name="mission",
            name="name",
            field=models.CharField(max_length=100, verbose_name="Name"),
        ),
        migrations.AlterField(
            model_name="mission",
            name="state",
            field=models.CharField(
                choices=[
                    ("ACTIVE", "Aktiv"),
                    ("INACTIVE", "Inaktiv"),
                    ("ARCHIVED", "Archiviert"),
                ],
                default="ACTIVE",
                max_length=10,
                verbose_name="Status",
            ),
        ),
        migrations.AlterModelOptions(
            name="mission",
            options={
                "verbose_name": "Einsatz",
                "verbose_name_plural": "Einsätze",
            },
        ),
        migrations.RunPython(rename_permissions, restore_permissions),
    ]
