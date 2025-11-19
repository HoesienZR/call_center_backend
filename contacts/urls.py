from django.urls import path
from rest_framework.routers import DefaultRouter

from contacts.views import ContactViewSet, RequestNewContactView

router = DefaultRouter()

router.register(r'contacts', ContactViewSet, basename='contacts')

urlpatterns = [
    path("contacts/request/", RequestNewContactView.as_view(), name="request-new-contact"),
]
urlpatterns += router.urls
