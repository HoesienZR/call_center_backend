from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter
from projects.urls import router as project_router
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

questions_router = NestedSimpleRouter(project_router, r"projects", lookup="project")
questions_router.register(r"questions", views.QuestionViewSet, basename="project-questions")

choices_router = NestedSimpleRouter(questions_router, r"questions", lookup="question")
choices_router.register(r"choices", views.AnswerChoiceViewSet, basename="project-choices")
router.register(r'saved-searches', views.SavedSearchViewSet, basename="saved-searches")
router.register(r'upload-files', views.UploadedFileViewSet, basename="upload-files")
# router.register(r'export-reports', views.ExportReportViewSet, basename="export-reports")

urlpatterns = questions_router.urls + choices_router.urls + router.urls
