from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from calls.calls_import import Contact, Project, Question, AnswerChoice
from calls.models import Call, CallEditHistory

User = get_user_model()


class CallAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(phone_number="1000000001", password="password1")
        self.user2 = User.objects.create_user(phone_number="1000000002", password="password2")
        self.admin_user = User.objects.create_superuser(phone_number="1000000000",
                                                        password="admin123")

        self.project = Project.objects.create(name="Test Project", created_by=self.user1)
        self.contact = Contact.objects.create(full_name="Test Contact", phone="2000000001", project=self.project)
        self.call = Call.objects.create(contact=self.contact, caller=self.user1, project=self.project,
                                        status="pending", call_result="interested", duration=120)
        self.question = Question.objects.create(text="Did you like the service?", project=self.project)
        self.answer_choice = AnswerChoice.objects.create(text="Yes", question=self.question)

    def test_list_calls(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/calls/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_list_calls_by_project(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"/api/calls/?project_id={self.project.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for call in response.data['results']:
            self.assertEqual(call['project'], self.project.id)



