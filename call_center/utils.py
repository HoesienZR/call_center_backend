import re
import random
from django.contrib.auth.models import User
from .models import Contact, ProjectMembership
from django.db.models import Count

import string

def validate_phone_number(phone):
    """
    اعتبارسنجی شماره تلفن
    فرمت‌های مجاز: 09123456789, +989123456789, 00989123456789
    """
    if not phone:
        return False, "شماره تلفن خالی است"

    # حذف فاصله‌ها و کاراکترهای اضافی
    phone = re.sub(r'[\s\-\(\)]', '', phone)

    # بررسی فرمت‌های مختلف شماره تلفن ایرانی
    patterns = [
        r'^09\d{9}$',  # 09123456789
        r'^\+989\d{9}$',  # +989123456789
        r'^00989\d{9}$',  # 00989123456789
    ]

    for pattern in patterns:
        if re.match(pattern, phone):
            return True, phone

    return False, "فرمت شماره تلفن نامعتبر است"


def normalize_phone_number(phone):
    """
    نرمال‌سازی شماره تلفن به فرمت استاندارد 09xxxxxxxxx
    """
    if not phone:
        return phone

    # حذف فاصله‌ها و کاراکترهای اضافی
    phone = re.sub(r'[\s\-\(\)]', '', phone)

    # تبدیل به فرمت استاندارد
    if phone.startswith('+98'):
        phone = '0' + phone[3:]
    elif phone.startswith('0098'):
        phone = '0' + phone[4:]
    elif phone.startswith('98') and len(phone) == 12:
        phone = '0' + phone[2:]

    return phone

def generate_username(phone):
    random_letters = random.choice((string.punctuation))+phone

    for _ in range(4):
        random_letters += random.choice(string.ascii_letters)
    return random_letters


def generate_secure_password(length=12):
    """
    تولید رمز عبور امن
    """

    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(characters) for _ in range(length))


def is_caller_user(user, project=None):
    """
    بررسی اینکه آیا کاربر یک تماس‌گیرنده است یا خیر
    تماس‌گیرندگان: کاربرانی که is_staff=False و is_superuser=False هستند
    """
    if user.is_staff:
        return True
    if project:
        return ProjectMembership.objects.filter(user=user, project=project, role="caller").exists()
    return ProjectMembership.objects.filter(user=user, role="caller").exists()



def validate_excel_data(df, required_columns, optional_columns=None):
    """
    اعتبارسنجی داده‌های اکسل
    """
    if optional_columns is None:
        optional_columns = []

    errors = []

    # بررسی وجود ستون‌های الزامی
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"ستون‌های الزامی یافت نشد: {', '.join(missing_columns)}")

    # بررسی خالی نبودن DataFrame
    if df.empty:
        errors.append("فایل خالی است")

    return errors


def clean_string_field(value):
    """
    تمیز کردن فیلدهای متنی
    """
    if value is None or str(value).strip().lower() in ['nan', 'none', '']:
        return None
    return str(value).strip()


