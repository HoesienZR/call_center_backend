from projects.urls import router
from users.views import UserViewSet
import auth_views
import views
from django.urls import path
router.register('users', UserViewSet, basename='users')

urlpatterns = [
    path("auth/login/", auth_views.login, name="login" ),
    path("auth/logout/", auth_views.logout, name="logout"),
    path("auth/profile/", auth_views.user_profile, name="profile"),
    path("auth/register/", auth_views.register, name="register"),
    path("auth/token/", auth_views.CustomAuthToken.as_view(), name="token"),
    path("request-otp/", views.request_otp, name="request-otp"),
    path("verify-otp/", views.verify_otp, name="verify-otp"),
]