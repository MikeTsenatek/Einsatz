from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.missions.models import Mission
from .models import MapOverlay
from .serializers import MapOverlaySerializer, GeoJSONImportSerializer


class MapModelPermissions(BasePermission):
    message = "Bitte melden Sie sich an oder lassen Sie Ihre Kartenrechte prüfen."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if isinstance(view, MissionMapView):
            if request.method in SAFE_METHODS:
                required = "map.view_mapoverlay"
            elif request.method == "PUT":
                action = (
                    "change_mapoverlay"
                    if MapOverlay.objects.filter(
                        mission_id=view.kwargs["mission_pk"],
                    ).exists()
                    else "add_mapoverlay"
                )
                required = f"map.{action}"
            else:
                required = "map.change_mapoverlay"
        else:
            action = "view_geojsonimport" if request.method in SAFE_METHODS else "add_geojsonimport"
            required = f"map.{action}"

        if not request.user.has_perm(required):
            raise PermissionDenied(
                "Für diese Kartenaktion fehlt das Recht "
                f"{required}. Bitte Gruppenmitgliedschaft oder Rechte durch die "
                "Administration prüfen lassen."
            )
        return True


class MissionMapView(APIView):
    permission_classes = (MapModelPermissions,)

    def get(self, request, mission_pk):
        mission = get_object_or_404(Mission, pk=mission_pk)
        overlay = MapOverlay.objects.filter(mission=mission).first()
        return Response(MapOverlaySerializer(overlay).data) if overlay else Response(status=204)

    def put(self, request, mission_pk):
        mission = get_object_or_404(Mission, pk=mission_pk)
        serializer = MapOverlaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        overlay, _ = MapOverlay.objects.update_or_create(mission=mission, defaults=serializer.validated_data)
        return Response(MapOverlaySerializer(overlay).data)

    def patch(self, request, mission_pk):
        mission = get_object_or_404(Mission, pk=mission_pk)
        overlay = get_object_or_404(MapOverlay, mission=mission)
        serializer = MapOverlaySerializer(overlay, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MapOverlaySerializer(overlay).data)


class MissionGeoJSONView(APIView):
    permission_classes = (MapModelPermissions,)

    def get(self, request, mission_pk):
        mission = get_object_or_404(Mission, pk=mission_pk)
        imports = mission.geojson_imports.order_by('pk')
        return Response(GeoJSONImportSerializer(imports, many=True).data)

    def post(self, request, mission_pk):
        mission = get_object_or_404(Mission, pk=mission_pk)
        serializer = GeoJSONImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(mission=mission)
        return Response(serializer.data, status=201)
