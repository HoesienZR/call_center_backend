from django.urls import path
from rest_framework.routers import DefaultRouter


from . import views

router = DefaultRouter()

router.register(r'projects', views.ProjectViewSet, basename='projects')
urlpatterns = [
    path('projectMememberships',views.ProjectMembershipApiListView.as_view(),name='project-memberships-list'),
    path("projects/<int:project_id>/import-callers/", views.CallerImportView.as_view(), name="import_contacts"),
]

urlpatterns += router.urls