import pytest
from unittest.mock import patch
from users.models import CustomUser
from ticket.models import Ticket

@pytest.mark.django_db
def test_send_message_to_developer_signal():
    user = CustomUser.objects.create_user(
        password="pass123",
        phone_number="09123456789",
        first_name="Test",
        last_name="User"
    )

    with patch("ticket.signals.requests.get") as mock_get:
        ticket = Ticket.objects.create(
            user=user,
            title="Test Ticket",
            description="This is a test ticket"
        )

        assert mock_get.called, "requests.get was not called by the signal"

        url_called = mock_get.call_args[0][0]
        assert "tsms.ir" in url_called
        assert "Test Ticket" in url_called
        assert "This is a test ticket" in url_called
        assert "09123456789" in url_called
