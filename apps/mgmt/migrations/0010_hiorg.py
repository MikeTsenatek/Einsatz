from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("mgmt", "0009_dischargedestination")]
    operations = [migrations.CreateModel(
        name="HiOrg",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("hiorg", models.CharField("HiOrg", max_length=200)),
            ("kreisverband", models.CharField("Kreisverband", max_length=200, blank=True)),
            ("gemeinschaft", models.CharField("Gemeinschaft", max_length=200, blank=True)),
            ("gliederung", models.CharField("Gliederung", max_length=200, blank=True)),
        ],
        options={"verbose_name": "HiOrg-Gliederung", "verbose_name_plural": "HiOrg-Gliederungen", "ordering": ("hiorg", "kreisverband", "gemeinschaft", "gliederung", "pk")},
    )]
