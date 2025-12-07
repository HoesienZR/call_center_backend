import uuid

import pandas as pd
from django.contrib.auth import get_user_model

from contacts.models import Contact
from projects.models import Project
from .utils import is_caller_user, clean_string_field

User = get_user_model()


def import_contacts_from_excel(file_obj, project: Project):
    created_contacts = []

    # --- فایل را بخوان ---
    try:
        df = pd.read_excel(file_obj, dtype=str)
    except Exception:
        df = pd.read_csv(file_obj, dtype=str)

    # --- بررسی ستون‌های ضروری ---
    required_columns = ["full_name", "contact_phone"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"ستون '{col}' در فایل موجود نیست.")

    for _, row in df.iterrows():
        full_name = clean_string_field(row.get("full_name", "نامشخص"))

        # phone
        raw_phone = row.get("contact_phone")
        if raw_phone:
            phone = clean_string_field(raw_phone)
        else:
            phone = f"unknown_{uuid.uuid4().hex[:8]}"

        phone = str(phone)

        # اگر شماره عددی بود و 0 نداشت → صفر اضافه شود
        if phone.isdigit() and not phone.startswith("0") and len(phone) in (9, 10):
            phone = "0" + phone

        # --- assigned caller ---
        assigned_caller = None
        is_special = False

        assigned_caller_phone = clean_string_field(row.get("assigned_caller_phone", ""))

        if assigned_caller_phone:
            # اگر بدون صفر بود، صفر اضافه شود
            if not assigned_caller_phone.startswith("0"):
                assigned_caller_phone = "0" + assigned_caller_phone

            try:
                caller = User.objects.get(phone_number=assigned_caller_phone)

                # فقط اگر نقش تماس‌گیرنده در پروژه دارد
                if is_caller_user(caller, project):
                    assigned_caller = caller
                    is_special = True

            except User.DoesNotExist:
                assigned_caller = None
                is_special = False

        contact = Contact.objects.create(
            project=project,
            full_name=full_name,
            phone=phone,
            assigned_caller=assigned_caller,
            is_special=is_special
        )

        created_contacts.append(contact.phone)

    return created_contacts
