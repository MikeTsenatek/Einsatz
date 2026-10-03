from rest_framework.routers import DefaultRouter

from .views import HiOrgViewSet, DischargeDestinationViewSet, TreatmentKeywordViewSet


router = DefaultRouter()
router.register("treatment-keywords", TreatmentKeywordViewSet, basename="treatment-keyword")

router.register("discharge-destinations", DischargeDestinationViewSet, basename="discharge-destination")

router.register("hiorgs", HiOrgViewSet, basename="hiorg")

urlpatterns = router.urls
