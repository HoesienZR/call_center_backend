from rest_framework_nested.routers import NestedSimpleRouter
from unicodedata import lookup

import views
from projects.urls import router

questions_router = NestedSimpleRouter(router, r"projects", lookup="project")
questions_router.register(r"questions", QuestionViewSet, basename="project-questions")

choices_router = NestedSimpleRouter(questions_router, r"questions", lookup="question")
choices_router.register(r"choices", AnswerChoiceViewSet, basename="project-choices")
router.register(r'saved-searches', views.SavedSearchViewSet, basename="saved-searches")
router.register(r'upload-files', views.UploadFileViewSet, basename="upload-files")
router.register(r'export-reports', views.ExportReportViewSet, basename="export-reports")