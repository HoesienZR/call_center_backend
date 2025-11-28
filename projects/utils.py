import pandas as pd
from django.contrib.auth import get_user_model
from django.db import transaction

from contacts.models import Contact
from projects.models import Project, ProjectMembership

User = get_user_model()


def is_caller_user(user, project=None):
    """
    Check whether a given user is a caller.
    A caller is a user who is not staff and is not a superuser.
    """
    if user.is_staff or user.is_superuser:
        return False

    if project:
        return ProjectMembership.objects.filter(
            user=user,
            project=project,
            role="caller"
        ).exists()

    return ProjectMembership.objects.filter(user=user, role="caller").exists()


def clean_string_field(value):
    """
    Clean string-like fields.
    Convert '', None, 'nan', 'none' → None.
    """
    if value is None:
        return None

    v = str(value).strip().lower()
    if v in ['', 'nan', 'none']:
        return None

    return str(value).strip()


def import_caller_from_excel(file_obj, project: Project):
    """
    Import callers from Excel or CSV.
    Create the user if not existing.
    Add user to project as caller.
    """
    new_callers = []

    # Read Excel or fallback to CSV
    try:
        df = pd.read_excel(file_obj, dtype=str)
    except Exception:
        df = pd.read_csv(file_obj, dtype=str)

    required_columns = ["name", "last_name", "phone_number"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' is missing from the file.")

    for _, row in df.iterrows():

        name = clean_string_field(row.get("name")) or "Unknown"
        last_name = clean_string_field(row.get("last_name")) or "Unknown"
        phone_number = clean_string_field(row.get("phone_number"))

        if not phone_number:
            continue

        # Normalize phone format
        phone_number = str(phone_number)
        if phone_number.isdigit() and not phone_number.startswith("0") and len(phone_number) in (9, 10):
            phone_number = "0" + phone_number

        caller = User.objects.filter(phone_number=phone_number).first()

        if caller is None:
            caller = User.objects.create(
                phone_number=phone_number,
                name=name,
                last=last_name
            )

        ProjectMembership.objects.get_or_create(
            user=caller,
            project=project,
            role="caller"
        )

        new_callers.append(caller)

    return new_callers


def check_if_user_exist(user_id: int):
    """
    Validate user existence by ID. Return actual user or raise error value.
    """
    if not user_id:
        return ValueError({'error': 'user id required'})

    user = User.objects.filter(id=user_id).first()
    if not user:
        return ValueError({'error': 'user not found'})

    return user


def check_if_project_exist(project_id: int):
    """
    Validate project existence by ID.
    """
    if not project_id:
        return ValueError({'error': 'project id required'})

    project = Project.objects.filter(id=project_id).first()
    if not project:
        return ValueError({'error': 'project not found'})

    return project


def check_if_project_membership_exist(project: Project, user: User):
    """
    Validate project membership existence by returning the membership.
    """
    membership = ProjectMembership.objects.filter(project=project, user=user).first()
    if not membership:
        return ValueError({'error': 'project membership not found'})

    return membership


def toggle_user_project_membership_role(project_membership: ProjectMembership, project: Project, user: User):
    """
    Toggle user role between caller ↔ contact.
    Admin role cannot be changed.
    """
    if project_membership.role == 'admin':
        return ValueError({'error': 'admin role cannot be changed'})

    with transaction.atomic():

        old_role = project_membership.role

        if old_role == 'caller':
            new_role = 'contact'

            # Remove assigned contacts from this caller
            Contact.objects.filter(
                project=project,
                assigned_caller=user
            ).update(assigned_caller=None)

        elif old_role == 'contact':
            new_role = 'caller'

        else:
            return ValueError({'error': f"invalid role '{old_role}'"})

        project_membership.role = new_role
        project_membership.save()

        return old_role, new_role
