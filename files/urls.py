from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

router.register(r'saved-searches', views.SavedSearchViewSet, basename="saved-searches")
router.register(r'upload-files', views.UploadedFileViewSet, basename="upload-files")
# router.register(r'export-reports', views.ExportReportViewSet, basename="export-reports")

urlpatterns = router.urls
