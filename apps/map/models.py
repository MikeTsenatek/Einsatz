from django.db import models


class MapOverlay(models.Model):
    mission = models.OneToOneField('missions.Mission', on_delete=models.CASCADE, related_name='map_overlay')
    name = models.CharField(max_length=255)
    image = models.TextField()
    corners = models.JSONField()
    control_points = models.JSONField(null=True, blank=True, default=None)
    opacity = models.FloatField(default=0.85)
    geojson_search_fields = models.JSONField(default=list, blank=True)
    geojson_result_fields = models.JSONField(default=list, blank=True)


class GeoJSONImport(models.Model):
    mission = models.ForeignKey('missions.Mission', on_delete=models.CASCADE, related_name='geojson_imports')
    name = models.CharField(max_length=255)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GeoJSONFeature(models.Model):
    geojson_import = models.ForeignKey(GeoJSONImport, on_delete=models.CASCADE, related_name='features')
    feature_index = models.PositiveIntegerField()
    identifier = models.CharField(max_length=255, blank=True)
    properties = models.JSONField(default=dict, blank=True)
    geometry = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ('feature_index', 'pk')
        constraints = [
            models.UniqueConstraint(fields=('geojson_import', 'feature_index'), name='unique_geojson_feature_index'),
        ]

    def __str__(self):
        return self.identifier or f'Feature {self.feature_index + 1}'


class GeoJSONCoordinate(models.Model):
    feature = models.ForeignKey(GeoJSONFeature, on_delete=models.CASCADE, related_name='coordinates')
    path = models.JSONField()
    longitude = models.FloatField()
    latitude = models.FloatField()
    altitude = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ('pk',)

    def __str__(self):
        return f'{self.longitude}, {self.latitude}'
