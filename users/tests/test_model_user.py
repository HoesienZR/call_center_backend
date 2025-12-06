import pytest
from django.db import IntegrityError
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_create_custom_user():
    # Create a user
    user = User.objects.create_user(
        password="strongpassword123",
        phone_number="09123456789",
        can_create_projects=True
    )

    # Check the user is saved correctly
    assert user.phone_number == "09123456789"
    assert user.can_create_projects is True

    # Check __str__ method
    assert str(user) == "09123456789"


@pytest.mark.django_db
def test_phone_number_unique_constraint():
    # Create first user
    User.objects.create_user(
        password="password1",
        phone_number="09121234567"
    )

    # Creating another user with the same phone_number should raise IntegrityError
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            password="password2",
            phone_number="09121234567"
        )
