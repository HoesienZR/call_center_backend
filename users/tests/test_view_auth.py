import pytest
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from django.urls import reverse
from users.models import CustomUser

@pytest.mark.django_db
class TestAuthAPI:

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def test_user(self):
        user = CustomUser.objects.create_user(
            username="testuser",
            password="strongpassword123",
            email="test@example.com",
            phone_number="09123456789"
        )
        return user

    def test_register(self, api_client):
        url = reverse('register')  # نام URL view register
        data = {
            "username": "newuser",
            "password": "password123",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "phone_number": "09121234567"
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == 201
        assert "token" in response.data
        assert response.data["username"] == "newuser"

    def test_login_with_phone(self, api_client, test_user):
        url = reverse('login')  # نام URL view login
        data = {
            "phone": "09123456789",
            "password": "strongpassword123"
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == 200
        assert "token" in response.data
        assert response.data["username"] == "testuser"

    def test_custom_auth_token(self, api_client, test_user):
        url = reverse('token')  # نام URL view CustomAuthToken
        data = {"username": "testuser", "password": "strongpassword123"}
        response = api_client.post(url, data, format='json')
        assert response.status_code == 200
        assert response.data["username"] == "testuser"
        assert "token" in response.data

    def test_user_profile(self, api_client, test_user):
        token, _ = Token.objects.get_or_create(user=test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        url = reverse('profile')  # نام URL view user_profile
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["username"] == "testuser"

    def test_logout(self, api_client, test_user):
        token, _ = Token.objects.get_or_create(user=test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        url = reverse('logout')  # نام URL view logout
        response = api_client.post(url)
        assert response.status_code == 200
        assert response.data["message"] == "Successfully logged out"

    def test_request_otp(self, api_client, test_user):
        url = reverse('request-otp')  # نام URL view request_otp
        data = {"phone": "09123456789"}
        response = api_client.post(url, data, format='json')
        assert response.status_code in [200, 429, 404]
        # OTP ارسال شده یا خطاهای محدودیت بررسی می‌شود

    def test_verify_otp(self, api_client, test_user, monkeypatch):
        # Mock کردن OTP
        from users.services import otp_service
        monkeypatch.setattr(otp_service, "get_cached_otp", lambda request, phone: "123456")
        monkeypatch.setattr(otp_service, "clear_otp", lambda request, phone: None)

        url = reverse('verify-otp')
        data = {"phone": "09123456789", "otp": "123456"}
        response = api_client.post(url, data, format='json')
        assert response.status_code == 200
        assert "token" in response.data
        assert response.data["username"] == "testuser"
