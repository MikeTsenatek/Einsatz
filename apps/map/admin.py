from copy import deepcopy

from django import forms
from django.contrib import admin
from rest_framework.exceptions import ValidationError

from .geojson import feature_coordinate_records, validate_geojson
from .models import GeoJSONCoordinate, GeoJSONFeature, GeoJSONImport


def at_path(data, path):
    for key in path:
        data = data[key]
    return data


def set_at_path(data, path, value):
    owner = at_path(data, path[:-1])
    index = path[-1]
    if isinstance(owner, list) and index == len(owner):
        owner.append(value)
    else:
        owner[index] = value


def sync_feature_rows(geojson_import):
    """Create editable rows lazily for imports created before normalization."""
    if geojson_import.features.exists():
        return
    for feature_index, feature, coordinates in feature_coordinate_records(geojson_import.data):
        feature_row = GeoJSONFeature.objects.create(
            geojson_import=geojson_import,
            feature_index=feature_index,
            identifier=str(feature.get('id', '')),
            properties=feature.get('properties') or {},
            geometry=deepcopy(feature['geometry']),
        )
        GeoJSONCoordinate.objects.bulk_create([
            GeoJSONCoordinate(
                feature=feature_row,
                path=list(path),
                longitude=position[0],
                latitude=position[1],
                altitude=position[2] if len(position) > 2 else None,
            )
            for path, position in coordinates
        ])


def feature_groups(geojson_import):
    """Yield each feature's coordinates with stable form-field indexes."""
    point_index = 0
    for feature_index, feature, coordinates in feature_coordinate_records(geojson_import.data):
        points = []
        for path, position in coordinates:
            points.append((point_index, path, position))
            point_index += 1
        yield feature_index, feature, points


class GeoJSONImportAdminForm(forms.ModelForm):
    class Meta:
        model = GeoJSONImport
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        data = deepcopy(self.instance.data)
        for feature_index, _, points in feature_groups(self.instance):
            if data.get('type') == 'FeatureCollection':
                target = data['features'][feature_index]
            else:
                target = data
            geometry = target['geometry'] if target.get('type') == 'Feature' else target

            for point_index, path, original_position in points:
                longitude_name = f'point_{point_index}_lng'
                latitude_name = f'point_{point_index}_lat'
                longitude = cleaned_data.get(longitude_name)
                latitude = cleaned_data.get(latitude_name)
                # Keep unchanged values when a client omits untouched fields.
                if longitude is None:
                    longitude = original_position[0]
                if latitude is None:
                    latitude = original_position[1]
                position = deepcopy(original_position)
                position[0], position[1] = longitude, latitude
                set_at_path(geometry, path, position)

            if target.get('type') == 'Feature' and points:
                properties = deepcopy(target.get('properties') or {})
                property_index = points[0][0]
                for suffix, key in (('type', 'type'), ('popup', 'popupContent')):
                    field_name = f'point_{property_index}_{suffix}'
                    if field_name in self.data:
                        value = cleaned_data.get(field_name, '')
                        if value or key in properties:
                            properties[key] = value
                target['properties'] = properties

        try:
            validate_geojson(data)
        except ValidationError as exc:
            raise forms.ValidationError(str(exc.detail)) from exc
        self._updated_geojson = data
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.data = self._updated_geojson
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class GeoJSONCoordinateInline(admin.TabularInline):
    model = GeoJSONCoordinate
    extra = 1
    fields = ('path', 'longitude', 'latitude', 'altitude')
    ordering = ('pk',)


class GeoJSONFeatureInline(admin.TabularInline):
    model = GeoJSONFeature
    extra = 0
    fields = ('feature_index', 'identifier', 'properties')
    readonly_fields = ('feature_index',)
    show_change_link = True


