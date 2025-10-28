from rest_framework.routers import DefaultRouter

from users.views import UserViewSet

router = DefaultRouter()

router.register('users', UserViewSet, basename='users')
