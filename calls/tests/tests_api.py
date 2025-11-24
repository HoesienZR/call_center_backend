from rest_framework.test import APIClient
from rest_framework import status
from django.test import TestCase
from django.urls import reverse
from calls.models import Call, Contact, Project
from django.contrib.auth import get_user_model


User = get_user_model()


class CallAPITest(TestCase):
    def setUp(self):
        """ تنظیمات اولیه برای تست‌ها """
        self.client = APIClient()

        # ایجاد کاربران تست
        self.user = User.objects.create_user(username="caller", password="password123")

        # ایجاد مخاطب تست
        self.contact = Contact.objects.create(full_name="Test Contact", phone="123456789")

        # ایجاد پروژه تست
        self.project = Project.objects.create(name="Test Project", created_by=self.user)

    def test_create_call(self):
        """تست ایجاد یک تماس جدید"""
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
        self.assertEqual(response.data['contact'], self.contact.id)

    def test_get_calls(self):
        """تست دریافت لیست تماس‌ها"""
        url = reverse('call-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_edit_call(self):
        """تست ویرایش یک تماس"""
        # ابتدا یک تماس ایجاد می‌کنیم تا ID آن برای ویرایش استفاده شود
        call = Call.objects.create(
            contact=self.contact,
            caller=self.user,
            project=self.project,
            status="pending",
            call_result="interested",
            duration=120
        )

        url = reverse('call-detail', kwargs={'pk': call.id})  # استفاده از ID تماس ایجاد شده
        data = {"status": "completed", "notes": "The call was successful."}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], "completed")
        self.assertEqual(response.data['notes'], "The call was successful.")
