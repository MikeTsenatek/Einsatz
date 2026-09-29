from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("missions", "0004_rename_etb_operation_log_entry"),
    ]

    operations = [
        migrations.AlterField(
            model_name="operationlogentry",
            name="sender",
            field=models.CharField(blank=True, max_length=100, verbose_name="Von"),
        ),
        migrations.AlterField(
            model_name="operationlogentry",
            name="recipient",
            field=models.CharField(blank=True, max_length=100, verbose_name="An"),
        ),
        migrations.AlterField(
            model_name="operationlogentry",
            name="measure",
            field=models.TextField(blank=True, verbose_name="Maßnahme"),
        ),
    ]
