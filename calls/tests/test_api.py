from rest_framework.test import APIClient
from rest_framework import status
from calls.models import Call, CallAnswer, CallEditHistory
from django.urls import reverse

class CallAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="caller", password="password123")
        self.contact = Contact.objects.create(full_name="Test Contact", phone="123456789")
        self.project = Project.objects.create(name="Test Project", created_by=self.user)

    def test_create_call(self):
        url = reverse('call-list')  # فرض بر اینکه نام endpoint `call-list` باشد
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

    def test_get_calls(self):
        url = reverse('call-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_edit_call(self):
        url = reverse('call-detail', kwargs={'pk': 1})  # فرض بر اینکه id تماس 1 است
        data = {"status": "completed", "notes": "The call was successful."}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], "completed")
