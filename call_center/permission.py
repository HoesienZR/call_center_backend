# call_center/permissions.py

from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import Project, ProjectMembership, Contact, Call

# 1. کلاس دسترسی برای ادمین پروژه
class IsProjectAdmin(BasePermission):
    """
    این کلاس دسترسی بررسی می‌کند که آیا کاربر، ادمین پروژه‌ی مورد نظر است یا خیر.
    ادمین پروژه دسترسی کامل به آن پروژه و تمام اشیاء مرتبط با آن (مخاطبین، تماس‌ها و ...) دارد.
    """
    message = "شما باید ادمین این پروژه باشید تا بتوانید این عملیات را انجام دهید."

    def has_object_permission(self, request, view, obj):
        # اگر کاربر superuser باشد، همیشه دسترسی دارد.
        if request.user.is_superuser:
            return True

        # مشخص کردن پروژه بر اساس نوع آبجکت (Project, Contact, Call, etc.)
        project = None
        if isinstance(obj, Project):
            project = obj
        elif hasattr(obj, 'project'): # برای مدل‌هایی مانند Contact, Call, etc.
            project = obj.project
        else:
            return False # اگر آبجکت به پروژه مرتبط نباشد، دسترسی داده نمی‌شود.

        # بررسی اینکه آیا کاربر عضو پروژه با نقش 'admin' است یا خیر.
        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role='admin'
        ).exists()


# 2. کلاس دسترسی برای تماس‌گیرنده پروژه
class IsProjectCaller(BasePermission):
    """
    این کلاس دسترسی بررسی می‌کند که آیا کاربر، تماس‌گیرنده پروژه‌ی مورد نظر است یا خیر.
    تماس‌گیرنده می‌تواند عملیات مربوط به نقش خود را در پروژه انجام دهد.
    """
    message = "شما باید به عنوان تماس‌گیرنده به این پروژه تخصیص داده شده باشید."

    def has_object_permission(self, request, view, obj):
        # اگر کاربر superuser باشد، همیشه دسترسی دارد.
        if request.user.is_superuser:
            return True

        project = None
        if isinstance(obj, Project):
            project = obj
        elif hasattr(obj, 'project'):
            project = obj.project
        else:
            return False

        # بررسی اینکه آیا کاربر عضو پروژه با نقش 'caller' است یا خیر.
        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role='caller'
        ).exists()


# 3. کلاس دسترسی ترکیبی: ادمین یا تماس‌گیرنده پروژه
class IsProjectAdminOrCaller(BasePermission):
    """
    این کلاس دسترسی بررسی می‌کند که آیا کاربر، ادمین یا تماس‌گیرنده پروژه‌ی مورد نظر است.
    برای عملیاتی که هم ادمین و هم تماس‌گیرنده می‌توانند انجام دهند.
    """
    message = "شما باید ادمین یا تماس‌گیرنده این پروژه باشید."

    def has_object_permission(self, request, view, obj):
        # اگر کاربر superuser باشد، همیشه دسترسی دارد.
        if request.user.is_superuser:
            return True

        project = None
        if isinstance(obj, Project):
            project = obj
        elif hasattr(obj, 'project'):
            project = obj.project
        else:
            return False

        # بررسی اینکه آیا کاربر عضو پروژه با نقش 'admin' یا 'caller' است.
        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role__in=['admin', 'caller']
        ).exists()


# 4. کلاس دسترسی برای کاربرانی که فقط حق خواندن دارند (مخاطب یا ...)
class IsReadOnlyOrProjectAdmin(BasePermission):
    """
    این کلاس دسترسی به همه اعضای پروژه اجازه خواندن (Read-Only) می‌دهد،
    اما فقط به ادمین‌های پروژه اجازه نوشتن (ایجاد، ویرایش، حذف) را می‌دهد.
    """
    message = "فقط ادمین‌های پروژه می‌توانند تغییرات ایجاد کنند."

    def has_object_permission(self, request, view, obj):
        # اگر کاربر superuser باشد، همیشه دسترسی دارد.
        if request.user.is_superuser:
            return True

        project = None
        if isinstance(obj, Project):
            project = obj
        elif hasattr(obj, 'project'):
            project = obj.project
        else:
            return False

        # بررسی عضویت کاربر در پروژه
        is_member = ProjectMembership.objects.filter(project=project, user=request.user).exists()

        # اگر متد درخواست از نوع امن (GET, HEAD, OPTIONS) باشد و کاربر عضو پروژه باشد، اجازه داده می‌شود.
        if request.method in SAFE_METHODS:
            return is_member

        # در غیر این صورت (برای متدهای POST, PUT, PATCH, DELETE)، باید کاربر نقش 'admin' داشته باشد.
        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role='admin'
        ).exists()
