from django.test import TestCase
from django.contrib.auth import get_user_model
from calls.models import Call, CallAnswer, CallEditHistory
from calls.calls_import import Project, Contact
from django.db.utils import IntegrityError

User = get_user_model()

class CallModelTest(TestCase):
    def setUp(self):
        # ایجاد کاربران و پروژه‌ها برای تست
        self.user = User.objects.create_user(username="caller", password="password123")
        self.contact = Contact.objects.create(full_name="Test Contact", phone="123456789")
        self.project = Project.objects.create(name="Test Project", created_by=self.user)

    def test_create_call(self):
        # تست ساخت یک تماس
        call = Call.objects.create(
            contact=self.contact,
            caller=self.user,
            project=self.project,
            status="pending",
            call_result="interested",
            duration=120
        )
        self.assertEqual(call.contact.full_name, "Test Contact")
        self.assertEqual(call.caller.username, "caller")
        self.assertEqual(call.project.name, "Test Project")

    def test_call_history_creation(self):
        # تست ایجاد تاریخچه ویرایش تماس
        call = Call.objects.create(
            contact=self.contact,
            caller=self.user,
            project=self.project,
            status="pending",
            call_result="interested",
            duration=120
        )
        self.assertEqual(CallEditHistory.objects.count(), 1)

    def test_signal_on_create_call(self):
        # تست سیگنال post_save برای تاریخچه ویرایش
        call = Call.objects.create(
            contact=self.contact,
            caller=self.user,
            project=self.project,
            status="pending",
            call_result="interested",
            duration=120
        )
        history = CallEditHistory.objects.first()
        self.assertEqual(history.field_name, "initial_save")

class CallAnswerModelTest(TestCase):
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

    def test_create_call_answer(self):
        call_answer = CallAnswer.objects.create(
            call=self.call,
            question=self.question,
            selected_choice=self.answer_choice
        )
        self.assertEqual(call_answer.call, self.call)
        self.assertEqual(call_answer.question.text, "Did you like the service?")
        self.assertEqual(call_answer.selected_choice.text, "Yes")
