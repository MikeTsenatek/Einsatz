import base64
import binascii
import math
import re
import xml.etree.ElementTree as ET
from rest_framework import serializers
from .models import GeoJSONCoordinate, GeoJSONFeature, MapOverlay, GeoJSONImport
from .geojson import feature_coordinate_records, validate_geojson


class MapOverlaySerializer(serializers.ModelSerializer):
    control_points = serializers.JSONField(required=False, allow_null=True, default=None)
    geojson_search_fields = serializers.JSONField(required=False, default=list)
    geojson_result_fields = serializers.JSONField(required=False, default=list)
    class Meta:
        model = MapOverlay
        fields = ('name', 'image', 'corners', 'opacity', 'control_points', 'geojson_search_fields', 'geojson_result_fields')

    def validate_image(self, value):
        match = re.fullmatch(r'data:image/(svg\+xml|png|jpeg|gif|webp);base64,([A-Za-z0-9+/=]+)', value)
        if not match or len(value) > 1_400_000:
            raise serializers.ValidationError('SVG, PNG, JPEG, GIF oder WebP bis 1 MB erforderlich.')
        try:
            data = base64.b64decode(match[2], validate=True)
            kind = match[1]
            valid = {'png': data.startswith(b'\x89PNG\r\n\x1a\n'), 'jpeg': data.startswith(b'\xff\xd8\xff'),
                     'gif': data.startswith((b'GIF87a', b'GIF89a')), 'webp': data.startswith(b'RIFF') and data[8:12] == b'WEBP'}
            if kind == 'svg+xml':
                if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
                    raise ValueError()
                valid[kind] = ET.fromstring(data).tag in ('svg', '{http://www.w3.org/2000/svg}svg')
            if not valid.get(kind) or len(data) > 1024 * 1024:
                raise ValueError()
        except (ValueError, binascii.Error, ET.ParseError):
            raise serializers.ValidationError('Ungültige Bilddatei.')
        return value

    def validate_corners(self, value):
        keys = ('topLeft', 'topRight', 'bottomLeft')
        try:
            if not isinstance(value, dict) or set(value) != set(keys):
                raise ValueError()
            points = []
            for key in keys:
                point = value[key]
                if set(point) != {'lat', 'lng'}:
                    raise ValueError()
                lat, lng = point['lat'], point['lng']
                if any(type(n) not in (int, float) or not math.isfinite(n) for n in (lat, lng)):
                    raise ValueError()
                if not (-85 <= lat <= 85 and -180 <= lng <= 180):
                    raise ValueError()
                points.append((math.radians(lng), math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))))
            a, b, c = points
            if abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])) < 1e-14:
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise serializers.ValidationError('Drei unterschiedliche, nicht kollineare Stützpunkte mit gültigen lat/lng-Koordinaten erforderlich (Breite −85 bis 85).')
        return value

    def validate_control_points(self, value):
        # null marks a legacy overlay whose three corners are its control points.
        if value is None:
            return value
        try:
            if not isinstance(value, list):
                raise ValueError()
            for point in value:
                if not isinstance(point, dict) or set(point) != {'x', 'y', 'lat', 'lng'}:
                    raise ValueError()
                if any(type(n) not in (int, float) or not math.isfinite(n) for n in point.values()):
                    raise ValueError()
                if not (0 <= point['x'] <= 1 and 0 <= point['y'] <= 1 and -85 <= point['lat'] <= 85 and -180 <= point['lng'] <= 180):
                    raise ValueError()
            if len(value) == 2:
                a, b = value
                if (a['x'], a['y']) == (b['x'], b['y']) or (a['lat'], a['lng']) == (b['lat'], b['lng']):
                    raise ValueError()
            if len(value) >= 3:
                u = sum(p['x'] for p in value) / len(value)
                v = sum(p['y'] for p in value) / len(value)
                uu = sum((p['x']-u)**2 for p in value)
                vv = sum((p['y']-v)**2 for p in value)
                uv = sum((p['x']-u)*(p['y']-v) for p in value)
                if uu * vv - uv * uv <= 1e-12 * (uu + vv)**2:
                    raise ValueError()
        except (ValueError, TypeError):
            raise serializers.ValidationError('Ungültige Stützpunkte: x/y müssen zwischen 0 und 1 liegen, lat/lng gültig sein; ab drei Punkten dürfen die Bildpunkte nicht alle auf einer Linie liegen.')
        return value

    def validate_opacity(self, value):
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise serializers.ValidationError('Deckkraft muss zwischen 0 und 1 liegen.')
        return value


class GeoJSONImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeoJSONImport
        fields = ('id', 'name', 'data', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_data(self, value):
        return validate_geojson(value)

    def create(self, validated_data):
        instance = super().create(validated_data)
        for feature_index, feature, coordinates in feature_coordinate_records(instance.data):
            feature_record = GeoJSONFeature.objects.create(
                geojson_import=instance,
                feature_index=feature_index,
                identifier=str(feature.get('id', '')),
                properties=feature.get('properties') or {},
                geometry=feature['geometry'],
            )
            GeoJSONCoordinate.objects.bulk_create([
                GeoJSONCoordinate(
                    feature=feature_record,
                    path=list(path),
                    longitude=position[0],
                    latitude=position[1],
                    altitude=position[2] if len(position) > 2 else None,
                )
                for path, position in coordinates
            ])
        return instance
