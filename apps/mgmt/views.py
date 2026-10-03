from config.permissions import StrictDjangoModelPermissions
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import DischargeDestination, TreatmentKeyword
from .serializers import DischargeDestinationSerializer, TreatmentKeywordSerializer


class TreatmentKeywordViewSet(ReadOnlyModelViewSet):
    queryset = TreatmentKeyword.objects.filter(is_active=True).order_by("name")
    serializer_class = TreatmentKeywordSerializer
    permission_classes = (StrictDjangoModelPermissions,)


class DischargeDestinationViewSet(ReadOnlyModelViewSet):
    queryset = DischargeDestination.objects.filter(is_active=True).order_by("pk")
    serializer_class = DischargeDestinationSerializer
    permission_classes = (StrictDjangoModelPermissions,)
