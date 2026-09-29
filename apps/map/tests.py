import base64
from copy import deepcopy
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from apps.missions.models import Mission
from .models import MapOverlay


class MissionMapTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username='map-admin', is_staff=True)
        self.viewer = get_user_model().objects.create_user(username='map-viewer')
        self.outsider = get_user_model().objects.create_user(username='map-outsider')
        self.outsider.groups.clear()
        self.mission = Mission.objects.create(name='Einsatz A')
        self.other = Mission.objects.create(name='Einsatz B')
        self.url = f'/api/missions/{self.mission.pk}/map/'
        self.data = {
            'name': 'Gelände.svg',
            'image': 'data:image/svg+xml;base64,' + base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>').decode(),
            'corners': {'topLeft': {'lat': 52.52, 'lng': 13.40}, 'topRight': {'lat': 52.52, 'lng': 13.41}, 'bottomLeft': {'lat': 52.51, 'lng': 13.40}},
            'opacity': 0.85,
            'control_points': None,
            'geojson_search_fields': [],
            'geojson_result_fields': [],
        }

    def test_admin_save_update_and_mission_isolation(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 204)
        self.assertEqual(self.client.put(self.url, self.data, format='json').status_code, 200)
        self.data['opacity'] = 0.4
        self.assertEqual(self.client.put(self.url, self.data, format='json').status_code, 200)
        self.assertEqual(MapOverlay.objects.count(), 1)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(self.url).json(), self.data)
        self.assertEqual(self.client.get(f'/api/missions/{self.other.pk}/map/').status_code, 204)

    def test_access_control(self):
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.put(self.url, self.data, format='json').status_code, 403)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.put(self.url, self.data, format='json').status_code, 403)
        self.assertFalse(MapOverlay.objects.exists())
        self.assertFalse(self.viewer.is_staff)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.put(self.url, self.data, format='json').status_code, 200)

    def test_invalid_corners_do_not_overwrite_saved_map(self):
        self.client.force_authenticate(self.admin)
        self.client.put(self.url, self.data, format='json')
        for invalid in ({}, [], None,
                        {**self.data['corners'], 'topLeft': {'lat': 90, 'lng': 13}},
                        {**self.data['corners'], 'topLeft': {'lat': True, 'lng': 13}},
                        {key: {'lat': 50, 'lng': 10} for key in self.data['corners']},
                        {key: {'lat': 50, 'lng': 10+i} for i, key in enumerate(self.data['corners'])}):
            with self.subTest(corners=invalid):
                data = {**self.data, 'corners': invalid}
                self.assertEqual(self.client.put(self.url, data, format='json').status_code, 400)
        self.assertEqual(self.client.get(self.url).json(), self.data)

    def test_invalid_images_and_opacity(self):
        self.client.force_authenticate(self.admin)
        for field, value in [('image', 'https://example.com/a.svg'), ('image', 'data:image/svg+xml;base64,AAAA'),
                             ('image', 'data:image/png;base64,' + base64.b64encode(b'not an image').decode()),
                             ('image', self.data['image'] + 'A' * 1_400_000), ('opacity', -0.1), ('opacity', 1.1)]:
            with self.subTest(field=field, size=len(str(value))):
                self.assertEqual(self.client.put(self.url, {**self.data, field: value}, format='json').status_code, 400)
        self.assertFalse(MapOverlay.objects.exists())

    def test_raster_and_missing_mission(self):
        self.client.force_authenticate(self.admin)
        data = deepcopy(self.data)
        data['image'] = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a2ioAAAAASUVORK5CYII='
        self.assertEqual(self.client.put(self.url, data, format='json').status_code, 200)
        self.assertEqual(self.client.put('/api/missions/999999/map/', data, format='json').status_code, 404)

    def test_variable_control_points_roundtrip(self):
        self.client.force_authenticate(self.admin)
        points = [
            {'x': 0.1, 'y': 0.1, 'lat': 52.519, 'lng': 13.401},
            {'x': 0.9, 'y': 0.1, 'lat': 52.519, 'lng': 13.409},
            {'x': 0.1, 'y': 0.9, 'lat': 52.511, 'lng': 13.401},
            {'x': 0.9, 'y': 0.9, 'lat': 52.511, 'lng': 13.409},
            {'x': 0.5, 'y': 0.5, 'lat': 52.515, 'lng': 13.405},
        ]
        for count in (0, 1, 2, 3, 4, 5):
            with self.subTest(count=count):
                data = {**self.data, 'control_points': points[:count]}
                self.assertEqual(self.client.put(self.url, data, format='json').status_code, 200)
                self.assertEqual(self.client.get(self.url).json(), data)

    def test_invalid_control_points(self):
        self.client.force_authenticate(self.admin)
        point = {'x': 0.2, 'y': 0.3, 'lat': 52.51, 'lng': 13.4}
        for points in ({}, [None], [dict(point, x=2)], [dict(point, x=True)],
                       [dict(point, lng=200)], [point, point], [point, point, point]):
            with self.subTest(points=points):
                self.assertEqual(self.client.put(self.url, {**self.data, 'control_points': points}, format='json').status_code, 400)

    def test_legacy_payload_without_points(self):
        self.client.force_authenticate(self.admin)
        data = {k: v for k, v in self.data.items() if k != 'control_points'}
        self.assertEqual(self.client.put(self.url, data, format='json').status_code, 200)
        self.assertIsNone(self.client.get(self.url).json()['control_points'])

    def test_geojson_search_configuration_is_persisted(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(self.url, {
            'geojson_search_fields': ['StandnummerohneGruppe'],
            'geojson_result_fields': ['Name'],
        }, format='json').status_code, 404)
        self.client.put(self.url, self.data, format='json')
        response = self.client.patch(self.url, {
            'geojson_search_fields': ['StandnummerohneGruppe'],
            'geojson_result_fields': ['Name'],
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['geojson_search_fields'], ['StandnummerohneGruppe'])
        self.assertEqual(response.data['geojson_result_fields'], ['Name'])


class GeoJSONImportTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username='geo-admin', is_staff=True)
        self.viewer = get_user_model().objects.create_user(username='geo-viewer')
        self.outsider = get_user_model().objects.create_user(username='geo-outsider')
        self.outsider.groups.clear()
        self.mission = Mission.objects.create(name='Geo A')
        self.other = Mission.objects.create(name='Geo B')
        self.url = f'/api/missions/{self.mission.pk}/map/geojson/'
        self.data = {'name': 'plan.geojson', 'data': {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [13.4, 52.5]},
             'properties': {'type': 'RMHP', 'popupContent': '<b>Halteplatz</b>'}},
            {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': [[13.4, 52.5], [13.41, 52.51]]},
             'properties': {'stroke': '#ff0000', 'stroke-width': 6, 'stroke-opacity': 0, 'dashArray': '5, 8'}},
        ]}}

    def test_multiple_imports_without_image_and_mission_isolation(self):
        self.client.force_authenticate(self.admin)
        for _ in range(2):
            response = self.client.post(self.url, self.data, format='json')
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data['data'], self.data['data'])
        self.assertFalse(MapOverlay.objects.exists())
        self.client.force_authenticate(self.viewer)
        self.assertEqual(len(self.client.get(self.url).data), 2)
        self.assertEqual(self.client.get(f'/api/missions/{self.other.pk}/map/geojson/').data, [])

    def test_permissions_and_import_only(self):
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.post(self.url, self.data, format='json').status_code, 403)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(self.url, self.data, format='json').status_code, 201)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.put(self.url, self.data, format='json').status_code, 405)
        self.assertEqual(self.client.patch(self.url, self.data, format='json').status_code, 405)
        self.assertEqual(self.client.delete(self.url).status_code, 405)
        self.assertEqual(self.client.post('/api/missions/999999/map/geojson/', self.data, format='json').status_code, 404)

    def test_invalid_import_does_not_save(self):
        self.client.force_authenticate(self.admin)
        invalid = [None, [], {}, {'type': 'FeatureCollection', 'features': []},
                   {'type': 'FeatureCollection', 'features': [None]},
                   {'type': 'Point', 'coordinates': [200, 52]},
                   {'type': 'Point', 'coordinates': [13, True]},
                   {'type': 'Point', 'coordinates': ['13', 52]},
                   {'type': 'LineString', 'coordinates': [[13, 52]]},
                   {'type': 'Polygon', 'coordinates': [[[13, 52], [14, 52], [14, 53], [13, 53]]]},
                   {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [13, 52]}, 'properties': []},
                   {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [13, 52]}, 'properties': {'popupContent': {}}},
                   {'type': 'Point', 'coordinates': [13, 52], 'padding': 'x' * (1024 * 1024)}]
        for data in invalid:
            with self.subTest(kind=type(data).__name__):
                self.assertEqual(self.client.post(self.url, {'name': 'bad.json', 'data': data}, format='json').status_code, 400)
        self.assertEqual(self.client.get(self.url).data, [])

    def test_geometry_variants(self):
        self.client.force_authenticate(self.admin)
        p = [13, 52]
        ring = [[13, 52], [14, 52], [14, 53], [13, 52]]
        geometries = [
            {'type': 'Point', 'coordinates': p},
            {'type': 'MultiPoint', 'coordinates': [p, [14, 53]]},
            {'type': 'MultiLineString', 'coordinates': [[p, [14, 53]]]},
            {'type': 'Polygon', 'coordinates': [ring]},
            {'type': 'MultiPolygon', 'coordinates': [[ring]]},
            {'type': 'GeometryCollection', 'geometries': [{'type': 'Point', 'coordinates': p}]},
            self.data['data']['features'][0],
        ]
        for geometry in geometries:
            with self.subTest(type=geometry['type']):
                response = self.client.post(self.url, {'name': 'geometry.json', 'data': geometry}, format='json')
                self.assertEqual(response.status_code, 201)


