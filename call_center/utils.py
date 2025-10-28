import re
import random
from django.contrib.auth.models import User
from .models import Contact, ProjectCaller, ProjectMembership
from django.db.models import Count

import string

# def validate_phone_number(phone):
#     """
#     اعتبارسنجی شماره تلفن
#     فرمت‌های مجاز: 09123456789, +989123456789, 00989123456789
#     """
#     if not phone:
#         return False, "شماره تلفن خالی است"
#
#     # حذف فاصله‌ها و کاراکترهای اضافی
#     phone = re.sub(r'[\s\-\(\)]', '', phone)
#
#     # بررسی فرمت‌های مختلف شماره تلفن ایرانی
#     patterns = [
#         r'^09\d{9}$',  # 09123456789
#         r'^\+989\d{9}$',  # +989123456789
#         r'^00989\d{9}$',  # 00989123456789
#     ]
#
#     for pattern in patterns:
#         if re.match(pattern, phone):
#             return True, phone
#
#     return False, "فرمت شماره تلفن نامعتبر است"


# def normalize_phone_number(phone):
#     """
#     نرمال‌سازی شماره تلفن به فرمت استاندارد 09xxxxxxxxx
#     """
#     if not phone:
#         return phone
#
#     # حذف فاصله‌ها و کاراکترهای اضافی
#     phone = re.sub(r'[\s\-\(\)]', '', phone)
#
#     # تبدیل به فرمت استاندارد
#     if phone.startswith('+98'):
#         phone = '0' + phone[3:]
#     elif phone.startswith('0098'):
#         phone = '0' + phone[4:]
#     elif phone.startswith('98') and len(phone) == 12:
#         phone = '0' + phone[2:]
#
#     return phone

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


# def is_caller_user(user, project=None):
#     """
#     بررسی اینکه آیا کاربر یک تماس‌گیرنده است یا خیر
#     تماس‌گیرندگان: کاربرانی که is_staff=False و is_superuser=False هستند
#     """
#     if user.is_staff:
#         return True
#     if project:
#         return ProjectMembership.objects.filter(user=user, project=project, role="caller").exists()
#     return ProjectMembership.objects.filter(user=user, role="caller").exists()

def get_available_callers_for_project(project):
    """
    دریافت لیست تماس‌گیرندگان فعال برای یک پروژه
    """
    from .models import ProjectCaller

    project_callers = ProjectCaller.objects.filter(
        project=project,
        is_active=True
    ).select_related('caller')

    return [pc.caller for pc in project_callers if is_caller_user(pc.caller)]


def assign_contacts_randomly(project, unassigned_contacts=None):
    """
    تخصیص تصادفی مخاطبین به تماس‌گیرندگان
    """
    from .models import Contact

    if unassigned_contacts is None:
        unassigned_contacts = Contact.objects.filter(
            project=project,
            assigned_caller__isnull=True
        )

    available_callers = get_available_callers_for_project(project)

    if not available_callers:
        return 0, "هیچ تماس‌گیرنده فعالی برای این پروژه یافت نشد"

    assigned_count = 0
    for contact in unassigned_contacts:
        # انتخاب تصادفی یک تماس‌گیرنده
        assigned_caller = random.choice(available_callers)
        contact.assigned_caller = assigned_caller
        contact.save()
        assigned_count += 1

    return assigned_count, f"{assigned_count} مخاطب به صورت تصادفی تخصیص داده شد"


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


# def clean_string_field(value):
#     """
#     تمیز کردن فیلدهای متنی
#     """
#     if value is None or str(value).strip().lower() in ['nan', 'none', '']:
#         return None
#     return str(value).strip()

def get_available_callers_for_project(project):
    """
    دریافت لیست تماس‌گیرندگان فعال برای یک پروژه
    """
    project_callers = ProjectCaller.objects.filter(
        project=project,
        is_active=True
    ).select_related('caller')

    return [pc.caller for pc in project_callers if is_caller_user(pc.caller)]

def assign_contacts_randomly(project, unassigned_contacts=None):
    """
    تخصیص عادلانه و تصادفی مخاطبین به تماس‌گیرندگان فعال پروژه.
    :param project: شیء Project
    :param unassigned_contacts: لیست یا QuerySet از مخاطبین (اختیاری)
    :return: تعداد تخصیص‌ها و پیام نتیجه
    """
    if unassigned_contacts is None:
        unassigned_contacts = Contact.objects.filter(
            project=project,
            assigned_caller__isnull=True
        )

    if not unassigned_contacts.exists():
        return 0, "هیچ مخاطب بدون تماس‌گیرنده‌ای یافت نشد."

    available_callers = get_available_callers_for_project(project)
    if not available_callers:
        return 0, "هیچ تماس‌گیرنده فعالی برای این پروژه یافت نشد."

    # شمارش تعداد مخاطبین فعلی هر تماس‌گیرنده برای توزیع عادلانه
    caller_contact_counts = Contact.objects.filter(
        project=project,
        assigned_caller__in=[caller.id for caller in available_callers]
    ).values('assigned_caller').annotate(count=Count('id')).order_by()

    # ایجاد دیکشنری برای تعداد مخاطبین هر تماس‌گیرنده
    caller_load = {caller.id: 0 for caller in available_callers}
    for item in caller_contact_counts:
        caller_load[item['assigned_caller']] = item['count']

    assigned_count = 0
    for contact in unassigned_contacts:
        if not contact.assigned_caller:
            # پیدا کردن تماس‌گیرنده با کمترین تعداد مخاطب
            min_load_caller_id = min(caller_load, key=caller_load.get)
            contact.assigned_caller_id = min_load_caller_id
            contact.save()
            caller_load[min_load_caller_id] += 1
            assigned_count += 1

    return assigned_count, f"{assigned_count} مخاطب به صورت تصادفی تخصیص داده شد."