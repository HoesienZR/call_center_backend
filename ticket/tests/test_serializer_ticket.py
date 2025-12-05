import pytest
from users.models import CustomUser
from ticket.serializers import TicketSerializer
from ticket.models import Ticket


@pytest.mark.django_db
class TestTicketSerializer:

    @pytest.fixture
    def user(self):
        return CustomUser.objects.create_user(
            username="user1",
            password="pass123",
            phone_number="09123456789"
        )

    def test_valid_data_creates_ticket(self, user):
        data = {
            "user": user.id,
            "title": "Test Ticket",
            "description": "This is a test ticket",
            "done": False,
        }

        serializer = TicketSerializer(data=data)

        assert serializer.is_valid(), serializer.errors
        ticket = serializer.save(user=user)

        assert ticket.title == data["title"]
        assert ticket.description == data["description"]
        assert ticket.user == user
        assert ticket.done is False
        assert ticket.created_at is not None  # auto add timestamp

    def test_missing_required_fields(self, user):
        data = {
            "user": user.id,
            "description": "Missing title",
        }

        serializer = TicketSerializer(data=data)

        assert not serializer.is_valid()
        assert "title" in serializer.errors  # ensures validation failure

    def test_serialized_output_format(self, user):
        ticket = Ticket.objects.create(
            user=user,
            title="Output Ticket",
            description="Test output formatting",
            done=True
        )

        serializer = TicketSerializer(ticket)
        serialized_data = serializer.data

        assert serialized_data["title"] == "Output Ticket"
        assert serialized_data["done"] is True
        assert "created_at" in serialized_data
