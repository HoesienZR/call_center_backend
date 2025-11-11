import pandas as pd
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from contacts.models import Contact
from projects.models import Project,ProjectMembership
from users.models import CustomUser

User = get_user_model()


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


def clean_string_field(value):
    """
    تمیز کردن فیلدهای متنی
    """
    if value is None or str(value).strip().lower() in ['nan', 'none', '']:
        return None
    return str(value).strip()
def import_caller_from_excel(file_obj, project: Project):

    new_callers = []
    try:
        df = pd.read_excel(file_obj, dtype=str)
    except Exception:
        df = pd.read_csv(file_obj, dtype=str)

    required_columns = ["name","last_name", "phone_number"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"ستون '{col}' در فایل موجود نیست.")
    for index, row in df.iterrows():
        name = clean_string_field(row.get("name", "نامشخص"))
        last_name = clean_string_field(row.get('last_name','نامشخص'))

        phone_number = str(clean_string_field(row.get("phone_number",)))


        if phone_number.isdigit() and not phone_number.startswith("0") and len(phone_number) in (9, 10):
            phone_number = "0" + phone_number
        try:
            caller=User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            caller=None
        if caller is None:
            caller = User.objects.create(phone_number=phone_number,name=name,last=last_name)
        ProjectMembership.objects.get_or_create(user=caller, project=project, role="caller")
        new_callers.append(caller)




    return new_callers
def check_if_user_exist(user_id:int):
    if not user_id:
        return ValueError({
            'error': 'user id required'
        })

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return ValueError({
            'error': 'user not found'
        })
    return user
def check_if_project_exist(project_id:int):
    if not project_id:
        return ValueError({'error': 'project id required'},)
    try:
        project = CustomUser.objects.get(id=project_id)
    except CustomUser.DoesNotExist:
        return ValueError({
            'error': 'user not found'
        })
    return project
def check_if_project_membership_exist(project:Project,user:User):
    try :
        project_membership = ProjectMembership.objects.get(project=project,user=user)
    except ProjectMembership.DoesNotExist:
        return ValueError({"error":"project membership not found"},)
    return project_membership
def toggle_user_project_membership_role(project_membership:ProjectMembership,project:Project,user:User):
    if project_membership.role == 'admin':
        return ValueError({
            'error': 'admin cannot changes'
            })
    with transaction.atomic():
        old_role = project_membership.role

        if project_membership.role == 'caller':
            new_role = 'contact'
            assigned_contacts = Contact.objects.filter(
                project=project,
                assigned_caller=user
            )
            assigned_contacts.update(assigned_caller=None)

        elif project_membership.role == 'contact':
            new_role = 'caller'
        else:
            return ValueError({
                'error': f'can\' this user role {project_membership.role} '
            })
        project_membership.role = new_role
        project_membership.save()
        return (old_role, new_role)
