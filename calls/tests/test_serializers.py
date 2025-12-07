import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from persiantools.jdatetime import JalaliDate
from rest_framework.exceptions import ValidationError

from calls.models import Call, CallAnswer
from calls.models import Question, AnswerChoice
from calls.serializers import CallSerializer, CallAnswerSerializer, CallExcelSerializer
from contacts.models import Contact
from projects.models import Project

User = get_user_model()


class CallSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone_number="09164896609", password="password123")
        self.project = Project.objects.create(name="Test Project", created_by=self.user)
        self.contact = Contact.objects.create(
            full_name="Test Contact",
            phone="123456789",
            project=self.project
        )

    def test_call_serializer_valid(self):
        data = {
            "contact_id": self.contact.id,
            "caller_id": self.user.id,
            "project_id": self.project.id,
            "status": "pending",
            "call_result": "interested",
            "duration": 120
        }
        serializer = CallSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        call = serializer.save()
        self.assertEqual(call.status, "pending")
        self.assertEqual(call.duration, 120)

    def test_call_serializer_invalid_missing_project(self):
        data = {
            "contact": self.contact.id,
            "caller": self.user.id,
            "call_result": "interested",
            "duration": 120
        }
        serializer = CallSerializer(data=data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)


class CallAnswerSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone_number="09164896609", password="password123")
        self.project = Project.objects.create(name="Test Project", created_by=self.user)
        self.contact = Contact.objects.create(
            full_name="Test Contact",
            phone="123456789",
            project=self.project
        )
        self.call = Call.objects.create(
            contact=self.contact,
            caller=self.user,
            project=self.project,
            status="pending",
            call_result="interested",
            duration=120
        )
        self.question = Question.objects.create(text="Did you like the service?", project=self.project)
        self.answer_choice = AnswerChoice.objects.create(text="Yes", question=self.question)

    def test_call_answer_serializer(self):
        call_answer = CallAnswer.objects.create(
            call=self.call,
            question=self.question,
            selected_choice=self.answer_choice
        )
        serializer = CallAnswerSerializer(call_answer)
        self.assertEqual(serializer.data['question_text'], "Did you like the service?")
        self.assertEqual(serializer.data['selected_choice_text'], "Yes")

    def test_call_answer_serializer_without_choice(self):
        call_answer = CallAnswer.objects.create(
            call=self.call,
            question=self.question,
            selected_choice=None
        )
        serializer = CallAnswerSerializer(call_answer)
        self.assertEqual(serializer.data['question_text'], "Did you like the service?")
        self.assertIsNone(serializer.data['selected_choice_text'])


@pytest.mark.django_db
def test_call_excel_serializer():
    # ---- Create User (Caller) ----
    caller = User.objects.create_user(
        phone_number="09120000000",
        password="testpass",
    )

    # ---- Create Project ----
    project = Project.objects.create(
        name="Demo Project",
        created_by=caller
    )

    # ---- Create Contact ----
    contact = Contact.objects.create(
        project=project,
        full_name="John Doe",
        phone="09123456789",
        gender="male",
        is_special=True,
        birth_date="1990-01-01",
        address="Tehran - Valiasr",
        custom_fields={"age": "34", "vip": "yes"}
    )

    # ---- Create Question & Choices ----
    q1 = Question.objects.create(
        text="How satisfied are you?",
        project=project
    )
    choice1 = AnswerChoice.objects.create(
        question=q1,
        text="Very satisfied"
    )

    q2 = Question.objects.create(
        text="Would you recommend us?",
        project=project
    )
    choice2 = AnswerChoice.objects.create(
        question=q2,
        text="Yes"
    )

    # ---- Create Call ----
    call_date = timezone.now()
    call = Call.objects.create(
        caller=caller,
        contact=contact,
        project=project,
        call_result="success",
        status="completed",
        notes="Test notes",
        duration=120,
        call_date=call_date
    )

    # ---- Create Answers ----
    CallAnswer.objects.create(
        call=call,
        question=q1,
        selected_choice=choice1
    )
    CallAnswer.objects.create(
        call=call,
        question=q2,
        selected_choice=choice2
    )

    # ---- Serialize ----
    data = CallExcelSerializer(call).data

    # ---- Assertions ----

    assert data["caller_name"] == caller.get_full_name()
    assert data["contact_name"] == "John Doe"
    assert data["contact_phone"] == "09123456789"
    assert data["project_name"] == "Demo Project"
    assert data["contact_gender"] == "male"
    assert data["special_contact"] is "True"
    assert data["contact_birth_date"] == "1990-01-01"
    assert data["caller_phone"] == "09120000000"
    assert data["notes"] == "Test notes"
    assert data["duration"] == 120
    assert data["address"] == "Tehran - Valiasr"

    # Persian date
    assert data["persian_date"] == str(JalaliDate(call_date.date()))

    # Custom fields
    assert data["custom_fields"] == {"age": "34", "vip": "yes"}

    # Answers format
    assert (
            "How satisfied are you? Very satisfied  |" in data["answers"]
    )
    assert (
            "Would you recommend us? Yes  |" in data["answers"]
    )
