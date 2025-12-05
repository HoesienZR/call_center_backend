import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from users.models import CustomUser
from ticket.models import Ticket


@pytest.mark.django_db
class TestTicketViewSet:

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def user(self):
        return CustomUser.objects.create_user(
            username="user1",
            password="pass123",
            phone_number="09120000001"
        )

    @pytest.fixture
    def token(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        return token

    def test_cannot_access_without_auth(self, api_client):
        url = reverse('ticket-list')
        response = api_client.get(url)
        assert response.status_code == 401

    def test_create_ticket(self, api_client, user, token):
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        url = reverse('ticket-list')

        data = {
            "title": "Test Ticket",
            "description": "Test Content",
            "done": False
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == 201
        ticket = Ticket.objects.first()
        assert ticket is not None
        assert ticket.user == user
        assert ticket.title == data["title"]
        assert ticket.description == data["description"]

    def test_list_tickets(self, api_client, user, token):
        Ticket.objects.create(user=user, title="T1", description="D1")
        Ticket.objects.create(user=user, title="T2", description="D2")

        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        url = reverse('ticket-list')
        response = api_client.get(url)

        assert response.status_code == 200
        assert len(response.data["results"]) == 2
        returned_titles = [i["title"] for i in response.data["results"]]
        assert "T1" in returned_titles
        assert "T2" in returned_titles

    def test_retrieve_ticket(self, api_client, user, token):
        ticket = Ticket.objects.create(user=user, title="Retrieve Test", description="Test retrieve")

        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        url = reverse('ticket-detail', args=[ticket.id])
        response = api_client.get(url)

        assert response.status_code == 200
        assert response.data["title"] == ticket.title

    def test_update_ticket(self, api_client, user, token):
        ticket = Ticket.objects.create(user=user, title="Old", description="Old desc")

        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        url = reverse('ticket-detail', args=[ticket.id])

        updated_data = {
            "title": "Updated",
            "description": "Updated desc",
            "done": True
        }

        response = api_client.put(url, updated_data, format="json")

        assert response.status_code == 200
        ticket.refresh_from_db()
        assert ticket.title == "Updated"
        assert ticket.done is True

    def test_delete_ticket(self, api_client, user, token):
        ticket = Ticket.objects.create(user=user, title="Delete", description="Delete me")

        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        url = reverse('ticket-detail', args=[ticket.id])
        response = api_client.delete(url)

        assert response.status_code in (204, 200)
        assert Ticket.objects.count() == 0
