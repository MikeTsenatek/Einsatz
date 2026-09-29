from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.missions.models import Mission
from .models import MapOverlay
from .serializers import MapOverlaySerializer, GeoJSONImportSerializer


class MapAdminPermission(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.is_staff


class MissionMapView(APIView):
    permission_classes = (IsAuthenticated, MapAdminPermission)

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
    permission_classes = (IsAuthenticated, MapAdminPermission)

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
