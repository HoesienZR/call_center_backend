class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    queryset = Ticket.objects.all()

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)
