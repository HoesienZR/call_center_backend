import uuid

import pandas as pd
from django.contrib.auth import get_user_model

from .models import Contact, Project, ProjectCaller
from .utils import is_caller_user, clean_string_field

User = get_user_model()


def import_callers_from_excel(file_obj):
    """
    Process an Excel or CSV file and create caller users.
    Required columns: username, first_name, last_name, phone
    """
    created_callers = []

    # Try loading Excel first, fallback to CSV
    try:
        df = pd.read_excel(file_obj, dtype=str)
    except Exception:
        df = pd.read_csv(file_obj, dtype=str)

    required_columns = ["username", "first_name", "last_name", "phone"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' is missing in the file.")

    for index, row in df.iterrows():
        username = clean_string_field(row.get("username", f"user_{uuid.uuid4().hex[:8]}"))
        first_name = clean_string_field(row.get("first_name", ""))
        last_name = clean_string_field(row.get("last_name", ""))
        phone = str(clean_string_field(row.get("phone", f"unknown_{uuid.uuid4().hex[:8]}")))

        # Create or update the user
        user, created = User.objects.get_or_create(username=username)
        user.first_name = first_name
        user.last_name = last_name
        user.phone_number = phone
        user.save()

        # Ensure user is recognized as a caller
        if not is_caller_user(user):
            ProjectCaller.objects.get_or_create(caller=user)

        if created:
            created_callers.append(user.username)

    return created_callers


def import_contacts_from_excel(file_obj, project: Project):
    """
    Process an Excel or CSV file and create contacts for the given project.
    Required columns: full_name, contact_phone
    Optional column: assigned_caller_phone
    """
    created_contacts = []

    # Try loading Excel first, fallback to CSV
    try:
        df = pd.read_excel(file_obj, dtype=str)
    except Exception:
        df = pd.read_csv(file_obj, dtype=str)

    required_columns = ["full_name", "contact_phone"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' is missing in the file.")

    for index, row in df.iterrows():
        full_name = clean_string_field(row.get("full_name", "Unknown"))
        phone = str(clean_string_field(row.get("contact_phone", f"unknown_{uuid.uuid4().hex[:8]}")))
        assigned_caller_phone = clean_string_field(row.get("assigned_caller_phone", ""))

        # Normalize phone number: add leading 0 if missing and length is valid
        if phone.isdigit() and not phone.startswith("0") and len(phone) in (9, 10):
            phone = "0" + phone

        assigned_caller = None
        is_special = False

        # Find assigned caller by phone number
        if assigned_caller_phone:
            if assigned_caller_phone.isdigit() and not assigned_caller_phone.startswith("0"):
                assigned_caller_phone = "0" + assigned_caller_phone

            try:
                caller = User.objects.get(phone_number=assigned_caller_phone)

                # Only assign if user is a valid caller for the project
                if is_caller_user(caller, project):
                    assigned_caller = caller
                    is_special = True

            except User.DoesNotExist:
                assigned_caller = None
                is_special = False

        # Create the contact associated with the project
        contact = Contact.objects.create(
            project=project,
            full_name=full_name,
            phone=phone,
            assigned_caller=assigned_caller,
            is_special=is_special
        )

        created_contacts.append(contact.phone)

    return created_contacts
