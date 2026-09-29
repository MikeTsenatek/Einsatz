from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import TreatmentKeyword
from .serializers import TreatmentKeywordSerializer


class TreatmentKeywordViewSet(ReadOnlyModelViewSet):
    queryset = TreatmentKeyword.objects.filter(is_active=True).order_by("name")
    serializer_class = TreatmentKeywordSerializer
    permission_classes = (IsAuthenticated,)
