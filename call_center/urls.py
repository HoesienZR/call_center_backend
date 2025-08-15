from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import auth_views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'projects', views.ProjectViewSet)
router.register(r'project-callers', views.ProjectCallerViewSet)
router.register(r'contacts', views.ContactViewSet)
router.register(r'calls', views.CallViewSet)
router.register(r'call-edit-history', views.CallEditHistoryViewSet)
router.register(r'call-statistics', views.CallStatisticsViewSet)
router.register(r'saved-searches', views.SavedSearchViewSet)
router.register(r'uploaded-files', views.UploadedFileViewSet)
router.register(r'export-reports', views.ExportReportViewSet)
router.register(r'cached-statistics', views.CachedStatisticsViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Authentication URLs
    path('auth/login/', auth_views.login, name='api_login'),
    path('auth/logout/', auth_views.logout, name='api_logout'),
    path('auth/profile/', auth_views.user_profile, name='api_user_profile'),
    path('auth/register/', auth_views.register, name='api_register'),
    path('auth/token/', auth_views.CustomAuthToken.as_view(), name='api_token_auth'),
]


