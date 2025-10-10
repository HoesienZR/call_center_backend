from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status

class AuthenticationTestCase(TestCase):
    """تست‌های سیستم احراز هویت"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.token = Token.objects.create(user=self.user)

    def test_login_success(self):
        """تست ورود موفقیت‌آمیز"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_login_invalid_credentials(self):
        """تست ورود با اطلاعات نادرست"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_with_token(self):
        """تست دریافت پروفایل با توکن"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

    def test_profile_without_token(self):
        """تست دریافت پروفایل بدون توکن"""
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProjectModelTestCase(TestCase):
    """تست‌های مدل Project"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.project = Project.objects.create(
            name='Test Project',
            description='Test Description',
            status='active',
            created_by=self.user
        )

    def test_project_creation(self):
        """تست ایجاد پروژه"""
        self.assertEqual(self.project.name, 'Test Project')
        self.assertEqual(self.project.status, 'active')
        self.assertEqual(self.project.created_by, self.user)

    def test_project_str(self):
        """تست نمایش رشته‌ای پروژه"""
        self.assertEqual(str(self.project), 'Test Project')


class ContactModelTestCase(TestCase):
    """تست‌های مدل Contact"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.project = Project.objects.create(
            name='Test Project',
            description='Test Description',
            status='active',
            created_by=self.user
        )
        self.contact = Contact.objects.create(
            project=self.project,
            full_name='John Doe',
            phone='09123456789',
            email='john@example.com'
        )

    def test_contact_creation(self):
        """تست ایجاد مخاطب"""
        self.assertEqual(self.contact.full_name, 'John Doe')
        self.assertEqual(self.contact.phone, '09123456789')

    def test_contact_str(self):
        """تست نمایش رشته‌ای مخاطب"""
        self.assertEqual(str(self.contact), 'John Doe - 09123456789')


class ProjectAPITestCase(TestCase):
    """تست‌های API پروژه"""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
        self.token = Token.objects.create(user=self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.project = Project.objects.create(
            name='Test Project',
            description='Test Description',
            status='active',
            created_by=self.admin_user
        )

    def test_list_projects(self):
        """تست دریافت لیست پروژه‌ها"""
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_create_project(self):
        """تست ایجاد پروژه"""
        data = {
            'name': 'New Project',
            'description': 'New Description',
            'status': 'active'
        }
        response = self.client.post('/api/projects/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Project')
        self.assertEqual(response.data['created_by']['id'], self.admin_user.id)

    def test_project_statistics(self):
        """تست آمار پروژه"""
        response = self.client.get(f'/api/projects/{self.project.id}/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_contacts', response.data)


class ContactAPITestCase(TestCase):
    """تست‌های API مخاطبین"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='caller',
            password='caller123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.project = Project.objects.create(
            name='Test Project',
            description='Test Description',
            status='active',
            created_by=self.user
        )

        ProjectCaller.objects.create(
            project=self.project,
            caller=self.user,
            is_active=True
        )

        self.contact = Contact.objects.create(
            project=self.project,
            full_name='John Doe',
            phone='09123456789',
            email='john@example.com',
            call_status='pending'
        )

    def test_list_contacts(self):
        """تست دریافت لیست مخاطبین"""
        response = self.client.get('/api/contacts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_request_new_call(self):
        """تست درخواست تماس جدید"""
        response = self.client.post('/api/contacts/request_new_call/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)



# call_center/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from io import BytesIO
import pandas as pd

from .models import Project, Contact, ProjectCaller
from .excel_imports import import_callers_from_excel, import_contacts_from_excel

class ExcelImportTestCase(TestCase):

    def setUp(self):
        # ایجاد پروژه تستی
        self.project = Project.objects.create(name="Test Project", created_by=User.objects.create(username="admin"))

    def test_import_callers_and_contacts(self):
        # ساخت فایل اکسل تماس‌گیرندگان در حافظه
        callers_data = pd.DataFrame({
            "username": ["caller1", "caller2"],
            "first_name": ["Ali", "Sara"],
            "last_name": ["Ahmadi", "Mohammadi"],
            "phone": ["09120000001", "09120000002"]
        })
        callers_file = BytesIO()
        callers_data.to_excel(callers_file, index=False)
        callers_file.seek(0)

        created_callers = import_callers_from_excel(callers_file)
        self.assertIn("caller1", created_callers)
        self.assertIn("caller2", created_callers)

        # بررسی اینکه کاربران در دیتابیس ساخته شده‌اند
        caller1 = User.objects.get(username="caller1")
        caller2 = User.objects.get(username="caller2")
        self.assertEqual(caller1.first_name, "Ali")
        self.assertEqual(caller2.first_name, "Sara")

        # ساخت فایل اکسل مخاطبین در حافظه
        contacts_data = pd.DataFrame({
            "full_name": ["Ali Reza", "Sara Ahmadi"],
            "phone": ["09331000001", "09331000002"],
            "assigned_caller_username": ["caller1", "caller2"]
        })
        contacts_file = BytesIO()
        contacts_data.to_excel(contacts_file, index=False)
        contacts_file.seek(0)

        created_contacts = import_contacts_from_excel(contacts_file, self.project)
        self.assertIn("09331000001", created_contacts)
        self.assertIn("09331000002", created_contacts)

        # بررسی اینکه مخاطبین به درستی ساخته شده‌اند و اختصاص داده شده‌اند
        ali = Contact.objects.get(phone="09331000001")
        sara = Contact.objects.get(phone="09331000002")
        self.assertEqual(ali.full_name, "Ali Reza")
        self.assertEqual(ali.assigned_caller, caller1)
        self.assertEqual(sara.assigned_caller, caller2)
        self.assertEqual(sara.full_name, "Sara Ahmadi")
