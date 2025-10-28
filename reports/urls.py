from rest_framework.routers import DefaultRouter
from projects.urls import router
import views

router.register(r'call-statistics', views.CallStatisticViewSet, basename='call-statistics')
router.register(r'cached-statistics', views.CachedStatisticViewSet, basename='cached-statistics')
router.register(r'excel', views.CallExcelViewSet, basename='excel')

