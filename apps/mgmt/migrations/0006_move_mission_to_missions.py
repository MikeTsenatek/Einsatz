from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("mgmt", "0005_priority_enum"),
        ("missions", "0001_initial"),
        ("patients", "0002_move_mission_to_missions"),
        ("teams", "0003_move_mission_to_missions"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[migrations.DeleteModel(name="Mission")],
        ),
    ]
