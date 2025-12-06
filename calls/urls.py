from rest_framework.routers import DefaultRouter

from .views import CallViewSet

router = DefaultRouter()
router.register(r'calls', CallViewSet, basename='calls')

urlpatterns = router.urls
