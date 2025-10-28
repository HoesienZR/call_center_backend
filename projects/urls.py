from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

router.register(r'projects', views.ProjectViewSet, basename='projects')
router.register(r"project-callers", views.ProjectCallerViewSet, basename='project-callers')

urlpatterns = router.urls
