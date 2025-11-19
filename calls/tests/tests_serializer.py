from rest_framework.exceptions import ValidationError
from calls.serializers import CallSerializer, CallAnswerSerializer
from calls.models import Call, CallAnswer
from django.test import TestCase

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'call_center_backend.settings')

import django
django.setup()

class CallSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="caller", password="password123")
        self.contact = Contact.objects.create(full_name="Test Contact", phone="123456789")
        self.project = Project.objects.create(name="Test Project", created_by=self.user)

    def test_call_serializer_valid(self):
        data = {
            "contact": self.contact.id,
            "caller": self.user.id,
            "project": self.project.id,
            "status": "pending",
            "call_result": "interested",
            "duration": 120
        }
        serializer = CallSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        call = serializer.save()
        self.assertEqual(call.status, "pending")
        self.assertEqual(call.duration, 120)

    def test_call_serializer_invalid(self):
        data = {
            "contact": self.contact.id,
            "caller": self.user.id,
            "project": self.project.id,
            "call_result": "interested",
            "duration": 120
        }
        serializer = CallSerializer(data=data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

class CallAnswerSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="caller", password="password123")
        self.contact = Contact.objects.create(full_name="Test Contact", phone="123456789")
        self.project = Project.objects.create(name="Test Project", created_by=self.user)
        self.call = Call.objects.create(
            contact=self.contact,
            caller=self.user,
            project=self.project,
            status="pending",
            call_result="interested",
            duration=120
        )
        self.question = Question.objects.create(text="Did you like the service?")
        self.answer_choice = AnswerChoice.objects.create(text="Yes")

    def test_call_answer_serializer(self):
        call_answer = CallAnswer.objects.create(
            call=self.call,
            question=self.question,
            selected_choice=self.answer_choice
        )
        serializer = CallAnswerSerializer(call_answer)
        self.assertEqual(serializer.data['question_text'], "Did you like the service?")
        self.assertEqual(serializer.data['selected_choice_text'], "Yes")
