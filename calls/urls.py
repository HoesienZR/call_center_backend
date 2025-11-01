from projects.urls import router
from . import views

router.register(r'calls', views.CallViewSet)
router.register(r'call-edit-history', views.CallEditHistoryViewSet)
