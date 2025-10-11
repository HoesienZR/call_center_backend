#!/usr/bin/.env python3
"""
تست جامع برای سیستم Call Center Backend
"""

import os
import sys
import django
import requests
import json
from datetime import datetime, timedelta

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'call_center_backend.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from call_center.models import Project, Contact, Call, ProjectCaller


class CallCenterAPITestCase(TestCase):
    """کلاس پایه برای تست‌های API"""
    
    def setUp(self):
        """تنظیمات اولیه برای تست‌ها"""
        # ایجاد کاربران تست
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='admin123',
            email='admin@test.com',
            is_staff=True,
            is_superuser=True
        )
        
        self.caller_user = User.objects.create_user(
            username='caller_test',
            password='caller123',
            email='caller@test.com',
            is_staff=False
        )
        
        # ایجاد توکن‌ها
        self.admin_token = Token.objects.create(user=self.admin_user)
        self.caller_token = Token.objects.create(user=self.caller_user)
        
        # ایجاد کلاینت API
        self.client = APIClient()
        
        # ایجاد پروژه تست
        self.test_project = Project.objects.create(
            name='پروژه تست',
            description='این یک پروژه تست است',
            status='active',
            created_by=self.admin_user
        )
        
        # تخصیص تماس‌گیرنده به پروژه
        ProjectCaller.objects.create(
            project=self.test_project,
            caller=self.caller_user,
            is_active=True
        )
        
        # ایجاد مخاطبین تست
        self.test_contact = Contact.objects.create(
            project=self.test_project,
            first_name='علی',
            last_name='احمدی',
            phone_number='09123456789',
            email='ali@test.com',
            call_status='pending'
        )

    def authenticate_admin(self):
        """احراز هویت به عنوان ادمین"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')

    def authenticate_caller(self):
        """احراز هویت به عنوان تماس‌گیرنده"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.caller_token.key}')

    def clear_authentication(self):
        """حذف احراز هویت"""
        self.client.credentials()


class AuthenticationTestCase(CallCenterAPITestCase):
    """تست‌های سیستم احراز هویت"""
    
    def test_login_success(self):
        """تست ورود موفقیت‌آمیز"""
        response = self.client.post('/api/auth/login/', {
            'username': 'admin_test',
            'password': 'admin123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['username'], 'admin_test')

    def test_login_invalid_credentials(self):
        """تست ورود با اطلاعات نادرست"""
        response = self.client.post('/api/auth/login/', {
            'username': 'admin_test',
            'password': 'wrong_password'
        })
        self.assertEqual(response.status_code, 401)

    def test_profile_with_token(self):
        """تست دریافت پروفایل با توکن"""
        self.authenticate_admin()
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'admin_test')

    def test_profile_without_token(self):
        """تست دریافت پروفایل بدون توکن"""
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, 401)

    def test_logout(self):
        """تست خروج"""
        self.authenticate_admin()
        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 200)


