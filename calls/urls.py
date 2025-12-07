from rest_framework.routers import DefaultRouter

from .views import CallViewSet, CallExcelViewSet

router = DefaultRouter()
router.register(r'calls', CallViewSet, basename='calls')
router.register(r'excel', CallExcelViewSet, basename='excel')

urlpatterns = router.urls
