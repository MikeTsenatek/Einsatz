from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mgmt", "0004_alter_mission_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="PriorityEnum",
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
                ("level", models.PositiveSmallIntegerField(unique=True)),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
            options={"ordering": ("level",)},
        ),
    ]
