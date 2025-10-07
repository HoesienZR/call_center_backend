from csv import excel

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import auth_views

from . import signals
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
router.register(r'excel',views.CallExcelViewSet,basename='excel')


urlpatterns = [
    path('', include(router.urls)),
    # Authentication URLs
    path("auth/login", auth_views.login, name="api_login"),
    path('auth/logout/', auth_views.logout, name='api_logout'),
    path('auth/profile/', auth_views.user_profile, name='api_user_profile'),
    path('auth/register/', auth_views.register, name='api_register'),
    path('auth/token/', auth_views.CustomAuthToken.as_view(), name='api_token_auth'),
    path('',views.check_postgresql_connection, name='check_postgresql_connection'),
    path('admin/dashboard/', views.dashboard_data, name='dashboard_data'),
    path('project/<int:project_id>/statistics/',views.project_statistics_api, name='project-statistics-api'),
    path('main_dashboard', views.dashboard_stats, name='dashboard_data'),
    path('request-otp/', auth_views.request_otp, name='request-otp'),
    path('verify-otp/', auth_views.verify_otp, name='verify-otp'),
    path("projects/<int:project_id>/import-contacts/", views.ContactImportView.as_view(), name="import_contacts"),

]



