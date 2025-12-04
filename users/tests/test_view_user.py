import pytest
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from projects.models import ProjectMembership, Project
from users.models import CustomUser


@pytest.mark.django_db
class TestUserViewSet:

    # ---------------- Fixtures ----------------
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

    @pytest.fixture
    def token(self, test_user):
        token, _ = Token.objects.get_or_create(user=test_user)
        return token

    @pytest.fixture
    def projects_and_callers(self, test_user):
        """
        ایجاد دو پروژه و دو کاربر با نقش caller
        """
        project1 = Project.objects.create(name="Test Project 1", created_by=test_user)
        project2 = Project.objects.create(name="Test Project 2", created_by=test_user)

        caller1 = CustomUser.objects.create_user(username="caller1", password="pass", phone_number="09120000001")
        caller2 = CustomUser.objects.create_user(username="caller2", password="pass", phone_number="09120000002")

        ProjectMembership.objects.create(user=caller1, project=project1, role="caller")
        ProjectMembership.objects.create(user=caller2, project=project2, role="caller")

        return {
            "projects": [project1, project2],
            "callers": [caller1, caller2]
        }

    # ---------------- Tests ----------------
    def test_me_endpoint(self, api_client, test_user, token):
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        url = reverse('users-me')  # نام url_name اکشن me
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["username"] == "testuser"
        assert response.data["phone_number"] == "09123456789"

    def test_callers_endpoint(self, api_client, test_user, token, projects_and_callers):
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        url = reverse('users-callers')  # نام url_name اکشن callers
        response = api_client.get(url)

        assert response.status_code == 200

        returned_usernames = [u["username"] for u in response.data]
        callers = projects_and_callers["callers"]

        # بررسی اینکه caller1 و caller2 برگشت داده شده‌اند
        assert "caller1" in returned_usernames
        assert "caller2" in returned_usernames

        # test_user نقش caller ندارد، پس نباید داخل لیست باشد
        assert "testuser" not in returned_usernames
