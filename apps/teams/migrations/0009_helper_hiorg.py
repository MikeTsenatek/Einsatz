from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("mgmt", "0010_hiorg"), ("teams", "0008_team_end_date")]
    operations = [migrations.AddField(
        model_name="helper", name="hiorg",
        field=models.ForeignKey(to="mgmt.hiorg", on_delete=django.db.models.deletion.PROTECT, null=True, blank=True),
    )]
