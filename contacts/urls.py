from contacts.views import ContactViewSet
from projects.urls import router

router.register(r'contacts', ContactViewSet, basename='contacts')
