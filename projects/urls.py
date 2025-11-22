from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

# ثبت مسیرهای مربوط به ProjectViewSet با استفاده از router
router.register(r'projects', views.ProjectViewSet, basename='projects')

urlpatterns = [
    # مسیرهای دستی برای ProjectMembershipApiListView و CallerImportView
    path('projectMemberships', views.ProjectMembershipApiListView.as_view(), name='project-memberships-list'),
    path("projects/<int:project_id>/import-callers/", views.CallerImportView.as_view(), name="import_contacts"),

    # مسیر برای بررسی نقش کاربر
    path('projects/<int:project_id>/check-user-role/', views.ProjectViewSet.as_view({'get': 'check_user_role'}),
         name='check_user_role'),

    # مسیر برای گزارش عملکرد تماس‌گیرندگان
    path("projects/<int:pk>/caller-performance/", views.ProjectViewSet.as_view({'get': 'caller_performance'}),
         name="caller_performance"),
]

# اضافه کردن URLهای ثبت‌شده توسط router به urlpatterns
urlpatterns += router.urls
