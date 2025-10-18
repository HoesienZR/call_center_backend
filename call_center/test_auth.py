#!/usr/bin/.env python3
"""
فایل تست برای سیستم احراز هویت Token Authentication
"""

import requests
import json

# تنظیمات
BASE_URL = ""
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def test_login():
    """تست ورود کاربر"""
    print("=== تست ورود کاربر ===")
    
    login_data = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }
    
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        token = response.json().get('token')
        print(f"Token دریافت شد: {token}")
        return token
    else:
        print("خطا در ورود")
        return None

def test_api_with_token(token):
    """تست دسترسی به API با توکن"""
    print("\n=== تست دسترسی به API با توکن ===")
    
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }
    
    # تست دریافت لیست پروژه‌ها
    response = requests.get(f"{BASE_URL}/projects/", headers=headers)
    print(f"GET /projects/ - Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("دسترسی به API موفقیت‌آمیز بود")
        print(f"تعداد پروژه‌ها: {len(response.json().get('results', []))}")
    else:
        print(f"خطا در دسترسی به API: {response.text}")

def test_api_without_token():
    """تست دسترسی به API بدون توکن"""
    print("\n=== تست دسترسی به API بدون توکن ===")
    
    response = requests.get(f"{BASE_URL}/projects/")
    print(f"GET /projects/ بدون توکن - Status Code: {response.status_code}")
    
    if response.status_code == 401 or response.status_code == 403:
        print("به درستی دسترسی رد شد (انتظار می‌رفت)")
    else:
        print("مشکل: دسترسی بدون توکن امکان‌پذیر است!")

def test_user_profile(token):
    """تست دریافت پروفایل کاربر"""
    print("\n=== تست دریافت پروفایل کاربر ===")
    
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{BASE_URL}/auth/profile/", headers=headers)
    print(f"GET /auth/profile/ - Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"پروفایل کاربر: {response.json()}")
    else:
        print(f"خطا در دریافت پروفایل: {response.text}")

def main():
    """تابع اصلی تست"""
    print("شروع تست سیستم احراز هویت Token Authentication")
    print("=" * 50)
    
    # تست ورود
    token = test_login()
    
    if token:
        # تست دسترسی با توکن
        test_api_with_token(token)
        
        # تست پروفایل کاربر
        test_user_profile(token)
    
    # تست دسترسی بدون توکن
    test_api_without_token()
    
    print("\n" + "=" * 50)
    print("تست‌ها تمام شد")

if __name__ == "__main__":
    main()

