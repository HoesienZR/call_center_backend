from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
router = DefaultRouter()

router.register(r'call-statistics', views.CallStatisticsViewSet, basename='call-statistics')
router.register(r'cached-statistics', views.CachedStatisticsViewSet, basename='cached-statistics')
router.register(r'excel', views.CallExcelViewSet, basename='excel')

urlpatterns = [
                  path("projects/<int:project_id>/import-contacts/", views.ContactImportView.as_view(),
                       name="import-contacts"),
              ] + router.urls
