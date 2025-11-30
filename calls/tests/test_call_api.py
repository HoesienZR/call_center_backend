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
        self.user1 = User.objects.create_user(username="caller1", phone_number="1000000001", password="password1")
        self.user2 = User.objects.create_user(username="caller2", phone_number="1000000002", password="password2")
        self.admin_user = User.objects.create_superuser(username="admin", phone_number="1000000000",
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

    def test_submit_call(self):
        self.client.force_authenticate(user=self.user2)

        data = {
            "contact_id": self.contact.id,
            "project_id": self.project.id,
            "caller_id": self.user2.id,
            "status": "pending",
            "call_result": "interested",
            "notes": "Test notes",
            "duration": 90,
            "follow_up_date": None
        }

        response = self.client.post("/api/calls/submit_call/", data, format="json")
        print(response.data)
        # بررسی وضعیت HTTP
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # بررسی فیلدهای اصلی
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["call_result"], "interested")
        self.assertEqual(response.data["duration"], 90)
        self.assertEqual(response.data["contact"]["id"], self.contact.id)
        self.assertEqual(response.data["project"], self.project.id)
        self.assertEqual(response.data["caller"]["id"], self.user2.id)

        # بررسی فیلدهای پیش‌فرض
        self.assertEqual(response.data["notes"], "Test notes")
        self.assertFalse(response.data["follow_up_required"])
        self.assertIsNone(response.data.get("follow_up_date"))

    def test_edit_call(self):
        self.client.force_authenticate(user=self.admin_user)

        data = {
            "notes": "Updated notes",
            "edit_reason": "Testing edit",
            "project_id": self.call.project.id
        }

        response = self.client.post(f"/api/calls/{self.call.id}/edit_call/", data, format="json")
        print(response.data)  # برای بررسی داده برگشتی

        # بررسی وضعیت HTTP
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # بروزرسانی call از DB
        self.call.refresh_from_db()

        # بررسی فیلدهای اصلی ویرایش شده
        self.assertEqual(self.call.notes, "Updated notes")

        # بررسی اینکه edit_reason ذخیره شده
        self.assertEqual(self.call.edit_reason, "Testing edit")

        # بررسی اینکه edited_by ست شده
        self.assertEqual(self.call.edited_by, self.admin_user)

        # بررسی اینکه edited_at ست شده
        self.assertIsNotNone(self.call.edited_at)

    def test_submit_feedback(self):
        self.client.force_authenticate(user=self.user1)
        data = {"notes": "Great call", "status": "pending"}
        response = self.client.post(f"/api/calls/{self.call.id}/submit_feedback/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.call.refresh_from_db()
        self.assertEqual(self.call.feedback, "Great call")
        self.assertEqual(self.call.status, "pending")

    def test_submit_detailed_report(self):
        self.client.force_authenticate(user=self.user1)
        data = {"report_data": "Detailed report content", "call_status": "pending"}
        response = self.client.post(f"/api/calls/{self.call.id}/submit_detailed_report/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.call.refresh_from_db()
        self.assertEqual(self.call.detailed_report, "Detailed report content")
        self.assertEqual(self.call.status, "pending")

    def test_call_edit_history_list(self):
        CallEditHistory.objects.create(call=self.call, edited_by=self.user1, field_name="notes",
                                       old_value="", new_value="Initial edit", edit_reason="Test")
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/call-edit-history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
