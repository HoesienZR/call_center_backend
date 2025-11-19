from django.urls import path
from rest_framework.routers import DefaultRouter

from . import auth_views
from . import views
from users.views import UserViewSet

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')

urlpatterns = [
                  path("auth/login/", auth_views.login, name="login"),
                  path("auth/logout/", auth_views.logout, name="logout"),
                  path("auth/profile/", auth_views.user_profile, name="profile"),
                  path("auth/register/", auth_views.register, name="register"),
                  path("auth/token/", auth_views.CustomAuthToken.as_view(), name="token"),
                  path("request-otp/", auth_views.request_otp, name="request-otp"),
                  path("verify-otp/", auth_views.verify_otp, name="verify-otp"),
              ] + router.urls
