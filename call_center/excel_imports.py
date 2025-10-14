# call_center/excel_imports.py
import pandas as pd
import uuid
from django.contrib.auth import get_user_model
from .models import Contact, Project, ProjectCaller
from .utils import is_caller_user, clean_string_field

User = get_user_model()

def import_callers_from_excel(file_obj):
    """
    اکسل تماس‌گیرندگان را پردازش و کاربران تماس‌گیرنده ایجاد می‌کند.
    فرمت: ستون username, first_name, last_name, phone
    """
    created_callers = []
    try:
        df = pd.read_excel(file_obj, dtype=str)
    except Exception:
        df = pd.read_csv(file_obj, dtype=str)

    required_columns = ["username", "first_name", "last_name", "phone"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"ستون '{col}' در فایل موجود نیست.")

    for index, row in df.iterrows():
        username = clean_string_field(row.get("username", f"user_{uuid.uuid4().hex[:8]}"))
        first_name = clean_string_field(row.get("first_name", ""))
        last_name = clean_string_field(row.get("last_name", ""))
        phone = str(clean_string_field(row.get("phone", f"unknown_{uuid.uuid4().hex[:8]}")))

        user, created = User.objects.get_or_create(username=username)
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        # مطمئن شدن که این کاربر تماس‌گیرنده است
        if not is_caller_user(user):
            ProjectCaller.objects.get_or_create(caller=user)  # اضافه شدن به جدول تماس‌گیرنده‌ها

        if created:
            created_callers.append(user.username)

    return created_callers


def import_contacts_from_excel(file_obj, project: Project):
    """
    اکسل مخاطبین را پردازش و مخاطبین پروژه ایجاد می‌کند.
    فرمت: full_name, phone, assigned_caller_username (اختیاری)
    """
    created_contacts = []
    try:
        df = pd.read_excel(file_obj, dtype=str)
    except Exception:
        df = pd.read_csv(file_obj, dtype=str)

    # ستون‌های ضروری: نام و شماره
    required_columns = ["full_name", "phone"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"ستون '{col}' در فایل موجود نیست.")

    for index, row in df.iterrows():
        full_name = clean_string_field(row.get("full_name", "نامشخص"))
        phone = str(clean_string_field(row.get("phone", f"unknown_{uuid.uuid4().hex[:8]}")))
        assigned_caller_username = clean_string_field(row.get("assigned_caller_username", ""))

        contact = Contact(
            project=project,
            full_name=full_name,
            phone=phone
        )

        # بررسی وجود تماس‌گیرنده در سیستم
        if assigned_caller_username:
            try:
                caller = User.objects.get(username=assigned_caller_username)
                if is_caller_user(caller):
                    contact.assigned_caller = caller
                    contact.is_special = True  # ✅ یعنی از اکسل با تماس‌گیرنده آمده
            except User.DoesNotExist:
                contact.assigned_caller = None
                contact.is_special = False
        else:
            contact.assigned_caller = None
            contact.is_special = False      # اگر ستون خالی بود → بدون تماس‌گیرنده

        contact.save()
        created_contacts.append(contact.phone)

    return created_contacts

