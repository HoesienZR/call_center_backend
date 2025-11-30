from rest_framework.routers import DefaultRouter

from .views import CallViewSet, CallEditHistoryViewSet

router = DefaultRouter()
router.register(r'calls', CallViewSet, basename='calls')
router.register(r'call-edit-history', CallEditHistoryViewSet, basename='call-edits')

urlpatterns = router.urls