class GeoJSONAdminTests(APITestCase):
    def setUp(self):
        from .models import GeoJSONImport
        self.user = get_user_model().objects.create_superuser(username='geo-super', email='geo@example.com', password='test-password')
        self.mission = Mission.objects.create(name='Admin-Karte')
        self.data = {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'id': 'halteplatz', 'geometry': {'type': 'Point', 'coordinates': [13.4, 52.5, 123]},
             'properties': {'type': 'RMHP', 'popupContent': 'Alt', 'custom': {'keep': True}}},
            {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': [[13, 52], [14, 53]]},
             'properties': {'stroke': 'red'}},
        ]}
        self.record = GeoJSONImport.objects.create(mission=self.mission, name='test.geojson', data=self.data)
        self.url = f'/admin/map/geojsonimport/{self.record.pk}/change/'
        self.client.force_login(self.user)
        self.form = {'name': 'test.geojson', 'point_0_lng': '13.45', 'point_0_lat': '52.55', 'point_0_type': 'LZ', 'point_0_popup': '<b>Neu</b>', '_save': 'Speichern'}

    def test_edit_point_preserves_other_data_and_updates_map_api(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url, self.form).status_code, 302)
        self.record.refresh_from_db()
        point = self.record.data['features'][0]
        self.assertEqual(point['geometry']['coordinates'], [13.45, 52.55, 123])
        self.assertEqual(point['id'], 'halteplatz')
        self.assertEqual(point['properties'], {'type': 'LZ', 'popupContent': '<b>Neu</b>', 'custom': {'keep': True}})
        self.assertEqual(self.record.data['features'][1], self.data['features'][1])
        self.assertEqual(self.client.get(f'/api/missions/{self.mission.pk}/map/geojson/').data[0]['data'], self.record.data)
        self.assertEqual(self.client.get('/admin/map/geojsonimport/add/').status_code, 403)

    def test_invalid_coordinates_do_not_save(self):
        response = self.client.post(self.url, {**self.form, 'point_0_lat': '100'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('point_0_lat', response.context['adminform'].form.errors)
        self.record.refresh_from_db()
        self.assertEqual(self.record.data, self.data)

    def test_read_only_permissions(self):
        from django.contrib.auth.models import Permission
        viewer = get_user_model().objects.create_user(username='geo-readonly', is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(content_type__app_label='map', codename='view_geojsonimport'))
        self.client.force_login(viewer)
        viewer.refresh_from_db()
        viewer.groups.clear()
        self.assertFalse(viewer.has_perm('map.change_geojsonimport'))
        read_response = self.client.get(self.url)
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(read_response.wsgi_request.user.pk, viewer.pk)
        response = self.client.post(self.url, self.form)
        self.assertEqual(response.wsgi_request.user.pk, viewer.pk)
        self.assertFalse(response.wsgi_request.user.has_perm('map.change_geojsonimport'))
        self.assertEqual(response.status_code, 403, response.get('Location'))
        self.record.refresh_from_db()
        self.assertEqual(self.record.data, self.data)

    def test_polygon_coordinates_are_editable_without_geometry_summary(self):
        self.record.data = {'type': 'Feature', 'geometry': {
            'type': 'Polygon',
            'coordinates': [[[13, 52], [14, 52], [14, 53], [13, 52]]],
        }, 'properties': {}}
        self.record.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'point_0_lng')
        self.assertNotContains(response, '4 Koordinaten')

    def test_coordinates_are_grouped_by_feature(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Feature 1 (halteplatz)')
        self.assertContains(response, 'Feature 2')

    def test_edit_polygon_coordinates(self):
        self.record.data = {'type': 'Feature', 'geometry': {
            'type': 'Polygon',
            'coordinates': [[[13, 52, 7], [14, 52], [14, 53], [13, 52, 7]]],
        }, 'properties': {}}
        self.record.save()
        form = {**self.form, 'point_0_lng': '13.1', 'point_0_lat': '52.1',
            'point_3_lng': '13.1', 'point_3_lat': '52.1'}
        self.assertEqual(self.client.post(self.url, form).status_code, 302)
        self.record.refresh_from_db()
        self.assertEqual(self.record.data['geometry']['coordinates'][0][0], [13.1, 52.1, 7])
        self.assertEqual(self.record.data['geometry']['coordinates'][0][1], [14, 52])
        self.assertEqual(self.record.data['geometry']['coordinates'][0][3], [13.1, 52.1, 7])

    def test_multipoint_properties_are_shared_and_altitudes_preserved(self):
        self.record.data = {'type': 'Feature', 'geometry': {'type': 'MultiPoint', 'coordinates': [[13, 52, 3], [14, 53, 4]]}, 'properties': {'type': 'LZ'}}
        self.record.save()
        form = {**self.form, 'point_1_lng': '14.1', 'point_1_lat': '53.1'}
        self.assertEqual(self.client.post(self.url, form).status_code, 302)
        self.record.refresh_from_db()
        self.assertEqual(self.record.data['geometry']['coordinates'], [[13.45, 52.55, 3], [14.1, 53.1, 4]])
        self.assertEqual(self.record.data['properties']['popupContent'], '<b>Neu</b>')


class GeoJSONDiagnosticTests(APITestCase):
    def test_error_identifies_feature_coordinate_and_reason(self):
        from .geojson import validate_geojson
        from rest_framework.exceptions import ValidationError
        data = {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [13, 52]}, 'properties': {}},
            {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [400000, 52]}, 'properties': {}},
        ]}
        with self.assertRaises(ValidationError) as caught:
            validate_geojson(data)
        message = str(caught.exception.detail)
        self.assertIn('$.features[1].geometry.coordinates[0]', message)
        self.assertIn('Längengrad 400000', message)

    def test_errors_distinguish_ring_crs_and_bad_property(self):
        from .geojson import validate_geojson
        from rest_framework.exceptions import ValidationError
        examples = [
            ({'type': 'Point', 'coordinates': [13, 52], 'crs': {}}, '$.crs', 'CRS'),
            ({'type': 'Polygon', 'coordinates': [[[13, 52], [14, 52], [14, 53], [13, 53]]]}, '$.coordinates[0]', 'nicht geschlossen'),
            ({'type': 'Feature', 'geometry': None, 'properties': []}, '$.properties', 'Objekt'),
            ({'type': 'Point', 'coordinates': ['13', 52]}, '$.coordinates[0]', 'Zahl'),
        ]
        for data, path, reason in examples:
            with self.subTest(path=path):
                with self.assertRaises(ValidationError) as caught:
                    validate_geojson(data)
                self.assertIn(path, str(caught.exception.detail))
                self.assertIn(reason, str(caught.exception.detail))
