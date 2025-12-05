from rest_framework import serializers

from .models import *


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("user", "title", "description", "done", "created_at")
        read_only_fields = ("user", "created_at")
