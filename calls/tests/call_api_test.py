from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from calls.models import Call
from projects.models import Project
from contacts.models import Contact
from django.contrib.auth import get_user_model

User = get_user_model()


class CallAPITest(TestCase):
    def setUp(self):
        """Initial setup for all tests"""
        self.client = APIClient()

        # Create test user and authenticate
        self.user = User.objects.create_user(username="caller", password="password123")
        self.client.force_authenticate(user=self.user)

        # Create test contact
        self.contact = Contact.objects.create(
            full_name="Test Contact",
            phone="123456789"
        )

        # Create test project
        self.project = Project.objects.create(
            name="Test Project",
            created_by=self.user
        )

        # Create an initial call for GET/EDIT tests
        self.call = Call.objects.create(
            contact=self.contact,
            caller=self.user,
            project=self.project,
            status="pending",
            call_result="interested",
            duration=120
        )

    def test_create_call(self):
        """Test creating a new call"""
        url = reverse('call-list')  # Ensure your ViewSet is registered with 'call'
        data = {
            "contact": self.contact.id,
            "caller": self.user.id,
            "project": self.project.id,
            "status": "pending",
            "call_result": "interested",
            "duration": 120
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], "pending")
        self.assertEqual(response.data['contact'], self.contact.id)

    def test_get_calls(self):
        """Test retrieving list of calls"""
        url = reverse('call-list')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)  # At least the one we created in setUp

    def test_edit_call(self):
        """Test editing an existing call"""
        url = reverse('call-detail', kwargs={'pk': self.call.id})
        data = {
            "status": "completed",
            "call_result": "successful",
            "duration": 150
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], "completed")
        self.assertEqual(response.data['call_result'], "successful")
        self.assertEqual(response.data['duration'], 150)
