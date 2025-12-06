import pytest
from django.utils import timezone
from users.models import CustomUser
from users.serializers import CustomUserSerializer
from persiantools.jdatetime import JalaliDate


@pytest.mark.django_db
def test_custom_user_serializer():
    user = CustomUser.objects.create_user(
        password="strongpassword123",
        email="test@example.com",
        phone_number="09123456789",
        first_name="Test",
        last_name="User",
        can_create_projects=True
    )

    serializer = CustomUserSerializer(user)
    data = serializer.data

    assert data['email'] == "test@example.com"
    assert data['first_name'] == "Test"
    assert data['last_name'] == "User"
    assert data['phone_number'] == "09123456789"
    assert data['can_create_projects'] is True

    # بررسی فیلد read-only
    assert data['is_staff'] is False
    assert data['is_active'] is True
    assert 'date_joined' in data
    assert 'last_login' in data

    # بررسی persian_date_joined
    expected_persian_date = str(JalaliDate(user.date_joined.date()))
    assert data['persian_date_joined'] == expected_persian_date
