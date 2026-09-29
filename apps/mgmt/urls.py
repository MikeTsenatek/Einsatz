from rest_framework.routers import DefaultRouter

from .views import TreatmentKeywordViewSet


router = DefaultRouter()
router.register("treatment-keywords", TreatmentKeywordViewSet, basename="treatment-keyword")

urlpatterns = router.urls
