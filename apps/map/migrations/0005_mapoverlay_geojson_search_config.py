from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('map', '0004_geojsonfeature_geojsoncoordinate'),
    ]

    operations = [
        migrations.AddField(
            model_name='mapoverlay',
            name='geojson_search_fields',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='mapoverlay',
            name='geojson_result_fields',
            field=models.JSONField(blank=True, default=list),
        ),
    ]