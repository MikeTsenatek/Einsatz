"""Validate imported RFC 7946 data before it reaches Leaflet."""
import json
import math
from rest_framework import serializers


def feature_coordinate_records(data):
    """Return feature data and coordinate paths relative to each geometry."""
    if data.get('type') == 'FeatureCollection':
        features = data['features']
    elif data.get('type') == 'Feature':
        features = [data]
    else:
        features = [{'type': 'Feature', 'geometry': data, 'properties': {}}]

    result = []

    def positions(value, path, records):
        if value and isinstance(value[0], (int, float)):
            records.append((path, value))
            return
        for index, child in enumerate(value):
            positions(child, path + (index,), records)

    def geometry(value, path, records):
        if value.get('type') == 'GeometryCollection':
            for index, child in enumerate(value['geometries']):
                geometry(child, path + ('geometries', index), records)
        else:
            positions(value['coordinates'], path + ('coordinates',), records)

    for index, feature in enumerate(features):
        records = []
        geometry(feature['geometry'], (), records)
        result.append((index, feature, records))
    return result


def validate_geojson(data):
    count = 0

    def invalid(path, reason):
        raise serializers.ValidationError(f'{path}: {reason}')

    def position(value, path):
        nonlocal count
        count += 1
        if count > 50000:
            invalid(path, 'Maximal 50.000 Koordinaten pro Import erlaubt.')
        if not isinstance(value, list) or len(value) < 2:
            invalid(path, 'Koordinatenpaar [Längengrad, Breitengrad] erwartet.')
        for index, number in enumerate(value):
            if type(number) not in (int, float) or not math.isfinite(number):
                invalid(f'{path}[{index}]', 'Eine endliche Zahl erwartet, kein Text oder null.')
        if not -180 <= value[0] <= 180:
            invalid(f'{path}[0]', f'Längengrad {value[0]} liegt außerhalb von −180 bis 180. WGS84 in Grad erwartet, keine projizierten Meterkoordinaten.')
        if not -90 <= value[1] <= 90:
            invalid(f'{path}[1]', f'Breitengrad {value[1]} liegt außerhalb von −90 bis 90. Reihenfolge: [Längengrad, Breitengrad].')

    def sequence(value, path, minimum, child):
        if not isinstance(value, list):
            invalid(path, 'Eine Liste erwartet.')
        if len(value) < minimum:
            invalid(path, f'Mindestens {minimum} Einträge erwartet; vorhanden: {len(value)}.')
        for index, item in enumerate(value):
            child(item, f'{path}[{index}]')

    def line(value, path):
        sequence(value, path, 2, position)

    def ring(value, path):
        sequence(value, path, 4, position)
        if value[0] != value[-1]:
            invalid(path, 'Polygonring nicht geschlossen: erste und letzte Koordinate müssen übereinstimmen.')

    def polygon(value, path):
        sequence(value, path, 1, ring)

    def geometry(value, path, depth=0):
        if value is None:
            return
        if not isinstance(value, dict):
            invalid(path, 'Ein Geometrie-Objekt erwartet.')
        if depth > 16:
            invalid(path, 'GeometryCollection ist zu tief verschachtelt (maximal 16 Ebenen).')
        kind, coords = value.get('type'), value.get('coordinates')
        coords_path = f'{path}.coordinates'
        if kind == 'GeometryCollection':
            sequence(value.get('geometries'), f'{path}.geometries', 0,
                     lambda g, p: geometry(g, p, depth+1) if g is not None else invalid(p, 'Geometrie darf hier nicht null sein.'))
        elif kind == 'Point':
            position(coords, coords_path)
        elif kind == 'MultiPoint':
            sequence(coords, coords_path, 1, position)
        elif kind == 'LineString':
            line(coords, coords_path)
        elif kind == 'MultiLineString':
            sequence(coords, coords_path, 1, line)
        elif kind == 'Polygon':
            polygon(coords, coords_path)
        elif kind == 'MultiPolygon':
            sequence(coords, coords_path, 1, polygon)
        else:
            invalid(f'{path}.type', f'Unbekannter oder fehlender Geometrietyp: {str(kind)[:80]}.')

    def feature(value, path):
        if not isinstance(value, dict) or value.get('type') != 'Feature':
            invalid(path, 'Ein GeoJSON-Feature mit type="Feature" erwartet.')
        if 'geometry' not in value:
            invalid(f'{path}.geometry', 'Geometrie fehlt.')
        props = value.get('properties')
        if props is not None and not isinstance(props, dict):
            invalid(f'{path}.properties', 'Ein Objekt oder null erwartet.')
        if props and 'popupContent' in props and not isinstance(props['popupContent'], (str, type(None))):
            invalid(f'{path}.properties.popupContent', 'Popup-Inhalt muss Text oder null sein.')
        geometry(value['geometry'], f'{path}.geometry')

    try:
        encoded = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, RecursionError):
        invalid('$', 'Nicht als gültiges JSON darstellbar: unzulässige Werte oder zu tiefe Verschachtelung.')
    if len(encoded) > 1024 * 1024:
        invalid('$', 'GeoJSON darf maximal 1 MB groß sein.')
    if not isinstance(data, dict):
        invalid('$', 'FeatureCollection, Feature oder Geometrie als JSON-Objekt erwartet.')
    if 'crs' in data:
        invalid('$.crs', 'Die Datei enthält eine ältere CRS-Angabe. Erwartet wird GeoJSON in WGS84 (Längengrad/Breitengrad in Grad) ohne crs-Feld. Vor einer Änderung das Koordinatensystem prüfen.')
    if data.get('type') == 'FeatureCollection':
        sequence(data.get('features'), '$.features', 1, feature)
    elif data.get('type') == 'Feature':
        feature(data, '$')
    else:
        geometry(data, '$')
    if not count:
        invalid('$', 'Die Datei enthält keine darstellbaren Geometrien.')
    return data
