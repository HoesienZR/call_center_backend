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
