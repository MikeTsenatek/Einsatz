from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mgmt", "0007_treatment_keyword"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="treatmentkeyword",
            name="category",
        ),
        migrations.AlterModelOptions(
            name="treatmentkeyword",
            options={
                "ordering": ("name",),
                "verbose_name": "Behandlungsstichwort",
                "verbose_name_plural": "Behandlungsstichwörter",
            },
        ),
    ]
