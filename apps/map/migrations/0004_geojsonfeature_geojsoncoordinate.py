from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('map', '0003_geojsonimport'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeoJSONFeature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_index', models.PositiveIntegerField()),
                ('identifier', models.CharField(blank=True, max_length=255)),
                ('properties', models.JSONField(blank=True, default=dict)),
                ('geometry', models.JSONField(blank=True, default=dict)),
                ('geojson_import', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='features', to='map.geojsonimport')),
            ],
            options={'ordering': ('feature_index', 'pk')},
        ),
        migrations.CreateModel(
            name='GeoJSONCoordinate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.JSONField()),
                ('longitude', models.FloatField()),
                ('latitude', models.FloatField()),
                ('altitude', models.FloatField(blank=True, null=True)),
                ('feature', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='coordinates', to='map.geojsonfeature')),
            ],
            options={'ordering': ('pk',)},
        ),
        migrations.AddConstraint(
            model_name='geojsonfeature',
            constraint=models.UniqueConstraint(fields=('geojson_import', 'feature_index'), name='unique_geojson_feature_index'),
        ),
    ]