from rest_framework.viewsets import ModelViewSet
from .serializers import TicketSerializer
from rest_framework.permissions import IsAuthenticated
from .models import Ticket


class TicketViewSet(ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    queryset = Ticket.objects.all()

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)
