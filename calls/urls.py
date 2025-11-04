from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register(r'calls', views.CallViewSet)
router.register(r'call-edit-history', views.CallEditHistoryViewSet)

urlpatterns = router.urls