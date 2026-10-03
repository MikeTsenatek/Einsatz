from rest_framework.routers import DefaultRouter

from .views import DischargeDestinationViewSet, TreatmentKeywordViewSet


router = DefaultRouter()
router.register("treatment-keywords", TreatmentKeywordViewSet, basename="treatment-keyword")

router.register("discharge-destinations", DischargeDestinationViewSet, basename="discharge-destination")

urlpatterns = router.urls
