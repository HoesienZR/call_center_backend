from projects.urls import router
from ticket import views

router.register(r'tickets', views.TicketViewSet)