from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("missions", "0006_operation_log_numbers")]

    operations = [
        migrations.AddField(
            model_name="mission", name="treatment_number_counter",
            field=models.PositiveIntegerField(default=0, editable=False),
        ),
    ]
