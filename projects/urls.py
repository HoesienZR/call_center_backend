from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter
from . import views

router = DefaultRouter()

router.register(r'projects', views.ProjectViewSet, basename='projects')
questions_router = NestedSimpleRouter(router, r"projects", lookup="project")
questions_router.register(r"questions", views.QuestionViewSet, basename="project-questions")

choices_router = NestedSimpleRouter(questions_router, r"questions", lookup="question")
choices_router.register(r"choices", views.AnswerChoiceViewSet, basename="project-choices")
urlpatterns = [
    # مسیرهای دستی برای ProjectMembershipApiListView و CallerImportView
    path('projectMemberships', views.ProjectMembershipApiListView.as_view(), name='project-memberships-list'),
    path("projects/<int:project_id>/import-callers/", views.CallerImportView.as_view(), name="import_contacts"),


]

urlpatterns += router.urls + questions_router.urls + choices_router.urls
