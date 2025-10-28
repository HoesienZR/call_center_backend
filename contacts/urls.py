from rest_framework.routers import DefaultRouter

from contacts.views import ContactViewSet

router = DefaultRouter

router.register(r'contacts', ContactViewSet, basename='contacts')