@admin.register(GeoJSONImport)
class GeoJSONImportAdmin(admin.ModelAdmin):
    list_display = ('name', 'mission', 'feature_count', 'created_at')
    list_filter = ('mission',)
    search_fields = ('name', 'mission__name')
    list_select_related = ('mission',)
    form = GeoJSONImportAdminForm
    readonly_fields = ('mission', 'created_at')

    def get_form(self, request, obj=None, **kwargs):
        attributes = {}
        groups = list(feature_groups(obj)) if obj else []
        for _, _, points in groups:
            for point_index, _, position in points:
                attributes[f'point_{point_index}_lng'] = forms.FloatField(
                    label='Längengrad', required=False, initial=position[0],
                    min_value=-180, max_value=180,
                )
                attributes[f'point_{point_index}_lat'] = forms.FloatField(
                    label='Breitengrad', required=False, initial=position[1],
                    min_value=-90, max_value=90,
                )
        for _, feature, points in groups:
            if points and feature.get('type') == 'Feature':
                properties = feature.get('properties') or {}
                property_index = points[0][0]
                attributes[f'point_{property_index}_type'] = forms.CharField(
                    label='Typ', required=False, initial=properties.get('type', ''),
                )
                attributes[f'point_{property_index}_popup'] = forms.CharField(
                    label='Popup-Inhalt', required=False,
                    initial=properties.get('popupContent', ''),
                    widget=forms.Textarea(attrs={'rows': 3}),
                )
        base_form = kwargs.get('form') or self.form
        kwargs['form'] = type('GeoJSONImportAdminForm', (base_form,), attributes)
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        fieldsets = [(None, {'fields': ('name', 'mission', 'created_at')})]
        groups = list(feature_groups(obj)) if obj else []
        for feature_index, feature, points in groups:
            identifier = str(feature.get('id', '')).strip()
            title = f'Feature {feature_index + 1}'
            if identifier:
                title += f' ({identifier})'
            fields = []
            if points:
                property_index = points[0][0]
                fields.extend((f'point_{property_index}_type', f'point_{property_index}_popup'))
                for point_index, _, _ in points:
                    fields.extend((f'point_{point_index}_lng', f'point_{point_index}_lat'))
            if fields:
                fieldsets.append((title, {'fields': tuple(fields)}))
        return fieldsets

    @admin.display(description='Features')
    def feature_count(self, obj):
        return obj.features.count()

    def has_add_permission(self, request):
        return False

@admin.register(GeoJSONFeature)
class GeoJSONFeatureAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'geojson_import', 'feature_index', 'coordinate_count')
    list_filter = ('geojson_import',)
    search_fields = ('identifier', 'geojson_import__name')
    list_select_related = ('geojson_import',)
    fields = ('geojson_import', 'feature_index', 'identifier', 'properties')
    readonly_fields = ('geojson_import', 'feature_index')
    inlines = (GeoJSONCoordinateInline,)

    @admin.display(description='Koordinaten')
    def coordinate_count(self, obj):
        return obj.coordinates.count()

    def has_add_permission(self, request):
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        if obj:
            sync_feature_rows(obj.geojson_import)
        return super().change_view(request, object_id, form_url, extra_context)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        deleted_paths = [tuple(item.path) for item in formset.deleted_objects]
        for deleted in formset.deleted_objects:
            deleted.delete()
        for instance in instances:
            instance.save()
        formset.save_m2m()

        feature = form.instance
        data = deepcopy(feature.geojson_import.data)
        if data.get('type') == 'FeatureCollection':
            target = data['features'][feature.feature_index]
        elif data.get('type') == 'Feature':
            target = data
        else:
            target = data
        target_geometry = target['geometry'] if target.get('type') == 'Feature' else target
        for path in sorted(deleted_paths, reverse=True):
            owner = at_path(target_geometry, path[:-1])
            if isinstance(owner, list):
                owner.pop(path[-1])
        for coordinate in feature.coordinates.all():
            position = [coordinate.longitude, coordinate.latitude]
            if coordinate.altitude is not None:
                position.append(coordinate.altitude)
            set_at_path(target_geometry, coordinate.path, position)
        if target.get('type') == 'Feature':
            if feature.identifier:
                target['id'] = feature.identifier
            target['properties'] = feature.properties
        validate_geojson(data)
        feature.geojson_import.data = data
        feature.geojson_import.save(update_fields=('data',))
