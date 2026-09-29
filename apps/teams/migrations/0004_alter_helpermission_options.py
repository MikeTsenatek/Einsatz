from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("teams", "0003_move_mission_to_missions")]

    operations = [
        migrations.AlterModelOptions(
            name="helpermission",
            options={"ordering": ("-start_date", "-pk")},
        ),
    ]
