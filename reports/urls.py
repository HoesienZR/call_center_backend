from django.urls import path
import views
from projects.urls import router

router.register(r'call-statistics', views.CallStatisticViewSet, basename='call-statistics')
router.register(r'cached-statistics', views.CachedStatisticViewSet, basename='cached-statistics')
router.register(r'excel', views.CallExcelViewSet, basename='excel')

urlpatterns = [
    path("projects/<int:project_id>/import-contacts/", views.ContactImportView.as_view(), name="import-contacts"),
]