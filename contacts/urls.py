from django.urls import path
from rest_framework.routers import DefaultRouter

from contacts.views import ContactViewSet
router = DefaultRouter()

router.register(r'contacts', ContactViewSet, basename='contacts')


urlpatterns = router.urls
