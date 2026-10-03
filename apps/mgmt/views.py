from config.permissions import StrictDjangoModelPermissions
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import DischargeDestination, TreatmentKeyword, HiOrg
from .serializers import DischargeDestinationSerializer, TreatmentKeywordSerializer, HiOrgSerializer


class TreatmentKeywordViewSet(ReadOnlyModelViewSet):
    queryset = TreatmentKeyword.objects.filter(is_active=True).order_by("name")
    serializer_class = TreatmentKeywordSerializer
    permission_classes = (StrictDjangoModelPermissions,)


class DischargeDestinationViewSet(ReadOnlyModelViewSet):
    queryset = DischargeDestination.objects.filter(is_active=True).order_by("pk")
    serializer_class = DischargeDestinationSerializer
    permission_classes = (StrictDjangoModelPermissions,)


class HiOrgViewSet(ReadOnlyModelViewSet):
    queryset = HiOrg.objects.all()
    serializer_class = HiOrgSerializer
    permission_classes = (StrictDjangoModelPermissions,)
    pagination_class = None
