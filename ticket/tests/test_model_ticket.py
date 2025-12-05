import pytest
from django.contrib.auth import get_user_model
from ticket.models import Ticket

User = get_user_model()


@pytest.mark.django_db
class TestTicketModel:

    def test_ticket_creation(self):
        # ایجاد کاربر
        user = User.objects.create_user(
            username="testuser",
            password="12345678",
            phone_number="09120000000"
        )

        # ایجاد تیکت
        ticket = Ticket.objects.create(
            user=user,
            title="Test Ticket",
            description="This is a test ticket"
        )

        # بررسی اینکه تیکت ساخته شده
        assert Ticket.objects.count() == 1
        assert ticket.user == user
        assert ticket.title == "Test Ticket"
        assert ticket.description == "This is a test ticket"

    def test_ticket_default_done_value(self):
        user = User.objects.create_user(
            username="user2",
            password="12345678",
            phone_number="09120000001"
        )
        ticket = Ticket.objects.create(
            user=user,
            title="Check Done",
            description="Testing default"
        )

        assert ticket.done is False  # مقدار پیش‌فرض

    def test_ticket_str_method(self):
        user = User.objects.create_user(
            username="user3",
            password="12345678",
            phone_number="09120000002"
        )
        ticket = Ticket.objects.create(
            user=user,
            title="StringTest",
            description="Testing __str__"
        )

        assert str(ticket) == "StringTest"

    def test_ticket_ordering(self):
        user = User.objects.create_user(
            username="user4",
            password="12345678",
            phone_number="09120000003"
        )

        t1 = Ticket.objects.create(user=user, title="A", description="test1")
        t2 = Ticket.objects.create(user=user, title="B", description="test2")

        tickets = Ticket.objects.all()

        # چون ordering بر اساس -created_at هست t2 باید اول بیاید
        assert tickets.first() == t2
