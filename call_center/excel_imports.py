# call_center/excel_imports.py
import pandas as pd
import uuid
from django.contrib.auth import get_user_model
from django.contrib.messages.apps import update_level_tags

from .models import Contact, Project, ProjectCaller
from .utils import is_caller_user, clean_string_field
from datetime import datetime

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
        if phone.startswith("+98"):
            phone = "0"+phone[3:]
        elif phone.startswith("9"):
            phone = "0"+phone
        user, created = User.objects.get_or_create(username=username)
        user.first_name = first_name
        user.last_name = last_name
        user.phone = phone
        user.save()
        # مطمئن شدن که این کاربر تماس‌گیرنده است
        if not is_caller_user(user):
            ProjectCaller.objects.get_or_create(caller=user)  # اضافه شدن به جدول تماس‌گیرنده‌ها

        if created:
            created_callers.append(user.username)

    return created_callers


def import_contacts_from_excel(file_obj, project: Project):
    created_contacts_count = 0
    updated_contacts_count = 0
    gender_map = {
        "مرد": "male",
        "زن": "female",
        "ترجیح میدهم که نگویم": "none",
        "": "none",
        None: "none",
        "آقا": "male",
        "خانم": "female",

    }
    """
    اکسل مخاطبین را پردازش و مخاطبین پروژه ایجاد می‌کند.
    فرمت: full_name, phone, assigned_caller_username (اختیاری)
    """
    created_contacts = []
    try:
        df = pd.read_excel(file_obj, dtype=str)
    except Exception:
        df = pd.read_csv(file_obj, dtype=str)


    required_columns = ["نام و نام خانوادگی", "شماره تماس"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"ستون '{col}' در فایل موجود نیست.")
    for index, row in df.iterrows():
        full_name = clean_string_field(row.get("نام و نام خانوادگی", "نامشخص"))
        raw_phone = clean_string_field(row.get("شماره تماس", "")).strip()

        assigned_caller_phone = clean_string_field(row.get("شماره تماس گیرنده مربوطه", ""))
        custom_fields = clean_string_field(row.get('فیلد سفارشی',""))
        if clean_string_field(row.get('جنسیت',"")) is None:
            gender_raw = None
        else :
            gender_raw = clean_string_field(row.get('جنسیت',"")).strip()
        gender = gender_map.get(gender_raw)
        #here is Inconsistency for database callculate age for uer and then save it as date
        age  = clean_string_field(row.get('سن',""))
        if age :
            try:
                age = int(age)
            except  ValueError :
                age =  None
        if age and  0 <= age <= 100  :
            birth_date_year = datetime.now().year - age
            birth_date = datetime(year=birth_date_year, month=1, day=1)
        else :
            birth_date = None

        address = clean_string_field(row.get('آدرس',''))
        if not raw_phone:
            continue


        if raw_phone.isdigit() and not raw_phone.startswith("0") and len(raw_phone) in (9, 10):
            raw_phone = "0" + raw_phone
        phone = raw_phone
        assigned_caller = None
        is_special = False
        if age :
            try :
                birth_date = pd.to_datetime(age).date()
            except Exception :
                birth_date = None



        if assigned_caller_phone and not assigned_caller_phone.startswith("0"):
            assigned_caller_phone = "0" + assigned_caller_phone
            try:
                caller = User.objects.get(phone_number=assigned_caller_phone)
                if is_caller_user(caller, project):
                    assigned_caller = caller
                    is_special = True
            except User.DoesNotExist:
                assigned_caller = None
                is_special = False
        contact, created = Contact.objects.update_or_create(
            project=project,
            phone=phone,
            defaults={
                "full_name": full_name,
                "assigned_caller": assigned_caller,
                "is_special": is_special,
                "custom_fields": custom_fields,
                "address": address,
                "gender": gender,
                "birth_date": birth_date,
            }
        )
        if created:
            created_contacts_count += 1
        else:
            updated_contacts_count += 1

        created_contacts.append(contact.phone)

    return created_contacts,created_contacts_count,updated_contacts_count

