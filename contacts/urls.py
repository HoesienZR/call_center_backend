from django.urls import path
from rest_framework.routers import DefaultRouter

from contacts.views import ContactViewSet, ContactImportView

router = DefaultRouter()

router.register(r'contacts', ContactViewSet, basename='contacts')

urlpatterns = [
                  path("projects/<int:project_id>/import-contacts/", ContactImportView.as_view(),
                       name="import-contacts"),
              ] + router.urls
