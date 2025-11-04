from rest_framework.routers import DefaultRouter

from ticket import views

router = DefaultRouter()

router.register(r'tickets', views.TicketViewSet)

urlpatterns = router.urls