class ProjectAPITestCase(CallCenterAPITestCase):
    """تست‌های API پروژه"""
    
    def test_list_projects_admin(self):
        """تست دریافت لیست پروژه‌ها توسط ادمین"""
        self.authenticate_admin()
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_list_projects_caller(self):
        """تست دریافت لیست پروژه‌ها توسط تماس‌گیرنده"""
        self.authenticate_caller()
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, 200)

    def test_create_project_admin(self):
        """تست ایجاد پروژه توسط ادمین"""
        self.authenticate_admin()
        response = self.client.post('/api/projects/', {
            'name': 'پروژه جدید',
            'description': 'توضیحات پروژه جدید',
            'status': 'active'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'پروژه جدید')

    def test_project_statistics(self):
        """تست دریافت آمار پروژه"""
        self.authenticate_admin()
        response = self.client.get(f'/api/projects/{self.test_project.id}/statistics/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_contacts', response.data)
        self.assertIn('total_calls', response.data)


class ContactAPITestCase(CallCenterAPITestCase):
    """تست‌های API مخاطبین"""
    
    def test_list_contacts_admin(self):
        """تست دریافت لیست مخاطبین توسط ادمین"""
        self.authenticate_admin()
        response = self.client.get('/api/contacts/')
        self.assertEqual(response.status_code, 200)

    def test_list_contacts_caller(self):
        """تست دریافت لیست مخاطبین توسط تماس‌گیرنده"""
        self.authenticate_caller()
        response = self.client.get('/api/contacts/')
        self.assertEqual(response.status_code, 200)

    def test_request_new_call(self):
        """تست درخواست تماس جدید"""
        self.authenticate_caller()
        response = self.client.post('/api/contacts/request_new_call/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('id', response.data)


class CallAPITestCase(CallCenterAPITestCase):
    """تست‌های API تماس‌ها"""
    
    def setUp(self):
        super().setUp()
        # ایجاد تماس تست
        self.test_call = Call.objects.create(
            contact=self.test_contact,
            caller=self.caller_user,
            call_date=datetime.now(),
            duration=300,
            status='completed'
        )

    def test_list_calls_admin(self):
        """تست دریافت لیست تماس‌ها توسط ادمین"""
        self.authenticate_admin()
        response = self.client.get('/api/calls/')
        self.assertEqual(response.status_code, 200)

    def test_list_calls_caller(self):
        """تست دریافت لیست تماس‌ها توسط تماس‌گیرنده"""
        self.authenticate_caller()
        response = self.client.get('/api/calls/')
        self.assertEqual(response.status_code, 200)

    def test_submit_feedback(self):
        """تست ثبت بازخورد"""
        self.authenticate_caller()
        response = self.client.post(f'/api/calls/{self.test_call.id}/submit_feedback/', {
            'feedback_text': 'تماس موفقیت‌آمیز بود',
            'call_status': 'successful'
        })
        self.assertEqual(response.status_code, 200)

    def test_submit_detailed_report(self):
        """تست ثبت گزارش تفصیلی"""
        self.authenticate_caller()
        response = self.client.post(f'/api/calls/{self.test_call.id}/submit_detailed_report/', {
            'report_data': {'notes': 'گزارش تفصیلی تماس', 'outcome': 'positive'},
            'call_status': 'successful'
        })
        self.assertEqual(response.status_code, 200)


class ExportTestCase(CallCenterAPITestCase):
    """تست‌های اکسپورت گزارش‌ها"""
    
    def test_export_project_statistics(self):
        """تست اکسپورت آمار پروژه"""
        self.authenticate_admin()
        response = self.client.get(f'/api/projects/{self.test_project.id}/export_report/', {
            'report_type': 'project_statistics',
            'format': 'xlsx'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('download_url', response.data)

    def test_export_caller_performance(self):
        """تست اکسپورت عملکرد تماس‌گیرندگان"""
        self.authenticate_admin()
        response = self.client.get(f'/api/projects/{self.test_project.id}/export_report/', {
            'report_type': 'caller_performance',
            'format': 'csv'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('download_url', response.data)


def run_manual_tests():
    """اجرای تست‌های دستی با استفاده از requests"""
    print("=== شروع تست‌های دستی ===")
    
    BASE_URL = "http://127.0.0.1:8000/api"
    
    # تست ورود
    print("\n1. تست ورود...")
    login_response = requests.post(f"{BASE_URL}/auth/login/", json={
        "username": "admin",
        "password": "admin123"
    })
    
    if login_response.status_code == 200:
        token = login_response.json().get('token')
        print(f"✅ ورود موفقیت‌آمیز. Token: {token[:20]}...")
        
        headers = {"Authorization": f"Token {token}"}
        
        # تست دریافت پروژه‌ها
        print("\n2. تست دریافت پروژه‌ها...")
        projects_response = requests.get(f"{BASE_URL}/projects/", headers=headers)
        if projects_response.status_code == 200:
            print(f"✅ دریافت پروژه‌ها موفقیت‌آمیز. تعداد: {len(projects_response.json().get('results', []))}")
        else:
            print(f"❌ خطا در دریافت پروژه‌ها: {projects_response.status_code}")
        
        # تست دریافت مخاطبین
        print("\n3. تست دریافت مخاطبین...")
        contacts_response = requests.get(f"{BASE_URL}/contacts/", headers=headers)
        if contacts_response.status_code == 200:
            print(f"✅ دریافت مخاطبین موفقیت‌آمیز. تعداد: {len(contacts_response.json().get('results', []))}")
        else:
            print(f"❌ خطا در دریافت مخاطبین: {contacts_response.status_code}")
        
        # تست دریافت تماس‌ها
        print("\n4. تست دریافت تماس‌ها...")
        calls_response = requests.get(f"{BASE_URL}/calls/", headers=headers)
        if calls_response.status_code == 200:
            print(f"✅ دریافت تماس‌ها موفقیت‌آمیز. تعداد: {len(calls_response.json().get('results', []))}")
        else:
            print(f"❌ خطا در دریافت تماس‌ها: {calls_response.status_code}")
        
        print("\n=== پایان تست‌های دستی ===")
    else:
        print(f"❌ خطا در ورود: {login_response.status_code}")


if __name__ == "__main__":
    print("انتخاب نوع تست:")
    print("1. تست‌های Django (Unit/Integration)")
    print("2. تست‌های دستی (Manual)")
    print("3. هر دو")
    
    choice = input("انتخاب کنید (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        print("\n=== اجرای تست‌های Django ===")
        import unittest
        
        # ایجاد test suite
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # اضافه کردن تست‌ها
        suite.addTests(loader.loadTestsFromTestCase(AuthenticationTestCase))
        suite.addTests(loader.loadTestsFromTestCase(ProjectAPITestCase))
        suite.addTests(loader.loadTestsFromTestCase(ContactAPITestCase))
        suite.addTests(loader.loadTestsFromTestCase(CallAPITestCase))
        suite.addTests(loader.loadTestsFromTestCase(ExportTestCase))
        
        # اجرای تست‌ها
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        print(f"\n=== نتایج تست‌های Django ===")
        print(f"تعداد کل تست‌ها: {result.testsRun}")
        print(f"موفقیت‌آمیز: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"شکست‌خورده: {len(result.failures)}")
        print(f"خطا: {len(result.errors)}")
    
    if choice in ['2', '3']:
        print("\n=== اجرای تست‌های دستی ===")
        run_manual_tests()

