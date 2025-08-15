from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status
from .models import Project, Contact, Call, ProjectCaller


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
